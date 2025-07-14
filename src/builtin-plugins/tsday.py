import json
import typing

aliases: dict[str, dict[str, str]] = {}

def init(f: typing.Callable[[], dict[str, typing.Any]]):
    global tsday_admins
    
    gvars = f()
    gvars["plugin_commands"].append(gvars["PluginCommand"](startswith="tsday", callback=main, need_async=True))
    config = gvars["config"]
    tsday_admins = config.get("tsday_admins", [])

    return {
        "name": "tsday",
        "version": "0.0.1",
        "description": "Set time to day."
    }

def _tellraw(server, sender, raw):
    server.run_command(f"/tellraw {sender} {json.dumps(raw)}")

def main(server, sender: str, _):
    def postresult(content, color):
        _tellraw(server, sender, {
            "text": content,
            "color": color
        })
        
    if sender not in tsday_admins:
        postresult("你没有权限使用这个命令", "red")
        return

    server.run_command("/time set day")
    _tellraw(server, "@a", {
        "text": f"{sender} 使用了 tsday 命令，已将时间设置为白天",
        "color": "green"
    })
    
    server.cmd_runner.kill("@e")

def __getattr__(name: str) -> typing.Any: return globals().get(name, lambda *args, **kwargs: None)