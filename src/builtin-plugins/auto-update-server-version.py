import typing
import logging

_globals: typing.Callable[[], dict[str, typing.Any]]|None = None

def init(f: typing.Callable[[], dict[str, typing.Any]]):
    globals()["_globals"] = f
    return {
        "name": "auto-update-server-version",
        "version": "builtin-noversion",
        "description": "Auto update server version in mscr_config.json"
    }
    
def loghooker(packer):
    if "Starting minecraft server version" in packer.obj:
        gvars = _globals()
        gvars["config"]["server_version"] = packer.obj.split(" ")[-1]
        gvars["save_config"]()
        logging.info(f"Updated server version to {gvars["config"]["server_version"]}")
        del globals()["loghooker"]

def __getattr__(name: str) -> typing.Any: return globals().get(name, lambda *args, **kwargs: None)