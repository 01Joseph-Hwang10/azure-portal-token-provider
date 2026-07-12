import asyncio
import json
from datetime import datetime
from typing import TypedDict

from camoufox.async_api import AsyncCamoufox


class AZPTokenSyncerDaemon:

    def __init__(self):
        self.auth_state: AuthState | None = None
        self.stop_requested = False
        self.stopped = False

    def get_auth_state(self) -> "AuthState" | None:
        if not self.auth_state:
            return None
        expires_at = datetime.fromtimestamp(self.auth_state["expiresAt"])
        if expires_at < datetime.now():
            return None
        return self.auth_state

    async def run(self):
        while True:
            async with AsyncCamoufox() as browser:
                page = await browser.new_page()
                await page.goto("https://portal.azure.com")
                await page.wait_for_function(
                    "window.location.href === 'https://portal.azure.com/#home'",
                    timeout=0,
                )

                while True:
                    auth_state_raw = await page.evaluate(
                        'window.sessionStorage.getItem("authState")'
                    )
                    if auth_state_raw is None:
                        break

                    auth_state: AuthState = json.loads(auth_state_raw)
                    self.auth_state = auth_state
                    if self.get_auth_state() is None:
                        break

                    expires_at = datetime.fromtimestamp(auth_state["expiresAt"])
                    while expires_at > datetime.now():
                        await asyncio.sleep(1)
                        if self.stop_requested:
                            break

                    if self.stop_requested:
                        break

                    await page.reload()
                    await asyncio.sleep(5)

            if self.stop_requested:
                break

        self.stopped = True

    async def stop(self):
        self.stop_requested = True
        while not self.stopped:
            await asyncio.sleep(1)


class AuthState(TypedDict):
    authHeader: str
    expiresAt: int
    expiresInMs: int
    tokenType: str
