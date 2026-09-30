from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from app.auth.session import (
    clear_session_cookie,
    is_authenticated,
    passwords_match,
    set_session_cookie,
)
from app.config import get_settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    password: str


class SessionStatus(BaseModel):
    auth_enabled: bool
    authenticated: bool


def _status(request: Request) -> SessionStatus:
    settings = get_settings()
    return SessionStatus(
        auth_enabled=settings.auth_enabled,
        authenticated=is_authenticated(request, settings),
    )


@router.get("/session")
def session(request: Request) -> SessionStatus:
    return _status(request)


@router.post("/login")
def login(body: LoginRequest, request: Request, response: Response) -> SessionStatus:
    settings = get_settings()
    if settings.auth_enabled and not passwords_match(body.password, settings.app_access_password):
        raise HTTPException(status_code=401, detail="Incorrect password")
    if settings.auth_enabled:
        set_session_cookie(response, request, settings)
    return SessionStatus(auth_enabled=settings.auth_enabled, authenticated=True)


@router.post("/logout")
def logout(response: Response) -> SessionStatus:
    settings = get_settings()
    clear_session_cookie(response)
    return SessionStatus(auth_enabled=settings.auth_enabled, authenticated=False)
