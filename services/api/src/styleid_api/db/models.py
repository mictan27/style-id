"""SQLAlchemy 2.0 declarative models.

Conventions: UUID primary keys stored as 36-character strings (SQLite friendly),
``created_at``/``updated_at`` in UTC, and a ``JSONType`` that is JSONB on Postgres
and JSON on SQLite. Pydantic models from ``styleid_schema`` are stored as their
``model_dump(mode="json")`` output in JSON columns; the API layer converts back.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

JSONType = JSON().with_variant(JSONB(), "postgresql")
UUIDStr = String(36)


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


class SizeChartStatus(StrEnum):
    """``styleid_schema.ChartStatus`` plus the queued state."""

    PENDING = "pending"
    OK = "ok"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"
    NOT_FOUND = "not_found"


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUIDStr, primary_key=True, default=new_id)
    apple_sub: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    dob_verified_18: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    #: ``PreferencesModel.model_dump()``
    preferences: Mapped[dict[str, Any]] = mapped_column(
        JSONType, default=lambda: {"shift_cm": {}}, nullable=False
    )


class BodyRecord(Base, TimestampMixin):
    __tablename__ = "body_records"

    id: Mapped[str] = mapped_column(UUIDStr, primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        UUIDStr, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    #: ``styleid_fit.Source`` value (lidar, photo, manual ...)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    mesh_blob_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    #: ``dict[BodyField, MeasurementModel]`` dump
    measurements: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    #: ``LandmarksModel`` dump
    landmarks: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Brand(Base, TimestampMixin):
    __tablename__ = "brands"

    id: Mapped[str] = mapped_column(UUIDStr, primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    #: Typical ease per zone in cm, used when a chart is body-based.
    typical_ease: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    seeded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(UUIDStr, primary_key=True, default=new_id)
    brand_id: Mapped[str | None] = mapped_column(
        UUIDStr, ForeignKey("brands.id", ondelete="SET NULL"), nullable=True, index=True
    )
    url_canonical: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    url_original: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    fabric_composition: Mapped[str | None] = mapped_column(Text, nullable=True)
    stretch_class: Mapped[str | None] = mapped_column(String(32), nullable=True)
    cut: Mapped[str | None] = mapped_column(String(32), nullable=True)
    garment_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    #: The chart currently backing this product's catalogue garments. ``use_alter`` breaks
    #: the products <-> size_charts cycle at DDL time.
    chart_id: Mapped[str | None] = mapped_column(
        UUIDStr,
        ForeignKey(
            "size_charts.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_products_chart_id_size_charts",
        ),
        nullable=True,
    )
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    brand: Mapped[Brand | None] = relationship(Brand, lazy="joined")
    chart: Mapped[SizeChart | None] = relationship(
        "SizeChart", foreign_keys=[chart_id], lazy="joined", post_update=True
    )


class SizeChart(Base, TimestampMixin):
    __tablename__ = "size_charts"

    id: Mapped[str] = mapped_column(UUIDStr, primary_key=True, default=new_id)
    product_id: Mapped[str | None] = mapped_column(
        UUIDStr, ForeignKey("products.id", ondelete="CASCADE"), nullable=True, index=True
    )
    brand_id: Mapped[str | None] = mapped_column(
        UUIDStr, ForeignKey("brands.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(16), default=SizeChartStatus.PENDING.value, nullable=False
    )
    #: ``ChartClassification`` dump
    classification: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    #: Raw ``ChartExtraction`` dump, as the model produced it
    extraction_json: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    #: ``NormalisedChart`` dump
    normalised: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    model_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Garment(Base, TimestampMixin):
    """A closet garment (``owner_user_id``) or one size of a product (``product_id`` +
    ``size_label``). Exactly one of the two parents is set."""

    __tablename__ = "garments"
    __table_args__ = (
        UniqueConstraint("product_id", "size_label", name="uq_garments_product_size"),
        Index("ix_garments_owner_reference", "owner_user_id", "is_reference"),
    )

    id: Mapped[str] = mapped_column(UUIDStr, primary_key=True, default=new_id)
    owner_user_id: Mapped[str | None] = mapped_column(
        UUIDStr, ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    product_id: Mapped[str | None] = mapped_column(
        UUIDStr, ForeignKey("products.id", ondelete="CASCADE"), nullable=True
    )
    size_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    cut: Mapped[str] = mapped_column(String(32), nullable=False)
    stretch_class: Mapped[str] = mapped_column(String(32), nullable=False)
    fit_tag: Mapped[str | None] = mapped_column(String(16), nullable=True)
    length_from_center_back: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sleeve_from_center_back: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    #: ``dict[GarmentField, MeasurementModel]`` dump
    measurements: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    is_reference: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)


class LandmarkCorrection(Base, TimestampMixin):
    __tablename__ = "landmark_corrections"

    id: Mapped[str] = mapped_column(UUIDStr, primary_key=True, default=new_id)
    garment_id: Mapped[str] = mapped_column(
        UUIDStr, ForeignKey("garments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    image_blob_key: Mapped[str] = mapped_column(String(512), nullable=False)
    proposed: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    corrected: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    scale_cm_per_px: Mapped[float] = mapped_column(Float, nullable=False)


class FitReportRow(Base, TimestampMixin):
    __tablename__ = "fit_reports"

    id: Mapped[str] = mapped_column(UUIDStr, primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        UUIDStr, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    body_record_id: Mapped[str | None] = mapped_column(
        UUIDStr, ForeignKey("body_records.id", ondelete="SET NULL"), nullable=True
    )
    product_id: Mapped[str] = mapped_column(
        UUIDStr, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reference_garment_id: Mapped[str | None] = mapped_column(
        UUIDStr, ForeignKey("garments.id", ondelete="SET NULL"), nullable=True
    )
    #: ``FitReportModel`` dump
    result: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    engine_version: Mapped[str] = mapped_column(String(32), nullable=False)


class PurchaseOutcome(Base, TimestampMixin):
    __tablename__ = "purchase_outcomes"

    id: Mapped[str] = mapped_column(UUIDStr, primary_key=True, default=new_id)
    fit_report_id: Mapped[str] = mapped_column(
        UUIDStr, ForeignKey("fit_reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        UUIDStr, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    size_bought: Mapped[str] = mapped_column(String(32), nullable=False)
    kept: Mapped[bool] = mapped_column(Boolean, nullable=False)
    problem_zone: Mapped[str | None] = mapped_column(String(16), nullable=True)
    direction: Mapped[str | None] = mapped_column(String(16), nullable=True)
