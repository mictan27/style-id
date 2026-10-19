"""Products: the thing the shopper is looking at, keyed by canonical URL."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from styleid_schema import GarmentKind

from ..auth import CurrentUser
from ..db.models import Brand, Product, SizeChart, SizeChartStatus
from ..db.session import get_db
from ..jobs.extraction import ExtractionRunner
from ..schemas import ProductOut, latest_chart, product_out
from ..urls import canonicalise_url, domain_of

router = APIRouter(prefix="/products", tags=["products"])

DB = Annotated[Session, Depends(get_db)]

_RETRYABLE = {SizeChartStatus.FAILED.value, SizeChartStatus.NOT_FOUND.value}


class ProductCheckIn(BaseModel):
    url: str = Field(min_length=4, max_length=2048, description="The product page URL as shared")
    garment_kind: GarmentKind = GarmentKind.TEE
    refresh: bool = Field(default=False, description="Re-run extraction even if a chart exists")


def get_runner(request: Request) -> ExtractionRunner:
    runner: ExtractionRunner = request.app.state.extraction_runner
    return runner


def find_or_create_brand(db: Session, domain: str) -> Brand:
    brand = db.scalar(select(Brand).where(Brand.domain == domain))
    if brand is None:
        brand = Brand(name=domain, domain=domain, seeded=False)
        db.add(brand)
        db.flush()
    return brand


@router.post("/check")
def check_product(
    payload: ProductCheckIn,
    user: CurrentUser,
    db: DB,
    runner: Annotated[ExtractionRunner, Depends(get_runner)],
) -> ProductOut:
    """Canonicalise the URL, find or create the product, and make sure a size chart has
    been extracted (or is being extracted). Idempotent for the same product."""
    canonical = canonicalise_url(payload.url)
    domain = domain_of(canonical)
    if not domain or "." not in domain:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="url has no host")

    product = db.scalar(select(Product).where(Product.url_canonical == canonical))
    if product is None:
        brand = find_or_create_brand(db, domain)
        product = Product(
            brand_id=brand.id,
            url_canonical=canonical,
            url_original=payload.url,
            garment_kind=payload.garment_kind.value,
        )
        db.add(product)
        db.commit()
        db.refresh(product)

    chart = latest_chart(db, product)
    needs_run = payload.refresh or chart is None or chart.status in _RETRYABLE
    if needs_run:
        chart = SizeChart(
            product_id=product.id,
            brand_id=product.brand_id,
            status=SizeChartStatus.PENDING.value,
        )
        db.add(chart)
        db.commit()
        chart_id = chart.id
        runner.run(chart_id)
        # The runner used its own session; drop ours so we read what it wrote.
        db.expire_all()
        refreshed = db.get(Product, product.id)
        if refreshed is None:  # pragma: no cover - the product cannot vanish mid-request
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="product not found")
        product = refreshed
    return product_out(db, product)


@router.get("/{product_id}")
def get_product(product_id: str, user: CurrentUser, db: DB) -> ProductOut:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="product not found")
    return product_out(db, product)
