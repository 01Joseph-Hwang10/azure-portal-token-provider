import asyncio
import logging
import signal
from datetime import datetime, timezone
from logging import Logger, getLogger
from typing import Any

from playwright.async_api import async_playwright


class AZPTokenSyncerDaemon:

    def __init__(self, *, logger: Logger = getLogger("AZPTokenSyncerDaemon")):
        self.logger = logger
        self.auth_state: dict[str, Any] | None = None
        self.stop_requested = False
        self.stopped = False

    def get_token(self) -> str | None:
        if not self.auth_state:
            return None
        expires_at = datetime.fromtimestamp(
            int(self.auth_state["expiresOn"]), tz=timezone.utc
        )
        if expires_at < datetime.now(tz=timezone.utc):
            return None
        return self.auth_state["secret"]

    def get_expires_at(self) -> datetime | None:
        if not self.auth_state:
            return None
        return datetime.fromtimestamp(
            int(self.auth_state["expiresOn"]), tz=timezone.utc
        )

    async def run(self):
        self.logger.info("Starting AZPTokenSyncerDaemon...")

        try:
            while not self.stop_requested:
                try:
                    async with async_playwright() as p:
                        browser = await p.firefox.launch(
                            headless=False,
                            handle_sigint=False,
                            handle_sigterm=False,
                            handle_sighup=False,
                        )
                        context = await browser.new_context()
                        page = await context.new_page()
                        await page.goto("https://portal.azure.com")

                        self.logger.info(
                            "Waiting for Azure Portal to be logged in by user..."
                        )
                        while not self.stop_requested:
                            try:
                                await page.wait_for_function(
                                    "() => window.location.href === 'https://portal.azure.com/#home'",  # noqa: E501
                                    timeout=2000,
                                )
                                break
                            except Exception:
                                if self.stop_requested:
                                    break
                                await asyncio.sleep(1)

                        if self.stop_requested:
                            break

                        self.logger.info(
                            "Azure Portal logged in. Starting token sync loop..."
                        )

                        while not self.stop_requested:
                            auth_state = None
                            while not self.stop_requested and auth_state is None:
                                try:
                                    auth_state = await page.evaluate(
                                        'Object.entries(window.sessionStorage).filter(([key]) => key.includes("accesstoken")).map(([key, value]) => [key, JSON.parse(value)]).filter(([key, value]) => key.includes("management.core.windows.net")).map(([, value]) => value).at(0)'  # noqa: E501
                                    )
                                    if auth_state is None:
                                        await asyncio.sleep(1)
                                except Exception as e:
                                    if "Execution context was destroyed" in str(e):
                                        self.logger.debug(
                                            "Execution context destroyed during "
                                            "evaluation, retrying..."
                                        )
                                        await asyncio.sleep(1)
                                        continue
                                    raise

                            self.logger.info(
                                "Retrieved authState from sessionStorage. "
                                "Updating auth_state..."
                            )

                            # It looks like:
                            # {
                            #     "homeAccountId": "c0ec2ea0-4379-4793-92bf-85cab79759e0.e8715ec0-6179-432a-a864-54ea4008adc2", # noqa: E501
                            #     "credentialType": "AccessToken",
                            #     "secret": "<token>",
                            #     "cachedAt": "1783920384",
                            #     "expiresOn": "1783925614",
                            #     "extendedExpiresOn": "1783930844",
                            #     "environment": "login.windows.net",
                            #     "clientId": "c44b4083-3bb0-49c1-b47d-974e53cbdf3c",
                            #     "realm": "e8715ec0-6179-432a-a864-54ea4008adc2",
                            #     "target": "https://management.core.windows.net//user_impersonation https://management.core.windows.net//.default", # noqa: E501
                            #     "tokenType": "Bearer",
                            #     "lastUpdatedAt": "1783920384131"
                            # }
                            self.auth_state = auth_state

                            self.logger.info(
                                "auth_state updated successfully. "
                                "Waiting for token to expire..."
                            )
                            expires_at = datetime.fromtimestamp(
                                int(auth_state["expiresOn"]),
                                tz=timezone.utc,
                            )
                            while (
                                expires_at > datetime.now(tz=timezone.utc)
                                and not self.stop_requested
                            ):
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
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
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
