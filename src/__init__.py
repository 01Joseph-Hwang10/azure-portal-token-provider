import asyncio
import sys

# Force the Proactor loop policy immediately when the worker imports this file
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
