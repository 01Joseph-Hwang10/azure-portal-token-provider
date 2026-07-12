class DaemonManager:
    def __init__(self):
        self._daemons: dict[str, object] = {}

    def __getattr__(self, name: str):
        if name == "_daemons":
            return self.__dict__["_daemons"]
        if name in self._daemons:
            return self._daemons[name]
        raise AttributeError(f"Daemon '{name}' not found.")

    def __setattr__(self, name: str, value: object):
        if name == "_daemons":
            self.__dict__["_daemons"] = value
        self._daemons[name] = value
