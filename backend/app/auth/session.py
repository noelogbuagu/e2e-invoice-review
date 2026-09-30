import hashlib
import hmac
from datetime import timedelta

from fastapi import Request, Response

from app.config import Settings

COOKIE_NAME = "ir_session"
SESSION_MAX_AGE = timedelta(days=7)
_SESSION_PAYLOAD = b"invoice-review"


def passwords_match(submitted: str, expected: str) -> bool:
    return hmac.compare_digest(
        hashlib.sha256(submitted.encode()).digest(),
        hashlib.sha256(expected.encode()).digest(),
    )


def session_token(secret: str) -> str:
    return hmac.new(secret.encode(), _SESSION_PAYLOAD, hashlib.sha256).hexdigest()


def is_authenticated(request: Request, settings: Settings) -> bool:
    if not settings.auth_enabled:
        return True
    presented = request.cookies.get(COOKIE_NAME, "")
    expected = session_token(settings.app_session_secret)
    return hmac.compare_digest(presented, expected)


def cookie_is_secure(request: Request) -> bool:
    forwarded = request.headers.get("x-forwarded-proto", "")
    scheme = forwarded.split(",")[0].strip() if forwarded else request.url.scheme
    return scheme == "https"


def set_session_cookie(response: Response, request: Request, settings: Settings) -> None:
    response.set_cookie(
        COOKIE_NAME,
        session_token(settings.app_session_secret),
        max_age=int(SESSION_MAX_AGE.total_seconds()),
        httponly=True,
        secure=cookie_is_secure(request),
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")
