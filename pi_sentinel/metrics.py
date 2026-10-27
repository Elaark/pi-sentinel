"""System metrics collection with psutil."""

import socket
import time
from dataclasses import dataclass
from datetime import timedelta

import psutil

THERMAL_SENSOR = "cpu_thermal"  # Raspberry Pi CPU sensor name


@dataclass(frozen=True)
class SystemMetrics:
    temperature: float | None  # °C, None if the sensor is unavailable
    cpu_percent: float
    ram_percent: float
    disk_percent: float
    disk_free_gb: float
    disk_total_gb: float
    uptime: timedelta


def read_temperature() -> float | None:
    """Return the CPU temperature in °C, or None if it cannot be read."""
    try:
        sensors = psutil.sensors_temperatures()
    except (AttributeError, OSError):
        return None
    if THERMAL_SENSOR not in sensors or not sensors[THERMAL_SENSOR]:
        return None
    return round(sensors[THERMAL_SENSOR][0].current, 1)


def uptime() -> timedelta:
    return timedelta(seconds=int(time.time() - psutil.boot_time()))


def collect(cpu_sample_seconds: float = 0.5) -> SystemMetrics:
    """Take a snapshot of the system. Blocks for `cpu_sample_seconds`."""
    disk = psutil.disk_usage("/")
    return SystemMetrics(
        temperature=read_temperature(),
        cpu_percent=psutil.cpu_percent(interval=cpu_sample_seconds),
        ram_percent=psutil.virtual_memory().percent,
        disk_percent=disk.percent,
        disk_free_gb=round(disk.free / 1024**3, 1),
        disk_total_gb=round(disk.total / 1024**3, 1),
        uptime=uptime(),
    )


def local_ip() -> str:
    """Return the LAN IP address (no packet is actually sent)."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            sock.connect(("10.255.255.255", 1))
            return sock.getsockname()[0]
        except OSError:
            return "unknown"
