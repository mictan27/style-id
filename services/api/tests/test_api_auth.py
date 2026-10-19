from pathlib import Path
from typing import Any

from conftest import DEV_HEADERS, OTHER_HEADERS, RsaSigner, build_app, make_settings
from fastapi.testclient import TestClient


def test_dev_auth_creates_user_and_me_works(client: TestClient) -> None:
    r = client.get("/v1/me", headers=DEV_HEADERS)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["dob_verified_18"] is False
    assert body["preferences"] == {"shift_cm": {}}
    again = client.get("/v1/me", headers=DEV_HEADERS).json()
    assert again["id"] == body["id"]
    other = client.get("/v1/me", headers=OTHER_HEADERS).json()
    assert other["id"] != body["id"]


def test_unauthenticated_is_401(client: TestClient) -> None:
    r = client.get("/v1/me")
    assert r.status_code == 401
    assert r.headers["WWW-Authenticate"] == "Bearer"
    assert client.get("/v1/closet/garments").status_code == 401
    assert client.get("/v1/me", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_dev_auth_can_be_disabled(tmp_path: Path, jwks_store: dict[str, Any]) -> None:
    settings = make_settings(tmp_path)
    settings.dev_auth_enabled = False
    with TestClient(build_app(settings, jwks_store)) as c:
        assert c.get("/v1/me", headers=DEV_HEADERS).status_code == 401


def test_dev_auth_secret(tmp_path: Path, jwks_store: dict[str, Any]) -> None:
    settings = make_settings(tmp_path)
    settings.dev_auth_secret = "s3cret"
    with TestClient(build_app(settings, jwks_store)) as c:
        assert c.get("/v1/me", headers=DEV_HEADERS).status_code == 401
        ok = c.get("/v1/me", headers={**DEV_HEADERS, "X-Dev-Secret": "s3cret"})
        assert ok.status_code == 200


def test_apple_sign_in_issues_bearer_token(
    client: TestClient, jwks_store: dict[str, Any], signer: RsaSigner
) -> None:
    jwks_store.update(signer.jwks)
    r = client.post(
        "/v1/auth/apple",
        json={"identity_token": signer.identity_token(), "dob_verified_18": True},
    )
    assert r.status_code == 200, r.text
    token = r.json()
    assert token["token_type"] == "bearer" and token["is_new_user"] is True

    me = client.get("/v1/me", headers={"Authorization": f"Bearer {token['access_token']}"})
    assert me.status_code == 200, me.text
    assert me.json()["id"] == token["user_id"]
    assert me.json()["email"] == "alice@privaterelay.appleid.com"
    assert me.json()["dob_verified_18"] is True

    second = client.post(
        "/v1/auth/apple",
        json={"identity_token": signer.identity_token(), "dob_verified_18": False},
    )
    assert second.json()["is_new_user"] is False
    assert second.json()["user_id"] == token["user_id"]


def test_apple_sign_in_rejects_bad_tokens(
    client: TestClient, jwks_store: dict[str, Any], signer: RsaSigner
) -> None:
    jwks_store.update(signer.jwks)
    wrong_aud = signer.identity_token(aud="com.someone.else")
    r = client.post("/v1/auth/apple", json={"identity_token": wrong_aud, "dob_verified_18": True})
    assert r.status_code == 401
    other_key = RsaSigner(kid="other-kid").identity_token()
    r = client.post("/v1/auth/apple", json={"identity_token": other_key, "dob_verified_18": True})
    assert r.status_code == 401
    assert "kid" in r.json()["detail"]
