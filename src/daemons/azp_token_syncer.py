import asyncio
import json
import logging
import signal
from datetime import datetime
from logging import Logger, getLogger
from typing import TypedDict

from camoufox.async_api import AsyncCamoufox


class AuthState(TypedDict):
    authHeader: str
    expiresAt: int
    expiresInMs: int
    tokenType: str


class AZPTokenSyncerDaemon:

    def __init__(self, *, logger: Logger = getLogger("AZPTokenSyncerDaemon")):
        self.logger = logger
        self.auth_state: AuthState | None = None
        self.stop_requested = False
        self.stopped = False

    def get_auth_state(self) -> AuthState | None:
        if not self.auth_state:
            return None
        expires_at = datetime.fromtimestamp(self.auth_state["expiresAt"])
        if expires_at < datetime.now():
            return None
        return self.auth_state

    async def run(self):
        self.logger.info("Starting AZPTokenSyncerDaemon...")

        try:
            while not self.stop_requested:
                options = {
                    "headless": False,
                    "handle_sigint": False,
                    "handle_sigterm": False,
                    "handle_sighup": False,
                }
                try:
                    async with AsyncCamoufox(**options) as browser:
                        page = await browser.new_page()
                        await page.goto("https://portal.azure.com")

                        self.logger.info("Waiting for Azure Portal to be logged in by user...")
                        while not self.stop_requested:
                            try:
                                await page.wait_for_function(
                                    "window.location.href === 'https://portal.azure.com/#home'",
                                    timeout=2000,
                                )
                                break
                            except Exception:
                                if self.stop_requested:
                                    break
                                await asyncio.sleep(1)

                        if self.stop_requested:
                            break

                        while not self.stop_requested:
                            auth_state_raw = await page.evaluate(
                                'window.sessionStorage.getItem("authState")'
                            )
                            if auth_state_raw is None:
                                break

                            self.logger.info(
                                "Retrieved authState from sessionStorage. "
                                "Updating auth_state..."
                            )
                            auth_state: AuthState = json.loads(auth_state_raw)
                            self.auth_state = auth_state
                            if self.get_auth_state() is None:
                                break

                            self.logger.info(
                                "auth_state updated successfully. "
                                "Waiting for token to expire..."
                            )
                            expires_at = datetime.fromtimestamp(auth_state["expiresAt"])
                            while expires_at > datetime.now() and not self.stop_requested:
                                await asyncio.sleep(1)

                            if self.stop_requested:
                                break

                            self.logger.info("Token expired. Reloading page...")
                            await page.reload()
                            for _ in range(5):
                                if self.stop_requested:
                                    break
                                await asyncio.sleep(1)
                except Exception as e:
                    if self.stop_requested:
                        break
                    self.logger.error(f"Error in browser loop: {e}")
                    for _ in range(5):
                        if self.stop_requested:
                            break
                        await asyncio.sleep(1)
        finally:
            self.stopped = True
            self.logger.info("AZPTokenSyncerDaemon loop exited.")

    async def stop(self):
        if self.stopped:
            return
        self.stop_requested = True
        self.logger.info(
            "Stop requested for AZPTokenSyncerDaemon. Waiting for it to stop..."
        )
        timeout = 10
        while not self.stopped:
            if timeout <= 0:
                break
            await asyncio.sleep(1)
            timeout -= 1
        self.logger.info("AZPTokenSyncerDaemon stop sequence completed.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    async def main():
        daemon = AZPTokenSyncerDaemon()

        loop = asyncio.get_running_loop()
        def handle_exit():
            daemon.logger.info("Signal received, requesting stop...")
            daemon.stop_requested = True

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, handle_exit)
            except NotImplementedError:
                pass

        try:
            await daemon.run()
        finally:
            await daemon.stop()

    asyncio.run(main())
