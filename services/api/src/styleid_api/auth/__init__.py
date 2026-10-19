"""Authentication: dev header, Sign in with Apple, and our own bearer JWT."""

from .deps import CurrentUser, VerifiedAdult, get_current_user, require_age_verified

__all__ = ["CurrentUser", "VerifiedAdult", "get_current_user", "require_age_verified"]
