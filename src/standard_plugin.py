import typing

_globals: typing.Callable[[], dict[str, typing.Any]]|None = None

init = lambda f: (globals().update({"_globals": f}), {
    "name": "standard-plugin",
    "version": "0.0.1-dev",
    "description": "Standard plugin for Minecraft Server Controler."
})[1]

close = lambda: globals().update({k: None for k, _ in globals().items()})