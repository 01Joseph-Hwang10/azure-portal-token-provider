import asyncio
import logging
import os
import signal
from datetime import datetime, timedelta, timezone
from logging import Logger, getLogger

import httpx

from src.config.settings import Settings


class HealthCheckDaemon:
    def __init__(self, *, logger: Logger = getLogger("HealthCheckDaemon")):
        self.logger = logger
        self.client = httpx.AsyncClient()
        self.stop_requested = False
        self.stopped = False

    async def run(self):
        self.logger.info("Starting HealthCheckDaemon...")

        try:
            while not self.stop_requested:
                settings = Settings()
                try:
                    self.logger.info(
                        f"Pinging {settings.health_check_url} " "for health check..."
                    )
                    response = await self.client.get(settings.health_check_url)
                    response.raise_for_status()
                except Exception as e:
                    self.logger.warning(
                        f"Failed to ping {settings.health_check_url}: {e}"
                    )
                next_ping_time = datetime.now(tz=timezone.utc) + timedelta(
                    seconds=settings.health_check_interval
                )
                self.logger.info(f"Next ping scheduled at {next_ping_time.isoformat()}")
                while (
                    not self.stop_requested
                    and datetime.now(tz=timezone.utc) < next_ping_time
                ):
                    await asyncio.sleep(1)
        finally:
            self.stopped = True
            self.logger.info("HealthCheckDaemon loop exited.")

    async def stop(self):
        if self.stopped:
            return
        self.stop_requested = True
        self.logger.info(
            "Stop requested for HealthCheckDaemon. Waiting for it to stop..."
        )
        timeout = 10
        while not self.stopped:
            if timeout <= 0:
                break
            await asyncio.sleep(1)
            timeout -= 1
        self.logger.info("HealthCheckDaemon stop sequence completed.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    async def main():
        daemon = HealthCheckDaemon()

        loop = asyncio.get_running_loop()

        def handle_exit():
            daemon.logger.info("Signal received, requesting stop...")
            daemon.stop_requested = True

        if os.name != "nt":
            for sig in (signal.SIGINT, signal.SIGTERM):
                try:
                    loop.add_signal_handler(sig, handle_exit)
                except NotImplementedError:
                    pass
        else:
            def handle_exit_win(sig, frame):
                daemon.logger.info(f"Signal {sig} received, requesting stop...")
                daemon.stop_requested = True

            signal.signal(signal.SIGINT, handle_exit_win)
            signal.signal(signal.SIGTERM, handle_exit_win)

        try:
            await daemon.run()
        except (KeyboardInterrupt, asyncio.CancelledError):
            daemon.logger.info("Daemon interrupted.")
            daemon.stop_requested = True
        finally:
            await daemon.stop()

    asyncio.run(main())
