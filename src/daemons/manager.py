class DaemonManager:
    def __init__(self):
        self.daemons: dict[str, object] = {}

    def __getattr__(self, name: str):
        if name in self.daemons:
            return self.daemons[name]
        raise AttributeError(f"Daemon '{name}' not found.")

    def __setattr__(self, name: str, value: object):
        self.daemons[name] = value
