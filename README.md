# 🛰️ pi-sentinel

Monitor and protect a **Raspberry Pi 5** from Discord. A single async Python service lets you query and control the Pi with chat commands, sends alerts when something goes wrong (overheating, full disk, reboot), and shuts the machine down cleanly before the hardware gets damaged.

```
┌──────────────────────┐   !status / !ping / !shutdown   ┌──────────────────────────────┐
│    Discord server    │ ◄─────────────────────────────► │ Raspberry Pi 5               │
│                      │                                 │                              │
│  #monitoring  ◄──────┼──────── webhook alerts ──────── │ python -m pi_sentinel        │
└──────────────────────┘                                 │  ├─ commands  (discord.py)   │
                                                         │  ├─ status_check   every 5m  │
                                                         │  └─ watchdog       every 1m  │
                                                         └──────────────────────────────┘
```

## ✨ Features

### Commands

| Command     | Description                                                     | Access            |
|-------------|-----------------------------------------------------------------|-------------------|
| `!ping`     | Bot latency in milliseconds                                     | Everyone          |
| `!status`   | Embed with CPU temperature, CPU load, RAM, storage and uptime   | Everyone          |
| `!shutdown` | Clean shutdown of the Raspberry Pi                              | 🔒 Bot owner only |

### Background tasks

| Task               | Behaviour                                                                                                                          |
|--------------------|------------------------------------------------------------------------------------------------------------------------------------|
| **Status check**   | Alerts when temperature ≥ 75 °C or disk ≥ 90 %. Only reports *changes* (new problem, recovery), so a lasting issue does not spam the channel. |
| **Watchdog**       | At 82 °C, posts an emergency message and powers off the Pi. Starts before the Discord connection so it protects the hardware even when offline. |
| **Boot notice**    | On startup, tells apart a Pi reboot from a bot restart using the system uptime, and ignores Discord reconnections.                |

All thresholds and intervals can be changed in `.env`.

## 🧠 Technical highlights

- **asyncio end to end**: `discord.ext.tasks` loops, async webhook calls over a shared `aiohttp` session, blocking `psutil` sampling moved off the event loop with `asyncio.to_thread`, non-blocking `asyncio.create_subprocess_exec` for shutdown.
- **Separation of concerns**: the alert logic (`alerts.py`) is pure and has no I/O. The bot only wires metrics, logic and Discord together.
- **Typed, immutable data**: `dataclass(frozen=True)` for configuration and metrics snapshots, with type hints throughout.
- **Secure by default**: secrets come from the environment or a git-ignored `.env`, and `!shutdown` is restricted with `@commands.is_owner()`.
- **Tested and linted**: `pytest` covers the alert logic and config loading, and `ruff` handles linting and formatting.

## 🚀 Installation

On the Raspberry Pi (Raspberry Pi OS, Python 3.11+):

```bash
git clone https://github.com/Elaark/pi-sentinel.git
cd pi-sentinel

python3 -m venv .venv
source .venv/bin/activate
pip install .

cp .env.example .env
chmod 600 .env
nano .env   # fill in DISCORD_TOKEN and WEBHOOK_URL
```

### Discord setup

1. Create an application on the [Discord Developer Portal](https://discord.com/developers/applications), add a bot and copy its token into `DISCORD_TOKEN`.
2. Enable the **Message Content** intent in the *Bot* tab.
3. In your server: *Channel settings → Integrations → Webhooks*, create a webhook and copy its URL into `WEBHOOK_URL`.

### Shutdown permission

Both `!shutdown` and the watchdog run `sudo shutdown -h now`. Allow it without a password for the service user only:

```bash
echo "pi ALL=(root) NOPASSWD: /usr/sbin/shutdown" | sudo tee /etc/sudoers.d/pi-sentinel
sudo chmod 440 /etc/sudoers.d/pi-sentinel
```

### Running

```bash
python -m pi_sentinel   # or simply: pi-sentinel
```

To keep it running permanently, create `/etc/systemd/system/pi-sentinel.service`:

```ini
[Unit]
Description=pi-sentinel - Raspberry Pi monitoring over Discord
After=network-online.target
Wants=network-online.target

[Service]
User=pi
WorkingDirectory=/home/pi/pi-sentinel
ExecStart=/home/pi/pi-sentinel/.venv/bin/python -m pi_sentinel
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now pi-sentinel
journalctl -u pi-sentinel -f   # follow the logs
```

## 🧪 Development

```bash
pip install -e ".[dev]"
pytest
ruff check . && ruff format --check .
```

## 📁 Project structure

```
pi-sentinel/
├── pi_sentinel/
│   ├── __main__.py    # Entry point (python -m pi_sentinel)
│   ├── bot.py         # Discord bot, commands, background tasks, webhook
│   ├── alerts.py      # Pure alert logic (thresholds, change tracking)
│   ├── metrics.py     # System metrics with psutil
│   └── config.py      # .env / environment configuration
├── tests/             # pytest suite
├── pyproject.toml     # Packaging, dependencies, pytest and ruff config
└── .env.example       # Configuration template
```

## 🛠️ Tech stack

`Python 3.11+` · `asyncio` · `discord.py` · `aiohttp` · `psutil` · `pytest` · `ruff` · `systemd` · `Raspberry Pi 5`
