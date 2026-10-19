"""The shopper's closet: measured garments, and landmark corrections on their photos."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from styleid_schema import GarmentModel

from ..auth import CurrentUser
from ..db.models import Garment, LandmarkCorrection, User
from ..db.session import get_db
from ..schemas import apply_garment_model, garment_model_from_row

router = APIRouter(prefix="/closet", tags=["closet"])

DB = Annotated[Session, Depends(get_db)]


class ClosetGarmentIn(GarmentModel):
    """A ``GarmentModel`` plus closet bookkeeping."""

    name: str | None = Field(default=None, max_length=120, description='e.g. "grey tee"')
    is_reference: bool = Field(
        default=True, description="Use this garment as a fit reference in reports"
    )


class ClosetGarmentOut(ClosetGarmentIn):
    id: str
    created_at: datetime
    updated_at: datetime


class LandmarkPoint(BaseModel):
    x: float
    y: float


class LandmarkCorrectionIn(BaseModel):
    image_blob_key: str = Field(max_length=512)
    proposed: dict[str, LandmarkPoint] = Field(description="Landmarks the app proposed, in px")
    corrected: dict[str, LandmarkPoint] = Field(description="Landmarks after the user moved them")
    scale_cm_per_px: float = Field(gt=0)


class LandmarkCorrectionOut(LandmarkCorrectionIn):
    id: str
    garment_id: str
    created_at: datetime


def garment_out(row: Garment) -> ClosetGarmentOut:
    model = garment_model_from_row(row)
    return ClosetGarmentOut(
        **model.model_dump(),
        name=row.name,
        is_reference=row.is_reference,
        id=row.id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _apply(row: Garment, payload: ClosetGarmentIn) -> None:
    apply_garment_model(row, payload)
    row.name = payload.name
    row.is_reference = payload.is_reference


def owned_garment(db: Session, user: User, garment_id: str) -> Garment:
    row = db.get(Garment, garment_id)
    if row is None or row.owner_user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="garment not found")
    return row


@router.get("/garments")
def list_closet_garments(user: CurrentUser, db: DB) -> list[ClosetGarmentOut]:
    rows = db.scalars(
        select(Garment).where(Garment.owner_user_id == user.id).order_by(Garment.created_at)
    ).all()
    return [garment_out(r) for r in rows]


@router.post("/garments", status_code=status.HTTP_201_CREATED)
def create_closet_garment(payload: ClosetGarmentIn, user: CurrentUser, db: DB) -> ClosetGarmentOut:
    row = Garment(owner_user_id=user.id)
    _apply(row, payload)
    db.add(row)
    db.commit()
    db.refresh(row)
    return garment_out(row)


@router.get("/garments/{garment_id}")
def get_closet_garment(garment_id: str, user: CurrentUser, db: DB) -> ClosetGarmentOut:
    return garment_out(owned_garment(db, user, garment_id))


@router.put("/garments/{garment_id}")
def update_closet_garment(
    garment_id: str, payload: ClosetGarmentIn, user: CurrentUser, db: DB
) -> ClosetGarmentOut:
    row = owned_garment(db, user, garment_id)
    _apply(row, payload)
    db.commit()
    db.refresh(row)
    return garment_out(row)


@router.delete("/garments/{garment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_closet_garment(garment_id: str, user: CurrentUser, db: DB) -> Response:
    row = owned_garment(db, user, garment_id)
    db.delete(row)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _correction_out(row: LandmarkCorrection) -> LandmarkCorrectionOut:
    return LandmarkCorrectionOut(
        id=row.id,
        garment_id=row.garment_id,
        image_blob_key=row.image_blob_key,
        proposed=row.proposed,
        corrected=row.corrected,
        scale_cm_per_px=row.scale_cm_per_px,
        created_at=row.created_at,
    )


@router.post("/garments/{garment_id}/landmark-corrections", status_code=status.HTTP_201_CREATED)
def create_landmark_correction(
    garment_id: str, payload: LandmarkCorrectionIn, user: CurrentUser, db: DB
) -> LandmarkCorrectionOut:
    """Record how the user moved the proposed flat-lay landmarks; training data for the
    landmark model."""
    garment = owned_garment(db, user, garment_id)
    row = LandmarkCorrection(
        garment_id=garment.id,
        image_blob_key=payload.image_blob_key,
        proposed={k: v.model_dump() for k, v in payload.proposed.items()},
        corrected={k: v.model_dump() for k, v in payload.corrected.items()},
        scale_cm_per_px=payload.scale_cm_per_px,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _correction_out(row)


@router.get("/garments/{garment_id}/landmark-corrections")
def list_landmark_corrections(
    garment_id: str, user: CurrentUser, db: DB
) -> list[LandmarkCorrectionOut]:
    garment = owned_garment(db, user, garment_id)
    rows = db.scalars(
        select(LandmarkCorrection)
        .where(LandmarkCorrection.garment_id == garment.id)
        .order_by(LandmarkCorrection.created_at)
    ).all()
    return [_correction_out(r) for r in rows]
