"""Logging + Sentry setup shared by the API and the worker."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from app import __version__
from app.config import Settings


class JsonFormatter(logging.Formatter):
    """One JSON object per line — what log shippers (Azure Monitor, Datadog, …) want."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def setup_observability(settings: Settings, *, component: str) -> None:
    handler = logging.StreamHandler()
    if settings.log_format == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.log_level.upper())

    if settings.sentry_dsn:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            release=f"ahoy-api@{__version__}",
            traces_sample_rate=settings.sentry_traces_sample_rate,
            send_default_pii=False,  # Captains' phone numbers / emails stay out of Sentry
        )
        sentry_sdk.set_tag("component", component)
