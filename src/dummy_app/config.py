from dataclasses import dataclass, field
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_FIXTURES_DIR = BASE_DIR / "fixtures"

load_dotenv(BASE_DIR / ".env")


@dataclass
class AppConfig:
    """Runtime configuration for the Sentry Dummy App."""

    sentry_dsn: str = field(default_factory=lambda: os.environ.get("SENTRY_DSN", "").strip())
    sentry_environment: str = field(
        default_factory=lambda: os.environ.get("SENTRY_ENVIRONMENT", "sandbox")
    )
    sentry_release: str = field(
        default_factory=lambda: os.environ.get("SENTRY_RELEASE", "dummy-app@0.1.0")
    )
    capture_local_fixtures: bool = field(
        default_factory=lambda: os.environ.get("CAPTURE_LOCAL_FIXTURES", "true").lower()
        in ("1", "true", "yes")
    )
    fixtures_dir: Path = field(
        default_factory=lambda: Path(os.environ.get("FIXTURES_DIR", str(DEFAULT_FIXTURES_DIR)))
    )


settings = AppConfig()
