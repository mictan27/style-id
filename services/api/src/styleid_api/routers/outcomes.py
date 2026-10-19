"""Purchase outcomes: the one post-delivery question, which nudges preferences."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from styleid_fit import nudge
from styleid_schema import Direction, OutcomeModel, PreferencesModel, Zone

from ..auth import CurrentUser
from ..db.models import FitReportRow, PurchaseOutcome
from ..db.session import get_db
from ..schemas import preferences_of

router = APIRouter(prefix="/outcomes", tags=["outcomes"])

DB = Annotated[Session, Depends(get_db)]


class OutcomeIn(BaseModel):
    fit_report_id: str
    size_bought: str = Field(min_length=1, max_length=32)
    kept: bool
    zone: Zone | None = Field(default=None, description="The zone that caused a return")
    direction: Direction | None = Field(default=None, description="tight or loose there")


class OutcomeOut(BaseModel):
    id: str
    fit_report_id: str
    size_bought: str
    kept: bool
    zone: Zone | None
    direction: Direction | None
    preferences: PreferencesModel = Field(description="Preferences after applying the nudge")
    created_at: datetime


@router.post("", status_code=status.HTTP_201_CREATED)
def create_outcome(payload: OutcomeIn, user: CurrentUser, db: DB) -> OutcomeOut:
    report = db.get(FitReportRow, payload.fit_report_id)
    if report is None or report.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="fit report not found")
    if not payload.kept and (payload.zone is None) != (payload.direction is None):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="a return needs both zone and direction, or neither",
        )

    outcome = OutcomeModel(kept=payload.kept, zone=payload.zone, direction=payload.direction)
    updated = nudge(preferences_of(user).to_engine(), outcome.to_engine())
    user.preferences = PreferencesModel.from_engine(updated).model_dump(mode="json")

    row = PurchaseOutcome(
        fit_report_id=report.id,
        user_id=user.id,
        size_bought=payload.size_bought,
        kept=payload.kept,
        problem_zone=payload.zone.value if payload.zone else None,
        direction=payload.direction.value if payload.direction else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    db.refresh(user)
    return OutcomeOut(
        id=row.id,
        fit_report_id=row.fit_report_id,
        size_bought=row.size_bought,
        kept=row.kept,
        zone=payload.zone,
        direction=payload.direction,
        preferences=preferences_of(user),
        created_at=row.created_at,
    )
