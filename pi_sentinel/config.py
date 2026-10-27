"""Configuration loaded from environment variables and an optional .env file."""

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_env_file(path: Path) -> None:
    """Load KEY=VALUE lines into os.environ without overriding existing variables."""
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


@dataclass(frozen=True)
class Config:
    discord_token: str
    webhook_url: str
    temp_warning: float = 75.0  # °C, triggers an alert
    temp_critical: float = 82.0  # °C, triggers an emergency shutdown
    disk_warning: float = 90.0  # %, triggers an alert
    status_interval: int = 300  # seconds between alert checks
    watchdog_interval: int = 60  # seconds between temperature checks

    @classmethod
    def from_env(cls, env_file: Path = PROJECT_ROOT / ".env") -> "Config":
        load_env_file(env_file)
        missing = [key for key in ("DISCORD_TOKEN", "WEBHOOK_URL") if not os.environ.get(key)]
        if missing:
            raise SystemExit(f"❌ Missing {', '.join(missing)}: create a .env file (see .env.example)")

        return cls(
            discord_token=os.environ["DISCORD_TOKEN"],
            webhook_url=os.environ["WEBHOOK_URL"],
            temp_warning=float(os.environ.get("TEMP_WARNING", cls.temp_warning)),
            temp_critical=float(os.environ.get("TEMP_CRITICAL", cls.temp_critical)),
            disk_warning=float(os.environ.get("DISK_WARNING", cls.disk_warning)),
            status_interval=int(os.environ.get("STATUS_INTERVAL", cls.status_interval)),
            watchdog_interval=int(os.environ.get("WATCHDOG_INTERVAL", cls.watchdog_interval)),
        )
