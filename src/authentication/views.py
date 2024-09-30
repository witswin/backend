from django.contrib.auth.models import User
from rest_framework.generics import CreateAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework import status
from authentication.models import UserProfile
from authentication.serializers import AuthenticateSerializer, UserProfileSerializer

from typing import Any
from web3 import Web3

import uuid


class GetProfileView(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer
    queryset = UserProfile.objects.all()

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def get_object(self):
        return self.request.user.profile  # type: ignore


class AuthenticateView(CreateAPIView):
    serializer_class = AuthenticateSerializer
    queryset = UserProfile.objects.filter(user__is_active=True)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        headers = self.get_success_headers(serializer.data)

        wallet_address = serializer.validated_data["address"]

        try:
            profile = UserProfile.objects.get(
                wallet_address=Web3.to_checksum_address(wallet_address)
            )
        except UserProfile.DoesNotExist:
            user = User.objects.create_user(username="WITS" + str(uuid.uuid4())[:16])

            profile = UserProfile.objects.create(
                wallet_address=Web3.to_checksum_address(wallet_address), user=user
            )

        data: Any = UserProfileSerializer(instance=profile).data

        token, _ = Token.objects.get_or_create(user=profile.user)

        data["token"] = token.key

        response = Response(data, status=status.HTTP_201_CREATED, headers=headers)

        response.set_cookie(
            key="userToken",
            value=token.key,
            httponly=True,
            secure=True,
            domain=".wits.win",  # Set the cookie for all subdomains of wits.win
            samesite="None",
        )

        return response
