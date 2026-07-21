from __future__ import annotations

try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    limiter = Limiter(key_func=get_remote_address)
    HAS_SLOWAPI = True
except ImportError:  # pragma: no cover - slowapi is a declared dependency
    HAS_SLOWAPI = False

    class _NullLimiter:
        """No-op stand-in so route decorators resolve even if slowapi is absent."""

        def limit(self, *_args, **_kwargs):
            def _decorator(fn):
                return fn

            return _decorator

    limiter = _NullLimiter()
