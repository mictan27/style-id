"""Body records: the nine measurements (plus landmarks) from a scan, photo or tape.

Everything that stores body data is behind the 18+ gate (``VerifiedAdult``)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from styleid_schema import BodyField, BodyModel, Confidence, MeasurementModel, Source

from ..auth import CurrentUser, VerifiedAdult
from ..db.models import BodyRecord, User, utcnow
from ..db.session import get_db
from ..schemas import body_model_from_row

router = APIRouter(prefix="/body", tags=["body"])

DB = Annotated[Session, Depends(get_db)]


class BodyRecordIn(BodyModel):
    """A ``BodyModel`` plus the blob key of the fitted mesh, if any."""

    mesh_blob_key: str | None = Field(default=None, max_length=512)


class BodyRecordOut(BodyModel):
    id: str
    mesh_blob_key: str | None
    confirmed_at: datetime | None
    is_current: bool
    created_at: datetime


CmValue = Annotated[float, Field(gt=0, lt=400)]


class BodyConfirmIn(BaseModel):
    """Per-field overrides from the confirm screen. Every value given replaces the measured
    one and is stored as ``source=manual, confidence=high``."""

    overrides: dict[BodyField, CmValue] = Field(default_factory=dict)


def record_out(row: BodyRecord) -> BodyRecordOut:
    model = body_model_from_row(row)
    return BodyRecordOut(
        **model.model_dump(),
        id=row.id,
        mesh_blob_key=row.mesh_blob_key,
        confirmed_at=row.confirmed_at,
        is_current=row.is_current,
        created_at=row.created_at,
    )


def current_record(db: Session, user: User) -> BodyRecord | None:
    return db.scalars(
        select(BodyRecord)
        .where(BodyRecord.user_id == user.id, BodyRecord.is_current.is_(True))
        .order_by(BodyRecord.created_at.desc())
        .limit(1)
    ).first()


def _owned(db: Session, user: User, record_id: str) -> BodyRecord:
    row = db.get(BodyRecord, record_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="body record not found")
    return row


@router.post("/records", status_code=status.HTTP_201_CREATED)
def create_body_record(payload: BodyRecordIn, user: VerifiedAdult, db: DB) -> BodyRecordOut:
    """Store a new body record and make it the current one."""
    db.execute(
        update(BodyRecord)
        .where(BodyRecord.user_id == user.id, BodyRecord.is_current.is_(True))
        .values(is_current=False)
    )
    dumped = payload.model_dump(mode="json")
    row = BodyRecord(
        user_id=user.id,
        source=payload.source.value,
        mesh_blob_key=payload.mesh_blob_key,
        measurements=dumped["measurements"],
        landmarks=dumped["landmarks"],
        is_current=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return record_out(row)


@router.get("/records/current")
def get_current_body_record(user: CurrentUser, db: DB) -> BodyRecordOut:
    row = current_record(db, user)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="no body record yet")
    return record_out(row)


@router.get("/records/{record_id}")
def get_body_record(record_id: str, user: CurrentUser, db: DB) -> BodyRecordOut:
    return record_out(_owned(db, user, record_id))


@router.post("/records/{record_id}/confirm")
def confirm_body_record(
    record_id: str, payload: BodyConfirmIn, user: VerifiedAdult, db: DB
) -> BodyRecordOut:
    """The user looked at the numbers and accepted them, overriding any they corrected."""
    row = _owned(db, user, record_id)
    model = body_model_from_row(row)
    measurements = dict(model.measurements)
    for field, value in payload.overrides.items():
        measurements[field] = MeasurementModel(
            value_cm=value, source=Source.MANUAL, confidence=Confidence.HIGH
        )
    updated = BodyModel(source=model.source, measurements=measurements, landmarks=model.landmarks)
    row.measurements = updated.model_dump(mode="json")["measurements"]
    row.confirmed_at = utcnow()
    db.commit()
    db.refresh(row)
    return record_out(row)
