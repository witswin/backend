# middleware.py
import base64
from http.cookies import SimpleCookie

from django.contrib.auth.models import AnonymousUser
from rest_framework.authtoken.models import Token
from channels.db import database_sync_to_async


@database_sync_to_async
def get_user_from_basic_auth(tk: str):
    try:
        token = Token.objects.filter(key=tk.strip().replace("'", "")).first()

        if token is None:
            return AnonymousUser()

        return token.user
    except Exception:
        return AnonymousUser()


class BasicTokenHeaderAuthentication:
    """
    Custom middleware (insecure) that takes user IDs from the query string.
    """

    def __init__(self, app):
        # Store the ASGI application we were passed
        self.app = app

    async def __call__(self, scope, receive, send):

        headers = dict(scope["headers"])
        cookie = SimpleCookie()

        query_params = scope["query_string"].decode("utf-8")

        if "auth" in query_params:
            scope["user"] = await get_user_from_basic_auth(query_params.split("=")[1])

        elif headers.get(b"cookie"):
            scope["user"] = AnonymousUser()

            cookie.load(headers[b"cookie"].decode("utf-8"))
            if cookie.get("userToken") or cookie.get("ws_session"):
                scope["user"] = await get_user_from_basic_auth(cookie.get("userToken").value or cookie.get("ws_session").value)  # type: ignore
        else:
            scope["user"] = AnonymousUser()

        return await self.app(scope, receive, send)
