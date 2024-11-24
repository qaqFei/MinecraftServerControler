from __future__ import annotations

import typing

_globals: typing.Callable[[], dict[str, typing.Any]]|None = None

def init(f: typing.Callable[[], dict[str, typing.Any]]):
    globals()["_globals"] = f
    return {
        "name": "standard-plugin",
        "version": "0.0.1-dev",
        "description": "Standard plugin for Minecraft Server Controler."
    }

def loghooker(packer): ...
def close(): ...

def __getattribute__(self, name: str) -> typing.Any: return globals().get(name, lambda *args, **kwargs: None)