import typing
import json
import re

startswith = "pfh"

PFH_HELP = f'''\
交互需使用前缀: ~!{startswith}

命令列表:
find-sw <name> - 查找以指定字符串开头的玩家
find-ew <name> - 查找以指定字符串结尾的玩家
find-in <name> - 查找包含指定字符串的玩家
find-re <regular-expressions> - 使用正则表达式查找玩家
\
'''

def init(f: typing.Callable[[], dict[str, typing.Any]]):
    gvars = f()
    config = gvars["config"]
    pfh_admins = config.get("player_find_helper_admins", [])
    
    gvars["plugin_commands"].append(gvars["PluginCommand"](startswith=startswith, callback=main, allow_users=pfh_admins, need_async=True))
    
    return {
        "name": "player-find-helper",
        "version": "builtin-noversion",
        "description": "Help Server Admin To Find Player."
    }

def _tellraws(server, target: str, raw: dict):
    return server.run_command(f"tellraw {target} {json.dumps(raw, ensure_ascii=False)}")

def main(server, sender: str, tokens: list[str]):
    players: list[str] = server.get_players()
    
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
            _tellraws(server, sender, {"text": PFH_HELP})
        
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
            _tellraws(server, sender, {"text": f"未知命令, 请使用 ~!{startswith} help 查看帮助信息"})

def __getattr__(name: str) -> typing.Any: return globals().get(name, lambda *args, **kwargs: None)