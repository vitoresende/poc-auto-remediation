from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from sentry_sdk.transport import Transport

from dummy_app.config import settings

LOCAL_FALLBACK_DSN = "https://00000000000000000000000000000000@local.sentry.invalid/1"

_RECENT_EVENTS: list[dict[str, Any]] = []
_MAX_RECENT_EVENTS = 25


class LocalOfflineTransport(Transport):
    """No-op transport used when no remote SENTRY_DSN is configured so Sentry SDK still builds full events."""

    def capture_envelope(self, envelope: Any) -> None:
        return None


def _json_default(obj: Any) -> str:
    """Fallback serializer for non-JSON-native objects in Sentry event dicts."""
    return repr(obj)


def _persist_event_fixture(event: dict[str, Any]) -> dict[str, str]:
    """Save the full Sentry event payload to fixtures/ for Package 1.3 & Package 2 testing."""
    fixtures_dir: Path = settings.fixtures_dir
    captured_dir: Path = fixtures_dir / "captured"
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    captured_dir.mkdir(parents=True, exist_ok=True)

    tags = event.get("tags") or {}
    scenario_slug = str(tags.get("scenario_slug") or "unclassified").replace("/", "_")
    event_id = str(event.get("event_id") or "unknown")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    canonical_path = fixtures_dir / f"sentry_{scenario_slug}.json"
    timestamped_path = captured_dir / f"{timestamp}_{scenario_slug}_{event_id[:8]}.json"

    serialized = json.dumps(event, indent=2, ensure_ascii=False, default=_json_default)
    canonical_path.write_text(serialized, encoding="utf-8")
    timestamped_path.write_text(serialized, encoding="utf-8")

    return {
        "canonical_fixture": str(canonical_path.relative_to(fixtures_dir.parent)),
        "timestamped_fixture": str(timestamped_path.relative_to(fixtures_dir.parent)),
    }


def _before_send(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
    """Intercept outgoing Sentry events to record local JSON fixtures while preserving PII."""
    del hint
    saved_paths: dict[str, str] = {}
    if settings.capture_local_fixtures:
        saved_paths = _persist_event_fixture(event)

    summary_entry = {
        "event_id": event.get("event_id"),
        "timestamp": event.get("timestamp"),
        "level": event.get("level"),
        "transaction": event.get("transaction"),
        "scenario_slug": (event.get("tags") or {}).get("scenario_slug", "unknown"),
        "sent_to_remote_sentry": bool(settings.sentry_dsn),
        "saved_paths": saved_paths,
        "event": json.loads(json.dumps(event, default=_json_default)),
    }
    _RECENT_EVENTS.insert(0, summary_entry)
    if len(_RECENT_EVENTS) > _MAX_RECENT_EVENTS:
        _RECENT_EVENTS.pop()

    return event


def init_sentry(custom_dsn: str | None = None) -> dict[str, Any]:
    """Initialize or re-initialize Sentry SDK with full PII and local variable capture enabled."""
    if custom_dsn is not None:
        settings.sentry_dsn = custom_dsn.strip()

    has_remote_dsn = bool(settings.sentry_dsn)
    active_dsn = settings.sentry_dsn if has_remote_dsn else LOCAL_FALLBACK_DSN

    init_kwargs: dict[str, Any] = {
        "dsn": active_dsn,
        "environment": settings.sentry_environment,
        "release": settings.sentry_release,
        "send_default_pii": True,
        "include_local_variables": True,
        "max_breadcrumbs": 100,
        "attach_stacktrace": True,
        "max_value_length": 4096,
        "before_send": _before_send,
        "integrations": [
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
        ],
    }

    if not has_remote_dsn:
        init_kwargs["transport"] = LocalOfflineTransport

    sentry_sdk.init(**init_kwargs)
    return get_sentry_status()


def get_sentry_status() -> dict[str, Any]:
    """Return current Sentry configuration status."""
    has_remote_dsn = bool(settings.sentry_dsn)
    masked_dsn = ""
    if has_remote_dsn:
        dsn = settings.sentry_dsn
        masked_dsn = f"{dsn[:18]}...{dsn[-12:]}" if len(dsn) > 32 else "***configured***"

    return {
        "remote_sentry_enabled": has_remote_dsn,
        "masked_dsn": masked_dsn,
        "environment": settings.sentry_environment,
        "release": settings.sentry_release,
        "send_default_pii": True,
        "include_local_variables": True,
        "capture_local_fixtures": settings.capture_local_fixtures,
        "fixtures_dir": str(settings.fixtures_dir),
    }


def get_recent_events() -> list[dict[str, Any]]:
    """Return in-memory list of recently captured Sentry events."""
    return list(_RECENT_EVENTS)


def get_last_event_for_scenario(scenario_slug: str) -> dict[str, Any] | None:
    """Return the most recent captured event matching a scenario slug."""
    for entry in _RECENT_EVENTS:
        if entry.get("scenario_slug") == scenario_slug:
            return entry
    return _RECENT_EVENTS[0] if _RECENT_EVENTS else None
