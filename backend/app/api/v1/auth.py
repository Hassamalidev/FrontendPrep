"""Authentication endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request, status

from app.core.config import settings
from app.core.deps import CurrentUser, DbSession
from app.schemas.auth import (
    AuthOut,
    ChangePasswordIn,
    LoginIn,
    RefreshIn,
    RegisterIn,
    TokenPair,
    UserPublic,
)
from app.schemas.common import Msg
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


@router.post("/register", response_model=AuthOut, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterIn, request: Request, db: DbSession) -> AuthOut:
    user, tokens = await auth_service.register(db, data, user_agent=_agent(request))
    return AuthOut(user=UserPublic.model_validate(user), tokens=tokens)


@router.post("/login", response_model=AuthOut)
async def login(data: LoginIn, request: Request, db: DbSession) -> AuthOut:
    user, tokens = await auth_service.login(db, data, user_agent=_agent(request))
    return AuthOut(user=UserPublic.model_validate(user), tokens=tokens)


@router.post("/refresh", response_model=TokenPair)
async def refresh(data: RefreshIn, request: Request, db: DbSession) -> TokenPair:
    return await auth_service.refresh_tokens(db, data.refresh_token, user_agent=_agent(request))


@router.post("/logout", response_model=Msg)
async def logout(data: RefreshIn, db: DbSession, user: CurrentUser) -> Msg:
    await auth_service.logout(db, user.id, data.refresh_token)
    return Msg(detail="Signed out.")


@router.post("/logout-all", response_model=Msg)
async def logout_all(db: DbSession, user: CurrentUser) -> Msg:
    await auth_service.logout(db, user.id, None, all_sessions=True)
    return Msg(detail="Signed out of every device.")


@router.get("/demo")
async def demo_accounts() -> dict:
    """Ready-made accounts for trying the app, when demo access is enabled.

    Returns an empty list rather than a 404 when disabled, so the sign-in page
    can simply render nothing. Gated on environment as well as the flag: a
    production deployment never advertises working credentials.
    """
    if not settings.demo_enabled:
        return {"enabled": False, "accounts": []}

    return {
        "enabled": True,
        "accounts": [
            {
                "label": "Candidate",
                "description": "The student experience: practice, mock tests and the ISSB suite.",
                "email": settings.DEMO_STUDENT_EMAIL,
                "password": settings.DEMO_STUDENT_PASSWORD,
            },
            {
                "label": "Administrator",
                "description": "Adds the question generator, the review queue and maintenance.",
                "email": settings.BOOTSTRAP_ADMIN_EMAIL,
                "password": settings.BOOTSTRAP_ADMIN_PASSWORD,
            },
        ],
    }


@router.get("/me", response_model=UserPublic)
async def me(user: CurrentUser) -> UserPublic:
    return UserPublic.model_validate(user)


@router.post("/change-password", response_model=Msg)
async def change_password(data: ChangePasswordIn, db: DbSession, user: CurrentUser) -> Msg:
    await auth_service.change_password(db, user, data)
    return Msg(detail="Password changed. Please sign in again.")
