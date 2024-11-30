import typing
import json
import re

_globals: typing.Callable[[], dict[str, typing.Any]]|None = None
pfh_admins: list[str]

PFH_HELP = '''\
交互需使用前缀: ~!pfh

命令列表:
find-sw "<name>" - 查找以指定字符串开头的玩家
find-ew "<name>" - 查找以指定字符串结尾的玩家
find-in "<name>" - 查找包含指定字符串的玩家
find-re "<regular-expressions>" - 使用正则表达式查找玩家
\
'''

def init(f: typing.Callable[[], dict[str, typing.Any]]):
    global pfh_admins
    
    globals()["_globals"] = f
    
    gvars = f()
    config = gvars["config"]
    pfh_admins = config.get("player_find_helper_admins", [])
    
    globals()["loghooker"] = gvars["tfunc"](loghooker)
    
    return {
        "name": "player-find-helper",
        "version": "builtin-noversion",
        "description": "Help Server Admin To Find Player."
    }

def _tellraws(server, target: str, raw: dict):
    return server.run_command(f"tellraw {target} {json.dumps(raw, ensure_ascii=False)}")

def loghooker(packer):
    msg: str = packer.obj
    if "<" not in msg or ">" not in msg: return
    
    sender = msg.split("<")[1].split(">")[0]
    tokens = list(filter(bool, "".join(msg.split(">")[1][1:]).split(" ")))
    gvars = _globals()
    server = gvars["server"]
    
    if len(tokens) < 2: return
    if tokens[0] != "~!pfh": return
    tokens.pop(0)
    
    if sender not in pfh_admins: return
    players: list[str] = server.get_players()
    
    try:
        tokens[1] = json.loads(tokens[1])
    except json.JSONDecodeError:
        _tellraws(server, sender, {"text": "参数错误, 请使用 ~!pfh help 查看帮助信息"})
        return
    
    def postresult(result: list[str]):
        _tellraws(server, sender, [
            {"text": f"找到 {len(result)} 名玩家:\n"},
            *[
                {
                    "text": f"{i + 1}. {x}",
                    "insertion": x,
                    "hoverEvent": {
                        "action": "show_text",
                        "contents": f"使用Shift+单击复制: {x}"
                    }
                }
                for i, x in enumerate(result)
            ]
        ])
    
    match tokens[0]:
        case "help":
            _tellraws(server, sender, [PFH_HELP])
        
        case "find-sw":
            result = list(filter(lambda x: x.startswith(tokens[1]), players))
            postresult(result)
        
        case "find-ew":
            result = list(filter(lambda x: x.endswith(tokens[1]), players))
            postresult(result)

        case "find-in":
            result = list(filter(lambda x: tokens[1] in x, players))
            postresult(result)
        
        case "find-re":
            result = list(filter(lambda x: re.search(tokens[1], x) is not None, players))
            postresult(result)

        case _:
            _tellraws(server, sender, {"text": "未知命令, 请使用 ~!pfh help 查看帮助信息"})
        
def close():
    del globals()["loghooker"]

def __getattr__(name: str) -> typing.Any: return globals().get(name, lambda *args, **kwargs: None)