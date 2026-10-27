"""Discord bot: commands, background monitoring tasks and webhook alerts."""

import asyncio
import logging
import socket
from datetime import timedelta

import aiohttp
import discord
from discord.ext import commands, tasks

from . import metrics
from .alerts import AlertTracker, find_problems, is_critical
from .config import Config

log = logging.getLogger(__name__)

# The bot is considered started "at boot" if the Pi has been up for less than this
BOOT_GRACE_PERIOD = timedelta(minutes=5)


async def shutdown_system() -> None:
    """Power off the machine (requires a passwordless sudo rule for shutdown)."""
    process = await asyncio.create_subprocess_exec("sudo", "shutdown", "-h", "now")
    await process.wait()


class PiSentinel(commands.Bot):
    def __init__(self, config: Config) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.config = config
        self.alert_tracker = AlertTracker()
        self.session: aiohttp.ClientSession | None = None
        self.startup_notified = False

    async def setup_hook(self) -> None:
        self.session = aiohttp.ClientSession()
        self.status_check.change_interval(seconds=self.config.status_interval)
        self.watchdog.change_interval(seconds=self.config.watchdog_interval)
        # The watchdog does not wait for the Discord connection: it must protect the hardware regardless
        self.watchdog.start()
        self.status_check.start()
        await self.add_cog(Commands(self))

    async def close(self) -> None:
        self.watchdog.cancel()
        self.status_check.cancel()
        if self.session:
            await self.session.close()
        await super().close()

    async def notify(self, message: str) -> None:
        """Send a message to the monitoring channel through the webhook."""
        webhook = discord.Webhook.from_url(self.config.webhook_url, session=self.session)
        try:
            await webhook.send(message, username=f"pi-sentinel @ {socket.gethostname()}")
        except (discord.HTTPException, aiohttp.ClientError) as error:
            log.error("Failed to send webhook message: %s", error)

    async def on_ready(self) -> None:
        log.info("Connected as %s", self.user)
        # on_ready also fires after reconnections: only announce the first one
        if self.startup_notified:
            return
        self.startup_notified = True
        if metrics.uptime() < BOOT_GRACE_PERIOD:
            await self.notify("🚀 The Raspberry Pi just booted!")
        else:
            await self.notify("🔄 The monitoring bot was restarted.")

    @tasks.loop(seconds=300)
    async def status_check(self) -> None:
        snapshot = await asyncio.to_thread(metrics.collect)
        message = self.alert_tracker.update(find_problems(snapshot, self.config))
        if message:
            await self.notify(f"{message}\n- Local IP: {metrics.local_ip()}")

    @status_check.before_loop
    async def before_status_check(self) -> None:
        await self.wait_until_ready()

    @tasks.loop(seconds=60)
    async def watchdog(self) -> None:
        temperature = metrics.read_temperature()
        if not is_critical(temperature, self.config):
            return
        log.critical("Critical temperature %s °C, shutting down", temperature)
        await self.notify(
            "🚨 **EMERGENCY SYSTEM SHUTDOWN** 🚨\n"
            f"The Raspberry Pi reached **{temperature} °C**. "
            "Shutting down cleanly to prevent hardware damage."
        )
        await shutdown_system()


class Commands(commands.Cog):
    def __init__(self, bot: PiSentinel) -> None:
        self.bot = bot

    @commands.command()
    async def ping(self, ctx: commands.Context) -> None:
        """Show the bot latency."""
        await ctx.send(f"🏓 Pong! Latency: {round(self.bot.latency * 1000)} ms.")

    @commands.command()
    async def status(self, ctx: commands.Context) -> None:
        """Show the Raspberry Pi health."""
        # psutil blocks while sampling the CPU, so run it outside the event loop
        snapshot = await asyncio.to_thread(metrics.collect)
        temperature = f"{snapshot.temperature} °C" if snapshot.temperature is not None else "N/A"

        embed = discord.Embed(title="📊 Raspberry Pi 5 status", color=discord.Color.brand_green())
        embed.add_field(name="🌡️ Temperature", value=f"**{temperature}**")
        embed.add_field(name="🧠 CPU", value=f"**{snapshot.cpu_percent} %**")
        embed.add_field(name="🐏 RAM", value=f"**{snapshot.ram_percent} %**")
        embed.add_field(
            name="💾 Storage",
            value=f"{snapshot.disk_free_gb} GB free of {snapshot.disk_total_gb} GB "
            f"(**{snapshot.disk_percent} %** used)",
            inline=False,
        )
        embed.add_field(name="⏱️ Uptime", value=str(snapshot.uptime), inline=False)
        await ctx.send(embed=embed)

    @commands.command()
    @commands.is_owner()  # 🔒 only the bot owner can power off the Pi
    async def shutdown(self, ctx: commands.Context) -> None:
        """Power off the Raspberry Pi."""
        await ctx.send("⚠️ Shutting down the Raspberry Pi... Good night! 💤")
        await shutdown_system()

    @shutdown.error
    async def shutdown_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.NotOwner):
            await ctx.send("⛔ Only the bot owner can use this command.")
        else:
            raise error
