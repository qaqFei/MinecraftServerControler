import json
import typing
import sys

def init(f: typing.Callable[[], dict[str, typing.Any]]):
    global gvars
    global admins
    
    gvars = f()
    gvars["plugin_commands"].append(gvars["PluginCommand"](startswith="run-cmd", callback=main, need_async=True))
    config = gvars["config"]
    admins = config.get("run_cmd_admins", [])

    return {
        "name": "run_cmd",
        "version": "0.0.1",
        "description": "Run command."
    }

def _tellraw(server, sender, raw):
    server.run_command(f"/tellraw {sender} {json.dumps(raw)}")

def main(server, sender: str, tokens: list[str]):
    def postresult(content, color):
        _tellraw(server, sender, {
            "text": content,
            "color": color
        })
    
    if len(tokens) == 0:
        postresult("usage: run-cmd <json-content>", "red")
        postresult("example: run-cmd \"cmd time set day\"", "red")
        return

    if sender not in admins:
        postresult("你没有权限使用这个命令", "red")
        return
    
    gvars["run_userinputcmd"](gvars["parse_shell"](tokens[0]))
    postresult("运行成功", "green")

def __getattr__(name: str) -> typing.Any: return globals().get(name, lambda *args, **kwargs: None)