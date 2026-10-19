"""The signed-in user and their learned preferences."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from styleid_schema import PreferencesModel

from ..auth import CurrentUser
from ..db.models import User
from ..db.session import get_db
from ..schemas import preferences_of

router = APIRouter(prefix="/me", tags=["me"])


class MeOut(BaseModel):
    id: str
    email: str | None
    dob_verified_18: bool
    preferences: PreferencesModel
    created_at: datetime


class MePatch(BaseModel):
    email: str | None = None
    dob_verified_18: bool | None = None


def me_out(user: User) -> MeOut:
    return MeOut(
        id=user.id,
        email=user.email,
        dob_verified_18=user.dob_verified_18,
        preferences=preferences_of(user),
        created_at=user.created_at,
    )


@router.get("")
def get_me(user: CurrentUser) -> MeOut:
    return me_out(user)


@router.patch("")
def update_me(
    payload: MePatch, user: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> MeOut:
    if payload.email is not None:
        user.email = payload.email
    if payload.dob_verified_18 is not None:
        user.dob_verified_18 = payload.dob_verified_18
    db.commit()
    db.refresh(user)
    return me_out(user)


@router.patch("/preferences")
def update_preferences(
    payload: PreferencesModel, user: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> PreferencesModel:
    """Merge the given per-zone shifts into the stored preferences. Send ``0`` to reset a
    zone. The engine nudges these automatically from purchase outcomes."""
    current = preferences_of(user)
    merged = dict(current.shift_cm)
    merged.update(payload.shift_cm)
    updated = PreferencesModel(shift_cm=merged)
    user.preferences = updated.model_dump(mode="json")
    db.commit()
    db.refresh(user)
    return preferences_of(user)
