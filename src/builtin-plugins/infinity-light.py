import typing
import threading
import time

_globals: typing.Callable[[], dict[str, typing.Any]]|None = None
ref_dur = None

def init(f: typing.Callable[[], dict[str, typing.Any]]):
    global ref_dur
    
    globals()["_globals"] = f
    ref_dur = _globals()["config"].get("builtin_infinity_light_ref_duration", 1 / 8)
    threading.Thread(target=worker, daemon=True).start()
    
    return {
        "name": "infinity-light",
        "version": "builtin-noversion",
        "description": "Minecraft Infinity Light, Need Player Tag: mscr_infinity_light"
    }
    
def worker():
    server = None
    while not server:
        try: server = _globals()["server"]
        except KeyError: time.sleep(1 / 15)
        
    while True:
        server.run_command(command="execute at @a[tag=mscr_infinity_light] run fill ~-5 ~-5 ~-5 ~5 ~5 ~5 minecraft:light replace minecraft:air")
        server.run_command(command="execute at @a[tag=mscr_infinity_light] run fill ~-5 ~-5 ~-5 ~5 ~5 ~5 minecraft:light replace minecraft:air")
        time.sleep(ref_dur)

def __getattr__(name: str) -> typing.Any: return globals().get(name, lambda *args, **kwargs: None)