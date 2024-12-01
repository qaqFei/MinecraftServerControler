import typing
import json

import cv2
from PIL import Image

conshow_admins: list[str]
startswith = "conshow"

CONSHOW_HELP = f'''\
交互需使用前缀: ~!{startswith}

命令列表:
help - 查看帮助
show-img <path> <width> <height> [--target <player-selector>] [--runin-datapack] - 在控制台显示图片
show-video <path> <width> <height> [--target <player-selector>] - 在控制台显示视频
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
                            lst.append({"text": "■", "color": color})
                            continue
                        
                        if lst[-1]["color"] == color:
                            lst[-1]["text"] += "■"
                        else:
                            lst.append({"text": "■", "color": color})
                            
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
            
            case "show-video":
                cap = cv2.VideoCapture(tokens[1])
                fps = cap.get(cv2.CAP_PROP_FPS)
                
                while True:
                    ret, frame = cap.read()
                    if not ret: break
                    
                    new_frame = cv2.resize(frame, (int(tokens[2]), int(tokens[3])))
                    
                    raw = [[] for _ in range(new_frame.shape[0])]
                    
                    for y in range(new_frame.shape[0]):
                        for x in range(new_frame.shape[1]):
                            b, g, r = new_frame[y, x]
                            color = f"#{r:02x}{g:02x}{b:02x}"
                            lst = raw[y]
                        
                            if not lst:
                                lst.append({"text": "■", "color": color})
                                continue
                            
                            if lst[-1]["color"] == color:
                                lst[-1]["text"] += "■"
                            else:
                                lst.append({"text": "■", "color": color})
                            
                        raw[y][-1]["text"] += "\n"
                
                    target = sender if "--target" not in tokens else tokens[tokens.index("--target") + 1]
                    _tellraws(server, target, {
                        "text": "鼠标悬停查看图片",
                        "color": "yellow",
                        "bold": True, "underlined": True,
                        "hoverEvent": {
                            "action": "show_text",
                            "contents": raw
                        }
                    })
    except Exception as e:
        _tellraws(server, sender, {"text": f"发生错误: {repr(e)}", "color": "red"})

def __getattr__(name: str) -> typing.Any: return globals().get(name, lambda *args, **kwargs: None)