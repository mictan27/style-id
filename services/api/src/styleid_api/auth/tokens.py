"""Our own session tokens: HS256 JWTs whose ``sub`` is the user id."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt

ALGORITHM = "HS256"


class InvalidToken(Exception):
    pass


def issue_token(user_id: str, *, secret: str, issuer: str, ttl_seconds: int) -> str:
    now = datetime.now(UTC)
    claims = {
        "sub": user_id,
        "iss": issuer,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl_seconds)).timestamp()),
    }
    return jwt.encode(claims, secret, algorithm=ALGORITHM)


def read_token(token: str, *, secret: str, issuer: str) -> str:
    """Return the user id or raise ``InvalidToken``."""
    try:
        claims = jwt.decode(token, secret, algorithms=[ALGORITHM], issuer=issuer)
    except JWTError as exc:
        raise InvalidToken(str(exc)) from exc
    sub = claims.get("sub")
    if not isinstance(sub, str) or not sub:
        raise InvalidToken("token has no subject")
    return sub
