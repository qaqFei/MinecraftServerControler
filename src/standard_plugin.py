import typing

_globals: typing.Callable[[], dict[str, typing.Any]]|None = None

def init(f: typing.Callable[[], dict[str, typing.Any]]):
    globals()["_globals"] = f
    return {
        "name": "standard-plugin",
        "version": "builtin-noversion",
        "description": "Standard plugin for Minecraft Server Controler."
    }

def loghooker(packer): ...
def close(): ...

def __getattr__(name: str) -> typing.Any: return globals().get(name, lambda *args, **kwargs: None)