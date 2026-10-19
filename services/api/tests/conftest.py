"""Shared fixtures: a SQLite app with dev auth, a fake chart extractor and a local JWKS."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jose import jwk, jwt

from styleid_api.config import Settings
from styleid_api.db.session import create_all, make_engine
from styleid_api.main import create_app
from styleid_schema import (
    ChartClassification,
    ChartStatus,
    Confidence,
    Cut,
    GarmentKind,
    GarmentModel,
    NormalisedChart,
    Source,
    StretchClass,
)

DEV_HEADERS = {"X-Dev-User": "alice"}
OTHER_HEADERS = {"X-Dev-User": "bob"}
APPLE_CLIENT_ID = "id.style.test"
APPLE_ISSUER = "https://appleid.apple.com"

GREY_TEE: dict[str, Any] = {
    "kind": "tee",
    "cut": "set_in",
    "stretch": "cotton_jersey",
    "size_label": "M",
    "fit_tag": "regular",
    "name": "grey tee",
    "is_reference": True,
    "measurements": {
        "chest_width": {"value_cm": 50, "source": "flatlay", "confidence": "high"},
        "shoulder_width": {"value_cm": 44, "source": "flatlay", "confidence": "high"},
        "length": {"value_cm": 70, "source": "flatlay", "confidence": "high"},
    },
}

AVG_BODY: dict[str, Any] = {
    "source": "lidar",
    "measurements": {
        "height": {"value_cm": 178, "source": "lidar", "confidence": "high"},
        "neck": {"value_cm": 39, "source": "lidar", "confidence": "high"},
        "shoulder": {"value_cm": 44, "source": "lidar", "confidence": "high"},
        "chest": {"value_cm": 96, "source": "lidar", "confidence": "medium"},
        "waist": {"value_cm": 84, "source": "lidar", "confidence": "high"},
        "hip": {"value_cm": 98, "source": "lidar", "confidence": "high"},
        "arm_length": {"value_cm": 62, "source": "lidar", "confidence": "high"},
        "bicep": {"value_cm": 31, "source": "lidar", "confidence": "high"},
        "back_length": {"value_cm": 46, "source": "lidar", "confidence": "high"},
    },
    "landmarks": {"waist_line_cm": 44, "hip_line_cm": 64, "wrist_cm": 78},
}

CHART_SIZES = {
    "S": {"chest_width": 48, "shoulder_width": 42, "hem_width": 47, "length": 68},
    "M": {"chest_width": 50, "shoulder_width": 44, "hem_width": 49, "length": 70},
    "L": {"chest_width": 52, "shoulder_width": 46, "hem_width": 51, "length": 72},
}


def fake_extract(url: str, garment_kind: GarmentKind) -> NormalisedChart:
    """Stands in for ``styleid_charts.pipeline.extract_product``: three cotton-jersey sizes."""
    sizes = [
        GarmentModel(
            kind=garment_kind,
            cut=Cut.SET_IN,
            stretch=StretchClass.COTTON_JERSEY,
            size_label=label,
            measurements={
                field: {"value_cm": value, "source": Source.CHART, "confidence": Confidence.HIGH}  # type: ignore[misc]
                for field, value in fields.items()
            },
        )
        for label, fields in CHART_SIZES.items()
    ]
    return NormalisedChart(
        status=ChartStatus.OK,
        classification=ChartClassification(chart_kind="garment", measure_basis="flat", unit="cm"),
        stretch=StretchClass.COTTON_JERSEY,
        fabric_composition="100% cotton",
        sizes=sizes,
        warnings=[],
        model_id="fake-extractor",
    )


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        database_url=f"sqlite+pysqlite:///{tmp_path / 'test.db'}",
        dev_auth_enabled=True,
        jwt_secret="test-secret",
        apple_client_id=APPLE_CLIENT_ID,
        apple_issuer=APPLE_ISSUER,
    )


def build_app(settings: Settings, jwks_store: dict[str, Any], **kwargs: Any) -> FastAPI:
    engine = make_engine(settings.database_url)
    create_all(engine)
    kwargs.setdefault("extract_fn", fake_extract)
    return create_app(settings, engine=engine, jwks_provider=lambda: jwks_store, **kwargs)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return make_settings(tmp_path)


@pytest.fixture
def jwks_store() -> dict[str, Any]:
    return {"keys": []}


@pytest.fixture
def app(settings: Settings, jwks_store: dict[str, Any]) -> FastAPI:
    return build_app(settings, jwks_store)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


# --- Apple helpers ------------------------------------------------------------------


class RsaSigner:
    def __init__(self, kid: str = "test-kid") -> None:
        self.kid = kid
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.private_pem = key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode()
        public_pem = (
            key.public_key()
            .public_bytes(
                serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
            )
            .decode()
        )
        public = jwk.construct(public_pem, "RS256").to_dict()
        public["kid"] = kid
        public["use"] = "sig"
        self.public_jwk = {
            k: (v.decode() if isinstance(v, bytes) else v) for k, v in public.items()
        }

    @property
    def jwks(self) -> dict[str, Any]:
        return {"keys": [self.public_jwk]}

    def identity_token(
        self,
        sub: str = "001234.abcdef",
        *,
        aud: str = APPLE_CLIENT_ID,
        iss: str = APPLE_ISSUER,
        email: str | None = "alice@privaterelay.appleid.com",
        expires_in: int = 600,
        kid: str | None = None,
    ) -> str:
        now = datetime.now(UTC)
        claims: dict[str, Any] = {
            "iss": iss,
            "aud": aud,
            "sub": sub,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
        }
        if email:
            claims["email"] = email
            claims["email_verified"] = "true"
        return jwt.encode(
            claims, self.private_pem, algorithm="RS256", headers={"kid": kid or self.kid}
        )


@pytest.fixture
def signer() -> RsaSigner:
    return RsaSigner()


# --- flow helpers -------------------------------------------------------------------


def verify_age(client: TestClient, headers: dict[str, str] = DEV_HEADERS) -> None:
    r = client.patch("/v1/me", json={"dob_verified_18": True}, headers=headers)
    assert r.status_code == 200, r.text


def check_product(
    client: TestClient, url: str = "https://shop.example.com/products/tee", **extra: Any
) -> dict[str, Any]:
    r = client.post("/v1/products/check", json={"url": url, **extra}, headers=DEV_HEADERS)
    assert r.status_code == 200, r.text
    data: dict[str, Any] = r.json()
    return data


def add_grey_tee(client: TestClient) -> dict[str, Any]:
    r = client.post("/v1/closet/garments", json=GREY_TEE, headers=DEV_HEADERS)
    assert r.status_code == 201, r.text
    data: dict[str, Any] = r.json()
    return data
