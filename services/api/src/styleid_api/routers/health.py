from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from .. import __version__

router = APIRouter(tags=["health"])


class HealthOut(BaseModel):
    status: str
    version: str


@router.get("/health")
def get_health() -> HealthOut:
    return HealthOut(status="ok", version=__version__)
