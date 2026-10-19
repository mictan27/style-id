"""``POST /v1/auth/apple``: exchange an Apple identity token for our bearer JWT."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import User
from ..db.session import get_db
from .apple import AppleTokenError, AppleVerifier
from .deps import SettingsDep
from .tokens import issue_token

router = APIRouter(prefix="/auth", tags=["auth"])


class AppleSignInRequest(BaseModel):
    identity_token: str = Field(description="The JWT from ASAuthorizationAppleIDCredential")
    dob_verified_18: bool = Field(
        description="The user confirmed in-app that they are 18 or older (needed for body data)"
    )


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    is_new_user: bool


def get_apple_verifier(request: Request) -> AppleVerifier:
    verifier: AppleVerifier = request.app.state.apple_verifier
    return verifier


@router.post("/apple", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def sign_in_with_apple(
    payload: AppleSignInRequest,
    db: Annotated[Session, Depends(get_db)],
    settings: SettingsDep,
    verifier: Annotated[AppleVerifier, Depends(get_apple_verifier)],
) -> TokenResponse:
    try:
        claims = verifier.verify(payload.identity_token)
    except AppleTokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    user = db.scalar(select(User).where(User.apple_sub == claims.sub))
    is_new = user is None
    if user is None:
        user = User(apple_sub=claims.sub, email=claims.email)
        db.add(user)
    if claims.email and user.email != claims.email:
        user.email = claims.email
    if payload.dob_verified_18 and not user.dob_verified_18:
        user.dob_verified_18 = True
    db.commit()
    db.refresh(user)

    token = issue_token(
        user.id,
        secret=settings.jwt_secret,
        issuer=settings.jwt_issuer,
        ttl_seconds=settings.jwt_ttl_seconds,
    )
    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_ttl_seconds,
        user_id=user.id,
        is_new_user=is_new,
    )
