import typing
import time
import threading

def init(f: typing.Callable[[], dict[str, typing.Any]]):
    global connect
    
    gvars = f()
    cfg = gvars["config"].get("auto_connect_rcon", {})
    connect = lambda: gvars["server"].connect_rcon(cfg["addr"], cfg["port"], cfg["password"])
    threading.Thread(target=try_connect, daemon=True).start()

    return {
        "name": "auto_connect_rcon",
        "version": "0.0.1",
        "description": "Auto connect to RCON server",
    }

def try_connect():
    global connect
    
    while True:
        try:
            connect()
        except Exception as e:
            print(f"Failed to connect to RCON server: {e}")
            time.sleep(3)
            continue
        
        print("Connected to RCON server")
        connect = lambda: None
        break

def __getattr__(name: str) -> typing.Any: return globals().get(name, lambda *args, **kwargs: None)