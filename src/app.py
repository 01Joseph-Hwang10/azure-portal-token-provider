from contextlib import asynccontextmanager

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
    app.daemons = DaemonManager()
    app.daemons.register("azps", AZPTokenSyncerDaemon())
    await app.daemons.start()

    app.settings = Settings()

    yield

    # Shutdown
    await app.daemons.stop()


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


@app.get("/token")
async def get_azure_portal_token():
    azps: AZPTokenSyncerDaemon = app.daemons.get("azps")
    token = azps.get_token()
    expires_at = azps.get_expires_at()
    if not token or not expires_at:
        return {"token": None, "expires_at": None}
    return {"token": token, "expires_at": expires_at.isoformat()}


if __name__ == "__main__":
    uvicorn.run(
        "src.app:app",
        host="127.0.0.1",
        port=8000,
        loop="asyncio",
        reload=True,
        access_log=False,
    )
