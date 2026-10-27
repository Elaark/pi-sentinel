"""Pure alert logic: decides what to report, without any I/O."""

from .config import Config
from .metrics import SystemMetrics


def find_problems(metrics: SystemMetrics, config: Config) -> list[str]:
    """Return a human-readable line for each threshold that is exceeded."""
    problems = []
    if metrics.temperature is not None and metrics.temperature >= config.temp_warning:
        problems.append(f"🌡️ **Overheating:** {metrics.temperature} °C")
    if metrics.disk_percent >= config.disk_warning:
        problems.append(f"💾 **Disk almost full:** {metrics.disk_percent} % used")
    return problems


def is_critical(temperature: float | None, config: Config) -> bool:
    return temperature is not None and temperature >= config.temp_critical


class AlertTracker:
    """Only reports changes, so a lasting problem does not spam the channel every check."""

    def __init__(self) -> None:
        self._active: list[str] = []

    def update(self, problems: list[str]) -> str | None:
        """Return the message to send for this check, or None if nothing changed."""
        # Compare problem categories (the emoji prefix), not the exact values
        previous = {p.split()[0] for p in self._active}
        current = {p.split()[0] for p in problems}
        self._active = problems

        if current == previous:
            return None
        if not problems:
            return "✅ **Back to normal:** all metrics are below their thresholds."
        return "\n".join(["⚠️ **ANOMALY DETECTED** ⚠️", *(f"- {p}" for p in problems)])
