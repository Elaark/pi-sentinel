from datetime import timedelta

import pytest

from pi_sentinel.alerts import AlertTracker, find_problems, is_critical
from pi_sentinel.config import Config
from pi_sentinel.metrics import SystemMetrics

CONFIG = Config(discord_token="token", webhook_url="https://example.com")


def make_metrics(temperature: float | None = 50.0, disk_percent: float = 40.0) -> SystemMetrics:
    return SystemMetrics(
        temperature=temperature,
        cpu_percent=10.0,
        ram_percent=30.0,
        disk_percent=disk_percent,
        disk_free_gb=20.0,
        disk_total_gb=32.0,
        uptime=timedelta(hours=1),
    )


def test_no_problem_when_below_thresholds():
    assert find_problems(make_metrics(), CONFIG) == []


def test_overheating_detected_at_threshold():
    problems = find_problems(make_metrics(temperature=75.0), CONFIG)
    assert len(problems) == 1
    assert "Overheating" in problems[0]


def test_disk_and_temperature_problems_reported_together():
    problems = find_problems(make_metrics(temperature=80.0, disk_percent=95.0), CONFIG)
    assert len(problems) == 2


def test_missing_sensor_is_not_a_problem():
    assert find_problems(make_metrics(temperature=None), CONFIG) == []


@pytest.mark.parametrize(
    ("temperature", "expected"),
    [(None, False), (81.9, False), (82.0, True), (90.0, True)],
)
def test_is_critical(temperature, expected):
    assert is_critical(temperature, CONFIG) is expected


def test_tracker_alerts_once_then_stays_quiet():
    tracker = AlertTracker()
    problems = find_problems(make_metrics(temperature=76.0), CONFIG)
    assert "ANOMALY" in tracker.update(problems)
    # Same problem with a slightly different value: no new alert
    assert tracker.update(find_problems(make_metrics(temperature=77.0), CONFIG)) is None


def test_tracker_reports_new_problem_and_recovery():
    tracker = AlertTracker()
    tracker.update(find_problems(make_metrics(temperature=76.0), CONFIG))
    assert "Disk" in tracker.update(find_problems(make_metrics(temperature=76.0, disk_percent=95.0), CONFIG))
    assert "Back to normal" in tracker.update([])
    assert tracker.update([]) is None
