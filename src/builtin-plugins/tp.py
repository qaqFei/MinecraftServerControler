import json
import typing

aliases: dict[str, dict[str, str]] = {}
points: dict[str, dict[str, tuple[float, float, float]]] = {}

def init(f: typing.Callable[[], dict[str, typing.Any]]):
    global global_alias
    global global_points
    
    gvars = f()
    gvars["plugin_commands"].append(gvars["PluginCommand"](startswith="tp", callback=main, need_async=True))
    gvars["plugin_commands"].append(gvars["PluginCommand"](startswith="tp-aa", callback=tp_addalias, need_async=True))
    gvars["plugin_commands"].append(gvars["PluginCommand"](startswith="tp-ap", callback=tp_addpoint, need_async=True))
    config = gvars["config"]
    global_alias = config.get("global_tp_alias", {})
    global_points = config.get("global_tp_points", {})

    return {
        "name": "tp",
        "version": "0.0.1",
        "description": "Tp to other pos."
    }

def _tellraw(server, sender, raw):
    server.run_command(f"/tellraw {sender} {json.dumps(raw)}")

def _tellraw_all_player(server, raw):
    server.run_command(f"/tellraw @a {json.dumps(raw)}")

def main(server, sender: str, tokens: list[str]):
    players: list[str] = server.get_players()
    
    def postresult(content, color):
        _tellraw(server, sender, {
            "text": content,
            "color": color
        })
    
    if len(tokens) == 0:
        postresult("usage: tp <player> 传送到指定玩家位置", "red")
        return

    if tokens[0] not in players:
        a = aliases.get(sender, {})
        p = points.get(sender, {})
        
        if tokens[0] in a:
            tokens[0] = a[tokens[0]]
        elif tokens[0] in global_alias:
            tokens[0] = global_alias[tokens[0]]
        elif tokens[0] in p:
            tokens[0] = " ".join(map(str, p[tokens[0]]))
        elif tokens[0] in global_points:
            tokens[0] = " ".join(map(str, global_points[tokens[0]]))
        else:
            postresult(f"没有找到玩家或传送点 {tokens[0]}", "red")
            return
    
    server.run_command(f"/tp {sender} {tokens[0]}")
    _tellraw_all_player(server, {
        "text": f"{sender} 传送到 {tokens[0]}",
    })

def tp_addalias(server, sender: str, tokens: list[str]):
    def postresult(content, color):
        _tellraw(server, sender, {
            "text": content,
            "color": color
        })
    
    if len(tokens) == 0:
        postresult("usage: tp-aa <alias> <player> 添加别名", "red")
        return
    
    if sender not in aliases:
        aliases[sender] = {}
        
    aliases[sender][tokens[0]] = tokens[1]
    postresult(f"添加别名 {tokens[0]} -> {tokens[1]}", "green")

def tp_addpoint(server, sender: str, tokens: list[str]):
    def postresult(content, color):
        _tellraw(server, sender, {
            "text": content,
            "color": color
        })

    if len(tokens) == 0:
        postresult("usage: tp-ap <alias> <x> <y> <z> 添加传送点", "red")
        return

    if sender not in points:
        points[sender] = {}

    points[sender][tokens[0]] = (float(tokens[1]), float(tokens[2]), float(tokens[3]))
    postresult(f"添加传送点 {tokens[0]} -> {tokens[1]},{tokens[2]},{tokens[3]}", "green")

def __getattr__(name: str) -> typing.Any: return globals().get(name, lambda *args, **kwargs: None)