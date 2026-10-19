"""Fit reports: the product's sizes vs the shopper's references and body."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from styleid_fit import build_report, primary_reference
from styleid_schema import FitReportModel

from ..auth import CurrentUser
from ..db.models import FitReportRow, Garment, Product, SizeChartStatus, User
from ..db.session import get_db
from ..schemas import (
    ProductOut,
    body_model_from_row,
    garment_model_from_row,
    latest_chart,
    preferences_of,
    product_out,
)
from .body import current_record

router = APIRouter(prefix="/fit", tags=["fit"])

DB = Annotated[Session, Depends(get_db)]


class FitReportIn(BaseModel):
    product_id: str
    reference_garment_ids: list[str] | None = Field(
        default=None,
        description=(
            "Closet garments to compare against; default: every garment marked as a reference"
        ),
    )


class FitReportOut(BaseModel):
    id: str
    report: FitReportModel
    product: ProductOut
    body_record_id: str | None
    reference_garment_id: str | None = Field(
        description="The closet garment the per-zone deltas are relative to"
    )
    created_at: datetime


def _out(db: Session, row: FitReportRow, product: Product) -> FitReportOut:
    return FitReportOut(
        id=row.id,
        report=FitReportModel.model_validate(row.result),
        product=product_out(db, product),
        body_record_id=row.body_record_id,
        reference_garment_id=row.reference_garment_id,
        created_at=row.created_at,
    )


def _catalogue(db: Session, product: Product) -> list[Garment]:
    chart = latest_chart(db, product)
    if product.chart_id is None or chart is None:
        state = chart.status if chart else "missing"
        error = chart.error if chart else ""
        detail = {
            "missing": "no size chart for this product yet; call /v1/products/check first",
            SizeChartStatus.PENDING.value: "size chart extraction is still running; try again",
            SizeChartStatus.NEEDS_REVIEW.value: "size chart needs review before it can be used",
            SizeChartStatus.FAILED.value: f"size chart extraction failed: {error}",
            SizeChartStatus.NOT_FOUND.value: "no size chart was found on the product page",
        }.get(state, f"size chart is {state}")
        raise HTTPException(status.HTTP_409_CONFLICT, detail=detail)
    rows = db.scalars(
        select(Garment).where(Garment.product_id == product.id).order_by(Garment.created_at)
    ).all()
    if not rows:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="the size chart has no sizes")
    return list(rows)


def _references(db: Session, user: User, ids: list[str] | None) -> list[Garment]:
    stmt = select(Garment).where(Garment.owner_user_id == user.id)
    if ids is None:
        stmt = stmt.where(Garment.is_reference.is_(True))
    else:
        if not ids:
            return []
        stmt = stmt.where(Garment.id.in_(ids))
    rows = list(db.scalars(stmt.order_by(Garment.created_at)).all())
    if ids is not None and len(rows) != len(set(ids)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="unknown reference garment id")
    return rows


@router.post("/reports", status_code=status.HTTP_201_CREATED)
def create_fit_report(payload: FitReportIn, user: CurrentUser, db: DB) -> FitReportOut:
    product = db.get(Product, payload.product_id)
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="product not found")
    catalogue = _catalogue(db, product)
    candidates = [garment_model_from_row(g).to_engine() for g in catalogue]

    body_row = current_record(db, user)
    body = body_model_from_row(body_row).to_engine() if body_row else None

    ref_rows = _references(db, user, payload.reference_garment_ids)
    refs = [garment_model_from_row(g).to_engine() for g in ref_rows]
    prefs = preferences_of(user).to_engine()

    report = build_report(candidates, body, refs, prefs)
    primary = primary_reference(candidates[0], refs)
    primary_id = next((row.id for row, g in zip(ref_rows, refs, strict=True) if g is primary), None)

    model = FitReportModel.from_engine(report)
    row = FitReportRow(
        user_id=user.id,
        body_record_id=body_row.id if body_row else None,
        product_id=product.id,
        reference_garment_id=primary_id,
        result=model.model_dump(mode="json"),
        engine_version=report.engine_version,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _out(db, row, product)


@router.get("/reports")
def list_fit_reports(
    user: CurrentUser, db: DB, limit: Annotated[int, Query(ge=1, le=200)] = 50
) -> list[FitReportOut]:
    rows = db.scalars(
        select(FitReportRow)
        .where(FitReportRow.user_id == user.id)
        .order_by(FitReportRow.created_at.desc(), FitReportRow.id)
        .limit(limit)
    ).all()
    out: list[FitReportOut] = []
    for row in rows:
        product = db.get(Product, row.product_id)
        if product is not None:
            out.append(_out(db, row, product))
    return out


@router.get("/reports/{report_id}")
def get_fit_report(report_id: str, user: CurrentUser, db: DB) -> FitReportOut:
    row = db.get(FitReportRow, report_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="fit report not found")
    product = db.get(Product, row.product_id)
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="product not found")
    return _out(db, row, product)
