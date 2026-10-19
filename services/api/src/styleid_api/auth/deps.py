"""``get_current_user``: dev header or bearer JWT; ``require_age_verified`` for body data."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import Settings
from ..db.models import User
from ..db.session import get_db
from .tokens import InvalidToken, read_token

DEV_SUB_PREFIX = "dev:"


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_or_create_user_by_sub(db: Session, apple_sub: str, *, email: str | None = None) -> User:
    user = db.scalar(select(User).where(User.apple_sub == apple_sub))
    if user is None:
        user = User(apple_sub=apple_sub, email=email)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def get_settings_dep(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


SettingsDep = Annotated[Settings, Depends(get_settings_dep)]


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    settings: SettingsDep,
    authorization: Annotated[str | None, Header()] = None,
    x_dev_user: Annotated[str | None, Header(alias="X-Dev-User")] = None,
    x_dev_secret: Annotated[str | None, Header(alias="X-Dev-Secret")] = None,
) -> User:
    if x_dev_user and settings.dev_auth_enabled:
        if settings.dev_auth_secret and x_dev_secret != settings.dev_auth_secret:
            raise _unauthorized("bad dev auth secret")
        handle = x_dev_user.strip()
        if not handle or len(handle) > 64:
            raise _unauthorized("bad dev user handle")
        return get_or_create_user_by_sub(db, DEV_SUB_PREFIX + handle)

    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise _unauthorized("expected 'Authorization: Bearer <token>'")
        try:
            user_id = read_token(token, secret=settings.jwt_secret, issuer=settings.jwt_issuer)
        except InvalidToken as exc:
            raise _unauthorized(f"invalid token: {exc}") from exc
        user = db.get(User, user_id)
        if user is None:
            raise _unauthorized("unknown user")
        return user

    raise _unauthorized("not authenticated")


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_age_verified(user: CurrentUser) -> User:
    """Body data is only stored for users who confirmed they are 18 or older."""
    if not user.dob_verified_18:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "age verification required: confirm you are 18 or older before storing body data"
            ),
        )
    return user


VerifiedAdult = Annotated[User, Depends(require_age_verified)]
