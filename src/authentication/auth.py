import jwt
import jwt.algorithms
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization

from more_itertools import first
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from django.contrib.auth.models import User
from django.conf import settings
from witswin.caching import cache_function_in_seconds

from authentication.models import PrivyProfile, UserProfile

import requests
import base64


PUBLIC_KEY_URL = settings.PRIVY_JWKS_URL


def base64url_decode(input_str):
    padding = "=" * (4 - (len(input_str) % 4))
    return base64.urlsafe_b64decode(input_str + padding)


def serialize_public_key(public_key):
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")


def deserialize_public_key(pem_data):
    return serialization.load_pem_public_key(pem_data.encode("utf-8"))


@cache_function_in_seconds(3600)
def get_jwk_keys():
    response = requests.get(PUBLIC_KEY_URL)

    assert response.ok, "Unable to fetch public keys"

    jwks = response.json()

    return jwks


def get_public_key(token: str):
    jwks = get_jwk_keys()

    token_kid = jwt.get_unverified_header(token)["kid"]
    public_key_data = next(key for key in jwks["keys"] if key["kid"] == token_kid)

    x_int = int.from_bytes(base64url_decode(public_key_data["x"]), "big")
    y_int = int.from_bytes(base64url_decode(public_key_data["y"]), "big")

    public_numbers = ec.EllipticCurvePublicNumbers(x_int, y_int, ec.SECP256R1())

    public_key = public_numbers.public_key()

    return serialize_public_key(public_key)


def get_privy_user_by_id(privy_id: str):
    response = requests.get(
        f"https://auth.privy.io/api/v1/users/{privy_id}",
        auth=(settings.PRIVY_APP_ID, settings.PRIVY_APP_SECRET),
        headers={"privy-app-id": settings.PRIVY_APP_ID},
    )

    assert response.ok, "Unable to get privy user"

    return response.json()


class PrivyJWTAuthentication(BaseAuthentication):
    def resolve_from_token(self, token: str):
        try:
            public_key = deserialize_public_key(get_public_key(token))

            payload = jwt.decode(
                token,
                public_key,
                issuer="privy.io",
                audience=settings.PRIVY_APP_ID,
                algorithms=["ES256"],
            )

            user_id = payload.get("sub")
            if not user_id:
                raise AuthenticationFailed("User not found in token")

            privy_user = PrivyProfile.objects.filter(id=user_id).first()

            if privy_user:
                return (privy_user.profile.user, token)

            privy_data = get_privy_user_by_id(user_id)

            wallet_address = first(
                filter(
                    lambda account: account.get("imported") is False
                    and account["wallet_client"] == "privy",
                    privy_data["linked_accounts"],
                )
            )

            user = User.objects.create(
                username=user_id + " | " + str(privy_data["created_at"])
            )

            user_profile = UserProfile.objects.create(
                wallet_address=wallet_address["address"],
                user=user,
                username=f"User {user.pk}",
            )

            privy_user = PrivyProfile.objects.create(profile=user_profile, id=user_id)

            return (user, token)

        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed("Token has expired")
        except jwt.InvalidTokenError:
            raise AuthenticationFailed("Invalid token")
        except Exception as e:
            raise AuthenticationFailed(f"Error during authentication: {str(e)}")

    def authenticate(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None

        parts = auth_header.split(" ")

        if len(parts) != 2 or parts[0] != "Bearer":
            return None

        token = parts[1]

        return self.resolve_from_token(token)
