"""Unit tests for Apple identity-token verification with a locally generated RSA key."""

from typing import Any

import httpx
import pytest
from conftest import APPLE_CLIENT_ID, APPLE_ISSUER, RsaSigner

from styleid_api.auth.apple import (
    AppleTokenError,
    AppleVerifier,
    CachedJWKS,
    verify_identity_token,
)


def verify(token: str, jwks: dict[str, Any]) -> Any:
    return verify_identity_token(token, jwks=jwks, client_id=APPLE_CLIENT_ID, issuer=APPLE_ISSUER)


def test_valid_token(signer: RsaSigner) -> None:
    claims = verify(signer.identity_token(sub="001.sub"), signer.jwks)
    assert claims.sub == "001.sub"
    assert claims.email == "alice@privaterelay.appleid.com"
    assert claims.email_verified is True


def test_expired_token(signer: RsaSigner) -> None:
    with pytest.raises(AppleTokenError, match="rejected"):
        verify(signer.identity_token(expires_in=-60), signer.jwks)


def test_wrong_audience_and_issuer(signer: RsaSigner) -> None:
    with pytest.raises(AppleTokenError):
        verify(signer.identity_token(aud="com.other"), signer.jwks)
    with pytest.raises(AppleTokenError):
        verify(signer.identity_token(iss="https://evil.example"), signer.jwks)


def test_unknown_kid_and_wrong_key(signer: RsaSigner) -> None:
    with pytest.raises(AppleTokenError, match="kid"):
        verify(signer.identity_token(kid="missing"), signer.jwks)
    impostor = RsaSigner(kid=signer.kid)  # same kid, different key
    with pytest.raises(AppleTokenError, match="rejected"):
        verify(impostor.identity_token(), signer.jwks)


def test_garbage_token(signer: RsaSigner) -> None:
    with pytest.raises(AppleTokenError, match="malformed"):
        verify("not.a.jwt", signer.jwks)


def test_cached_jwks_fetches_once_and_refreshes(signer: RsaSigner) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=signer.jwks)

    now = [1000.0]
    jwks = CachedJWKS(
        "https://appleid.apple.com/auth/keys",
        ttl_seconds=60,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        clock=lambda: now[0],
    )
    assert jwks()["keys"][0]["kid"] == signer.kid
    assert jwks()["keys"][0]["kid"] == signer.kid
    assert calls == 1
    now[0] += 61
    jwks()
    assert calls == 2

    verifier = AppleVerifier(client_id=APPLE_CLIENT_ID, issuer=APPLE_ISSUER, jwks=jwks)
    assert verifier.verify(signer.identity_token()).sub == "001234.abcdef"
    # Unknown kid triggers exactly one forced refresh before giving up.
    with pytest.raises(AppleTokenError, match="kid"):
        verifier.verify(signer.identity_token(kid="rotated"))
    assert calls == 3
