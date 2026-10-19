"""Response models shared by several routers, and row <-> ``styleid_schema`` converters.

The vocabulary (enums, GarmentModel, BodyModel, ...) comes from ``styleid_schema``;
nothing here redefines it.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from styleid_schema import (
    BodyModel,
    Cut,
    GarmentKind,
    GarmentModel,
    PreferencesModel,
    Source,
    StretchClass,
)

from .db.models import BodyRecord, Brand, Garment, Product, SizeChart, SizeChartStatus, User


class BrandOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    domain: str


class SizeChartOut(BaseModel):
    id: str
    status: SizeChartStatus
    size_labels: list[str]
    warnings: list[str]
    unmapped_measures: list[str]
    model_id: str | None
    error: str | None
    extracted_at: datetime | None
    created_at: datetime


class ProductOut(BaseModel):
    id: str
    brand: BrandOut | None
    url_canonical: str
    url_original: str
    title: str | None
    fabric_composition: str | None
    stretch_class: StretchClass | None
    cut: Cut | None
    garment_kind: GarmentKind
    chart: SizeChartOut | None
    fetched_at: datetime | None
    created_at: datetime


def chart_out(chart: SizeChart) -> SizeChartOut:
    normalised = chart.normalised or {}
    sizes = normalised.get("sizes") or []
    return SizeChartOut(
        id=chart.id,
        status=SizeChartStatus(chart.status),
        size_labels=[str(s.get("size_label") or "?") for s in sizes],
        warnings=list(normalised.get("warnings") or []),
        unmapped_measures=list(normalised.get("unmapped_measures") or []),
        model_id=chart.model_id,
        error=chart.error,
        extracted_at=chart.extracted_at,
        created_at=chart.created_at,
    )


def latest_chart(db: Session, product: Product) -> SizeChart | None:
    """The chart backing the product, or the newest attempt (pending/failed) if none does."""
    if product.chart is not None:
        return product.chart
    return db.scalars(
        select(SizeChart)
        .where(SizeChart.product_id == product.id)
        .order_by(SizeChart.created_at.desc())
        .limit(1)
    ).first()


def product_out(db: Session, product: Product) -> ProductOut:
    chart = latest_chart(db, product)
    return ProductOut(
        id=product.id,
        brand=BrandOut.model_validate(product.brand) if product.brand else None,
        url_canonical=product.url_canonical,
        url_original=product.url_original,
        title=product.title,
        fabric_composition=product.fabric_composition,
        stretch_class=StretchClass(product.stretch_class) if product.stretch_class else None,
        cut=Cut(product.cut) if product.cut else None,
        garment_kind=GarmentKind(product.garment_kind),
        chart=chart_out(chart) if chart else None,
        fetched_at=product.fetched_at,
        created_at=product.created_at,
    )


def brand_out(brand: Brand) -> BrandOut:
    return BrandOut.model_validate(brand)


def garment_model_from_row(row: Garment) -> GarmentModel:
    return GarmentModel.model_validate(
        {
            "kind": row.kind,
            "cut": row.cut,
            "stretch": row.stretch_class,
            "size_label": row.size_label,
            "fit_tag": row.fit_tag,
            "length_from_center_back": row.length_from_center_back,
            "sleeve_from_center_back": row.sleeve_from_center_back,
            "measurements": row.measurements,
        }
    )


def apply_garment_model(row: Garment, model: GarmentModel) -> None:
    row.kind = model.kind.value
    row.cut = model.cut.value
    row.stretch_class = model.stretch.value
    row.size_label = model.size_label
    row.fit_tag = model.fit_tag.value if model.fit_tag else None
    row.length_from_center_back = model.length_from_center_back
    row.sleeve_from_center_back = model.sleeve_from_center_back
    row.measurements = model.model_dump(mode="json")["measurements"]


def body_model_from_row(row: BodyRecord) -> BodyModel:
    return BodyModel.model_validate(
        {
            "source": Source(row.source),
            "measurements": row.measurements,
            "landmarks": row.landmarks,
        }
    )


def preferences_of(user: User) -> PreferencesModel:
    return PreferencesModel.model_validate(user.preferences or {"shift_cm": {}})
