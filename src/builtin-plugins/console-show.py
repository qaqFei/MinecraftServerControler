import typing
import json

from PIL import Image

conshow_admins: list[str]
startswith = "conshow"

CONSHOW_HELP = f'''\
交互需使用前缀: ~!{startswith}

命令列表:
help - 查看帮助
show-img <path> <width> <height> [--target <player-selector>] [--runin-datapack] - 在控制台显示图片
\
'''

def init(f: typing.Callable[[], dict[str, typing.Any]]):
    global conshow_admins
    
    gvars = f()
    config = gvars["config"]
    conshow_admins = config.get("console_show_admins", [])
    
    gvars["plugin_commands"].append(gvars["PluginCommand"](startswith=startswith, callback=main, allow_users=conshow_admins))
    
    return {
        "name": "console-show",
        "version": "builtin-noversion",
        "description": "Show Something In Minecraft Console."
    }

def _tellraws_creater(target: str, raw: dict):
    return f"tellraw {target} {json.dumps(raw, ensure_ascii=False)}"

def _tellraws(server, target: str, raw: dict):
    return server.run_command(_tellraws_creater(target, raw))

def main(server, sender: str, tokens: list[str]):
    try:
        match tokens[0]:
            case "help":
                _tellraws(server, sender, {"text": CONSHOW_HELP})
            
            case "show-img":
                im = Image.open(tokens[1]).convert("RGB").resize((int(tokens[2]), int(tokens[3])))
                raw = [[] for _ in range(im.height)]
                for y in range(im.height):
                    for x in range(im.width):
                        r, g, b = im.getpixel((x, y))
                        color = f"#{r:02x}{g:02x}{b:02x}"
                        lst = raw[y]
                        
                        if not lst:
                            lst.append({"text": "■", "color": color, "bold": True})
                            continue
                        
                        if lst[-1]["color"] == color:
                            lst[-1]["text"] += "■"
                        else:
                            lst.append({"text": "■", "color": color, "bold": True})
                            
                    raw[y][-1]["text"] += "\n"
                
                target = sender if "--target" not in tokens else tokens[tokens.index("--target") + 1]
                rawdata = {
                    "text": "鼠标悬停查看图片",
                    "color": "yellow",
                    "bold": True, "underlined": True,
                    "hoverEvent": {
                        "action": "show_text",
                        "contents": raw
                    }
                }
                        
                if "--runin-datapack" not in tokens:
                    _tellraws(server, target, rawdata)
                else:
                    server.run_command_byfunc(_tellraws_creater(target, rawdata), False)
    except Exception as e:
        _tellraws(server, sender, {"text": f"发生错误: {repr(e)}", "color": "red"})

def __getattr__(name: str) -> typing.Any: return globals().get(name, lambda *args, **kwargs: None)