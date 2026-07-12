import asyncio
from contextlib import asynccontextmanager
from typing import cast

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_cloud_logging import RequestLoggingMiddleware

from src.auth.api_key import APIKeyMiddleware
from src.config.settings import Settings
from src.daemons.azp_token_syncer import AZPTokenSyncerDaemon
from src.daemons.manager import DaemonManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    azps = AZPTokenSyncerDaemon()
    asyncio.create_task(azps.run())

    app.daemons = DaemonManager()
    app.daemons.azps = azps

    app.settings = Settings()

    yield

    # Shutdown
    await app.daemons.azps.stop()


app = FastAPI(lifespan=lifespan)
app.add_middleware(APIKeyMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/token")
async def get_azure_portal_token():
    auth_state = cast(AZPTokenSyncerDaemon, app.daemons.azps).get_auth_state()
    return {
        "token": auth_state["authHeader"].replace(f"{auth_state['tokenType']} ", ""),
        "token_type": auth_state["tokenType"],
        "expires_at": auth_state["expiresAt"],
    }


if __name__ == "__main__":
    uvicorn.run(
        "src.app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        access_log=False,
    )
