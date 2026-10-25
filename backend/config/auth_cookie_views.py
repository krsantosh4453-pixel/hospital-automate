"""
Token refresh and CSRF endpoints for the cookie-based browser session.

Kept apart from config/auth_cookies.py, which DRF imports while loading its
settings (DEFAULT_AUTHENTICATION_CLASSES); importing DRF views there would be
circular.
"""

from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.views import TokenRefreshView

from config.auth_cookies import REFRESH_COOKIE, wants_cookies


class CookieTokenRefreshView(TokenRefreshView):
    """Refresh from the body (API clients) or from the httpOnly refresh cookie."""

    def post(self, request, *args, **kwargs):
        if "refresh" in request.data or not wants_cookies(request):
            return super().post(request, *args, **kwargs)
        raw = request.COOKIES.get(REFRESH_COOKIE)
        if not raw:
            return Response({"detail": "No active session."}, status=status.HTTP_401_UNAUTHORIZED)
        serializer = self.get_serializer(data={"refresh": raw})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            raise InvalidToken(exc.args[0])
        # AuthCookieMiddleware moves the new tokens into cookies.
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def csrf_token(request):
    """The CSRF cookie is httpOnly, so the client reads the token from here."""
    return Response({"csrfToken": get_token(request)})
