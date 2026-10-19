"""Sign in with Apple: verify an identity token against Apple's JWKS.

The verification is a pure function of (token, keys, client id, issuer) so tests can
sign a token with a throwaway RSA key and hand the matching JWK set in. The JWKS
provider is injected; production uses ``CachedJWKS`` over httpx.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx
from jose import JWTError, jwt

JWKSProvider = Callable[[], dict[str, Any]]
"""Returns ``{"keys": [...]}`` as served at https://appleid.apple.com/auth/keys."""

APPLE_ALGORITHMS = ["RS256"]


class AppleTokenError(Exception):
    pass


@dataclass(frozen=True)
class AppleClaims:
    sub: str
    email: str | None
    email_verified: bool


def _as_bool(value: object) -> bool:
    # Apple sends "true"/"false" strings in some tokens and real booleans in others.
    if isinstance(value, bool):
        return value
    return isinstance(value, str) and value.lower() == "true"


def verify_identity_token(
    token: str,
    *,
    jwks: dict[str, Any],
    client_id: str,
    issuer: str,
) -> AppleClaims:
    """Check signature (by ``kid``), ``iss``, ``aud`` and ``exp``; return the stable claims."""
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise AppleTokenError(f"malformed identity token: {exc}") from exc
    kid = header.get("kid")
    alg = header.get("alg")
    if alg not in APPLE_ALGORITHMS:
        raise AppleTokenError(f"unsupported algorithm {alg!r}")
    key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
    if key is None:
        raise AppleTokenError(f"no Apple signing key with kid={kid!r}")
    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=APPLE_ALGORITHMS,
            audience=client_id,
            issuer=issuer,
            options={"require_exp": True, "require_sub": True},
        )
    except JWTError as exc:
        raise AppleTokenError(f"identity token rejected: {exc}") from exc
    sub = claims.get("sub")
    if not isinstance(sub, str) or not sub:
        raise AppleTokenError("identity token has no subject")
    email = claims.get("email")
    return AppleClaims(
        sub=sub,
        email=email if isinstance(email, str) and email else None,
        email_verified=_as_bool(claims.get("email_verified", False)),
    )


class CachedJWKS:
    """Fetch Apple's JWKS with httpx and cache it for ``ttl_seconds``.

    ``refresh()`` forces a fetch, which callers use once when a ``kid`` is unknown
    (Apple rotates keys)."""

    def __init__(
        self,
        url: str,
        *,
        ttl_seconds: int = 3600,
        client: httpx.Client | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._url = url
        self._ttl = ttl_seconds
        self._client = client
        self._clock = clock
        self._cached: dict[str, Any] | None = None
        self._fetched_at = 0.0
        self._lock = threading.Lock()

    def _fetch(self) -> dict[str, Any]:
        client = self._client or httpx.Client(timeout=5.0)
        try:
            response = client.get(self._url)
            response.raise_for_status()
            data: dict[str, Any] = response.json()
        finally:
            if self._client is None:
                client.close()
        if "keys" not in data:
            raise AppleTokenError("Apple JWKS response has no 'keys'")
        return data

    def refresh(self) -> dict[str, Any]:
        with self._lock:
            self._cached = self._fetch()
            self._fetched_at = self._clock()
            return self._cached

    def __call__(self) -> dict[str, Any]:
        with self._lock:
            fresh = self._cached is not None and self._clock() - self._fetched_at < self._ttl
            if fresh and self._cached is not None:
                return self._cached
        return self.refresh()


class AppleVerifier:
    """Binds settings and a JWKS provider; retries once with fresh keys on unknown ``kid``."""

    def __init__(self, *, client_id: str, issuer: str, jwks: JWKSProvider) -> None:
        self._client_id = client_id
        self._issuer = issuer
        self._jwks = jwks

    def verify(self, token: str) -> AppleClaims:
        try:
            return verify_identity_token(
                token, jwks=self._jwks(), client_id=self._client_id, issuer=self._issuer
            )
        except AppleTokenError as exc:
            if "no Apple signing key" in str(exc) and isinstance(self._jwks, CachedJWKS):
                return verify_identity_token(
                    token,
                    jwks=self._jwks.refresh(),
                    client_id=self._client_id,
                    issuer=self._issuer,
                )
            raise
