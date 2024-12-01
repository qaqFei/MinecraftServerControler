import typing
import json
import random

gsn_admins: list[str]
songs: list[str] = []
startswith = "gsn"
GSN_DEFAULT = {
    "started": False,
    "songs": []
}
gsn_data = GSN_DEFAULT.copy()

GSN_HELP = f'''\
这里是猜歌插件帮助信息。
交互需使用前缀: ~!{startswith}

命令列表 (省略前缀 带admin的为管理员命令):
help - 显示帮助信息
start - 开始游戏
openletter <letter> - 开指定字母
guess <name> - 猜歌名
admin-stop - 停止游戏
\
'''

def init(f: typing.Callable[[], dict[str, typing.Any]]):
    global gsn_admins
    global songs, oncenum
    
    gvars = f()
    config = gvars["config"]
    gsn_admins = config.get("guess_songname_admins", [])
    songs = config.get("guess_songname_songs", [])
    oncenum = config.get("guess_songname_oncenum", 10)
    
    gvars["plugin_commands"].append(gvars["PluginCommand"](startswith=startswith, callback=main))
    
    return {
        "name": "guess-songname",
        "version": "builtin-noversion",
        "description": "A Guess Song Name Game Plugin."
    }

def _getnewsongs():
    return [
        [s, False, "".join([("*" if (
            ord("a") <= ord(i) <= ord("z") or
            ord("A") <= ord(i) <= ord("Z") or
            ord("0") <= ord(i) <= ord("9")
        ) else i) for i in s]), "null"]
        for s in random.sample(songs, oncenum)
    ]

def _tellraws(server, target: str, lines: list[str]):
    return server.run_command(f"tellraw {target} {json.dumps({"text": "\n".join(lines)}, ensure_ascii=False)}")

def _getstate():
    return ["猜歌名目前进度:"] + [
        f"{i + 1}. {s[2]}{" (已猜出)" if s[1] else ""}"
        for i, s in enumerate(gsn_data["songs"])
    ]

def _nostart_tl(server, sender: str):
    _tellraws(server, sender, ["游戏未开始,", f"请使用 ~!{startswith} start 发起并开始游戏"])

def _getstopstate():
    return ["游戏已结束, 以下是游戏结果:"] + [
        f"{i + 1}. {s[2]} ({"已" if s[1] else "未"}猜出, 猜出者: {s[3]}) 答案: {s[0]}"
        for i, s in enumerate(gsn_data["songs"])
    ]

def main(server, sender: str, tokens: list[str]):
    global gsn_data
    
    is_admin = sender in gsn_admins
    
    match tokens[0]:
        case "help":
            _tellraws(server, sender, GSN_HELP.split("\n"))
            
        case "start":
            if gsn_data["started"]:
                _tellraws(server, sender, ["游戏已经开始,", "请等待游戏结束或管理员使用admin-stop命令结束游戏"])
                return
                
            gsn_data = GSN_DEFAULT.copy()
            gsn_data["started"] = True
            gsn_data["songs"] = _getnewsongs()
            
            _tellraws(server, "@a", [
                f"猜歌名游戏开始! 发起者: {sender}",
                f"可使用 ~!{startswith} help 查看帮助信息",
                "", *_getstate()
            ])
            
        case "openletter":
            if not gsn_data["started"]:
                _nostart_tl(server, sender)
                return
            
            if len(tokens) < 2:
                _tellraws(server, sender, ["请输入要开启的字母"])
                return
            
            if len(tokens[1]) != 1:
                _tellraws(server, sender, ["请输入一个字母"])
                return
            
            for s in gsn_data["songs"]:
                if s[1]: continue
                indexs = [i for i, c in enumerate(s[0]) if c.lower() == tokens[1].lower()]
                slist = list(s[2])
                for i in indexs: slist[i] = s[0][i]
                s[2] = "".join(slist)
                
                if "*" not in s[2]:
                    s[1] = True
                    s[3] = "开出来的... :("
            
            _tellraws(server, "@a", ["", *_getstate()])
        
        case "guess":
            if not gsn_data["started"]:
                _nostart_tl(server, sender)
                return
            
            tokens = [tokens[0]] + [" ".join(tokens[1:])]
            
            if len(tokens) < 2:
                _tellraws(server, sender, ["请输入要猜的歌名"])
                return
            
            for s in gsn_data["songs"]:
                if s[1]: continue
                if s[0] == tokens[1]:
                    s[1], s[2], s[3] = True, s[0], sender
                    _tellraws(server, "@a", [f"{s[0]} 已被猜出!", "", *_getstate()])
                    
                    if all([i[1] for i in gsn_data["songs"]]):
                        _tellraws(server, "@a", ["", f"猜歌名游戏已结束!", "", *_getstopstate()])
                        gsn_data = GSN_DEFAULT.copy()
                        return
                    
                    return
            
            _tellraws(server, sender, ["猜错了!"])
        
        case "admin-stop":
            if not is_admin:
                _tellraws(server, sender, ["你没有权限使用这个命令"])
                return
            
            if not gsn_data["started"]:
                _tellraws(server, sender, ["游戏还没有开始"])
                return
            
            _tellraws(server, "@a", [f"游戏已结束! 被 {sender} 终止", "", *_getstopstate()])
            gsn_data = GSN_DEFAULT.copy()
        
        case _:
            _tellraws(server, sender, [f"未知命令, 请使用 ~!{startswith} help 查看帮助信息"])
        
def __getattr__(name: str) -> typing.Any: return globals().get(name, lambda *args, **kwargs: None)