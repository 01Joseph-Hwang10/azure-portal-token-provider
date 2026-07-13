import asyncio


class DaemonManager:
    def __init__(self):
        self.daemons: list[tuple[str, object]] = []
        self.tasks: list[asyncio.Task] = []

    def get(self, name: str):
        for daemon_name, daemon in self.daemons:
            if daemon_name == name:
                return daemon
        raise ValueError(f"Daemon with name '{name}' not found.")

    def register(self, name: str, daemon: object):
        self.daemons.append((name, daemon))

    async def start(self):
        for name, daemon in self.daemons:
            task = asyncio.create_task(daemon.run())
            self.tasks.append(task)

    async def stop(self):
        for name, daemon in reversed(self.daemons):
            await daemon.stop()
