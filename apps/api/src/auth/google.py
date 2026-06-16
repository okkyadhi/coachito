"""Google ID-token verification.

Wraps google-auth so the rest of the codebase doesn't import it directly.
Raises ValueError on any verification failure — the router maps that to 401.
"""

from typing import Any

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from src.config import settings

_ALLOWED_ISSUERS = ("accounts.google.com", "https://accounts.google.com")


def verify_google_id_token(token: str) -> dict[str, Any]:
    if not settings.google_client_id:
        raise ValueError("Google Sign-In is not configured on this deployment.")
    if not token:
        raise ValueError("Missing Google id_token.")

    claims = id_token.verify_oauth2_token(
        token,
        google_requests.Request(),
        settings.google_client_id,
    )
    if claims.get("iss") not in _ALLOWED_ISSUERS:
        raise ValueError("Untrusted token issuer.")
    if not claims.get("email_verified", False):
        raise ValueError("Email not verified by Google.")
    return claims
