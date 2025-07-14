from __future__ import annotations

import importlib.util
import subprocess
import socket
import typing
import threading
import time
import logging
import shutil
import json
from os import mkdir, remove
from os.path import abspath, dirname, exists, isfile, isdir
from random import randint

logging.basicConfig(
    level = logging.INFO,
    format = "[%(asctime)s] %(levelname)s %(filename)s %(funcName)s: %(message)s",
    datefmt = "%H:%M:%S"
)
    
rcon_promises: list[Promise] = []

class RCON_PACKET_TYPE:
    SERVERDATA_AUTH = 3
    SERVERDATA_AUTH_RESPONSE = 2
    SERVERDATA_EXECCOMMAND = 2
    SERVERDATA_RESPONSE_VALUE = 0

class Promise:
    def __init__(self, rid: int):
        self._e = threading.Event()
        self._v = None
        self.rid = rid
    
    def resolve(self, value):
        self._v = value
        self._e.set()
    
    def wait(self):
        self._e.wait()
        return self._v

class LogWaiterPromise:
    def __init__(self, server: MinecraftServer, pattern: typing.Callable[[str], bool]):
        self.server = server
        self.pattern = pattern
        self._e = threading.Event()
        self._v = None
        server.log_waiter_promises.append(self)
    
    def resolve(self, line: str):
        self._e.set()
        self._v = line
    
    def wait(self):
        self._e.wait()
        return self._v

class CmdRunner:
    def __init__(self, server: MinecraftServer):
        self.server = server
    
    def run(self, cmd: str) -> str:
        return self.server.run_command(cmd, urcon=True).wait()
    
    def kill(self, selector: str):
        return self.run(f"kill {selector}")
    
    def give(self, selector: str, item: str, count: int = 1, nbt: typing.Optional[dict] = None):
        if nbt is None:
            nbt = {}
        
        return self.run(f"give {selector} {item}{json.dumps(nbt)} {count}")
    
    def tp(self, selector: str, target: str):
        return self.run(f"tp {selector} {target}")
    
    def effect_give(self, selector: str, effect: str, duration: int, amplifier: int = 0, hideparticles: bool = False):
        return self.run(f"effect give {selector} {effect} {duration} {amplifier} {json.dumps(hideparticles)}")
    
    def effect_clear(self, selector: str, effect: str):
        return self.run(f"effect clear {selector} {effect}")
    
    def clear(self, selector: str, item: typing.Optional[str] = None):
        if item is None:
            item = ""
        else:
            item = f" {item}"
            
        return self.run(f"clear {selector}{item}")
    
    def advancement_grant(self, selector: str, advancement: str):
        return self.run(f"advancement grant {selector} {advancement}")
    
    def advancement_revoke(self, selector: str, advancement: str):
        return self.run(f"advancement revoke {selector} {advancement}")
    
    def attribute_get(self, selector: str, attribute: str, scale: typing.Optional[float] = None):
        if scale is None:
            scale = ""
        else:
            scale = f" {scale}"
        
        return self.run(f"attribute {selector} {attribute} get{scale}")
    
    def attribute_base(self, method: typing.Literal["set", "get"], selector: str, attribute: str, sov: typing.Optional[float] = ""):
        if sov is None:
            sov = ""
        else:
            sov = f" {sov}"

        return self.run(f"attribute {selector} {attribute} base {method}{sov}")
    
    def ban(self, selector: str, reason: typing.Optional[str] = None):
        if reason is None:
            reason = ""
        else:
            reason = f" {reason}"

        return self.run(f"ban {selector}{reason}")
    
    def ban_ip(self, selector: str, reason: typing.Optional[str] = None):
        if reason is None:
            reason = ""
        else:
            reason = f" {reason}"

        return self.run(f"ban-ip {selector}{reason}")
    
    def banlist(self, t: typing.Literal["ips", "players"]):
        return self.run(f"banlist {t}")
    
    def setblock(self, x: str, y: str, z: str, block: str, mode: typing.Optional[str] = None):
        if mode is None:
            mode = ""
        else:
            mode = f" {mode}"

        return self.run(f"setblock {x} {y} {z} {block}{mode}")
    
    def fill(self, x1: str, y1: str, z1: str, x2: str, y2: str, z2: str, block: str, mode: typing.Optional[str] = None):
        if mode is None:
            mode = ""
        else:
            mode = f" {mode}"
            
        return self.run(f"fill {x1} {y1} {z1} {x2} {y2} {z2} {block}{mode}")
    
    def reload(self):
        return self.run("reload")
    
    def op(self, selector: str):
        return self.run(f"op {selector}")

    def deop(self, selector: str):
        return self.run(f"deop {selector}")
    
    def stop(self):
        return self.run("stop")
    
    def datapack_enable(self, name: str):
        return self.run(f"datapack enable {name}")
    
    def datapack_disable(self, name: str):
        return self.run(f"datapack disable {name}")

    def datapack_list(self):
        return self.run("datapack list")
    
    def list(self):
        return self.run("list")
    
    def pardon(self, selector: str):
        return self.run(f"pardon {selector}")

    def pardon_ip(self, selector: str):
        return self.run(f"pardon-ip {selector}")
    
    def msg(self, selector: str, msg: str):
        return self.run(f"msg {selector} {msg}")
    
    def tellraw(self, selector: str, msg: dict):
        return self.run(f"tellraw {selector} {json.dumps(msg)}")
    
    def data_get(self, path: str):
        return self.run(f"data get {path}")
    
    def data_merge(self, path: str, value: dict):
        return self.run(f"data merge {path} {json.dumps(value)}")

    def data_modify(self, path: str, value: dict):
        return self.run(f"data modify {path} {json.dumps(value)}")
    
    def data_remove(self, path: str):
        return self.run(f"data remove {path}")
    
class MinecraftServer:
    def __init__(
        self,
        server_path: str,
        server_rundir: str = None,
        loghooker: typing.Callable[[str], typing.Any] = lambda x: x
    ):
        self.server_path = server_path
        self.server_rundir = server_rundir if server_rundir is not None else dirname(abspath(self.server_path))
        self.loghooker = loghooker
        self.waiting_commands: list[str] = []
        self.log_waiter_promises: list[LogWaiterPromise] = []
        self.cmd_runner = CmdRunner(self)
        
        self._spopen = None
        self._rcon = None
        self._rcon_logindata = None
    
    def start(self, args: typing.Iterable[str] = (), max_mem: str = "768M"):
        if self._spopen is not None:
            raise Exception("Server is already running")
        
        worldpath = f"{self.server_rundir}/world"
        datapackname = "minecraftservercontrolerdatapack"
        datapackpath = f"{worldpath}/datapacks/{datapackname}"
        
        try: mkdir(worldpath)
        except FileExistsError: pass
        try: mkdir(f"{worldpath}/datapacks")
        except FileExistsError: pass
        
        if exists(datapackpath) and isdir(datapackpath):
            logging.warning(f"datapack {datapackname} already exists, deleting...")
            try: shutil.rmtree(datapackpath)
            except Exception as e: logging.error(f"error in deleting datapack {datapackname}: {repr(e)}")
        
        mkdir(datapackpath)
        
        with open(f"{datapackpath}/pack.mcmeta", "w", encoding="utf-8") as f:
            f.write(json.dumps({
                "pack": { 
                    "pack_format": 0,
                    "description": "Minecraft Server Controler Datapack"
                }
            }))
        
        mkdir(f"{datapackpath}/data")
        mkdir(f"{datapackpath}/data/minecraftservercontroler")
        self.datapack_funcspath = f"{datapackpath}/data/minecraftservercontroler/functions"
        mkdir(self.datapack_funcspath)
        
        self._spopen = subprocess.Popen([
                "java", f"-Xmx{max_mem}", "-jar",
                self.server_path,
                *args
            ], 
            stdin = subprocess.PIPE,
            stdout = subprocess.PIPE,
            cwd = self.server_rundir,
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
        )
        
        threading.Thread(target=self._outputlogs, daemon=True).start()
    
    def stop(self):
        self._check_running()
        
        if self._spopen.poll() is None:
            self._spopen.stdin.write(b"stop\n")
            self._spopen.stdin.flush()
            self._spopen.wait()
        self._spopen = None
    
    def _outputlogs(self):
        while self._spopen.poll() is None:
            try:
                rawline = self._spopen.stdout.readline().decode().strip("\n").strip("\r")
                for lwp in self.log_waiter_promises.copy():
                    if lwp.pattern(rawline):
                        lwp.resolve(rawline)
                        self.log_waiter_promises.remove(lwp)
                    
                line = self.loghooker(rawline)
                if line: print(line)
            except Exception as e:
                logging.error(f"error in outputlogs: {repr(e)}")
                continue
    
    def _check_running(self):
        if self._spopen is None: raise Exception("Server is not running")
    
    def _check_rcon(self):
        if self._rcon is None: raise Exception("RCON is not connected")
    
    def _make_rconpocket(self, reqid: int, packet_type: typing.Literal[0, 2, 3], packet_body: str):
        packet = (
            reqid.to_bytes(4, "little")
            + packet_type.to_bytes(4, "little")
            + packet_body.encode()
            + b"\x00\x00"
        )
        return len(packet).to_bytes(4, "little") + packet
        
    def _send_rcon(
        self,
        packet_type: typing.Literal[0, 2, 3],
        packet_body: str
    ):
        reqid = randint(0, 2147483647)
        packet = self._make_rconpocket(reqid, packet_type, packet_body)
        pm = Promise(reqid)
        rcon_promises.append(pm)
        self._rcon.send(packet)
        return pm

    def _receive_rcon(self):
        while True:
            if self._rcon is None:
                time.sleep(1 / 15)
                continue
            
            try:
                packet_size = int.from_bytes(self._rcon.recv(4), "little")
                packet = self._rcon.recv(packet_size)
                
                reqid = int.from_bytes(packet[:4], "little")
                packet_type = int.from_bytes(packet[4:8], "little")
                packet_body = packet[8:-2].decode()
                for pm in rcon_promises:
                    if pm.rid == reqid:
                        pm.resolve((reqid, packet_type, packet_body))
                        rcon_promises.remove(pm)
                        break
            except Exception as e:
                logging.error(f"error in rcon receive: {repr(e)}")
                
                if isinstance(e, ConnectionAbortedError):
                    self.connect_rcon(*self._rcon_logindata)
                    return
                
                time.sleep(1 / 15)
    
    def _remove_datapack_function(self, name: str):
        try: remove(f"{self.datapack_funcspath}/{name}.mcfunction")
        except Exception as e: logging.error(f"error in remove function file: {repr(e)}")
    
    def connect_rcon(self, addr: str, port: int, password: str):
        try:
            self._rcon = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._rcon.connect((addr, port))
            self._rcon_logindata = (addr, port, password)
            threading.Thread(target=self._receive_rcon, daemon=True).start()
            auth_result = self._send_rcon(RCON_PACKET_TYPE.SERVERDATA_AUTH, password).wait()
            if auth_result[0] == -1:
                raise Exception("RCON authentication failed")
        except Exception as e:
            self._rcon = None
            raise e
    
    def run_command(self, command: str, adwl: bool = False, urcon: bool = False):
        if adwl:
            self.waiting_commands.append(command)
            return
        
        self._check_running()
        if not command: return
        command = command if command[0] != "/" else command[1:]
        
        if urcon:
            return self._send_rcon(RCON_PACKET_TYPE.SERVERDATA_EXECCOMMAND, command)
        else:
            self._spopen.stdin.write((f"{command}\n").encode())
            self._spopen.stdin.flush()
    
    def run_commands(self, commands: list[str], adwl: bool = False, urcon: bool = False):
        if adwl:
            self.waiting_commands.extend(commands)
            return
            
        self._check_running()
        if not commands: return
        command_joined = "\n".join([rldc for c in commands if (rldc := (c if c and c[0] != "/" else c[1:]))])
        
        if urcon:
            return self._send_rcon(RCON_PACKET_TYPE.SERVERDATA_EXECCOMMAND, command_joined)
        else:
            self._spopen.stdin.write(command_joined.encode() + b"\n")
            self._spopen.stdin.flush()
    
    def run_command_byfunc(self, command: str, urcon: bool = False):
        self.waiting_commands.clear()
        rfid = randint(0, 2147483647)
        with open(f"{self.datapack_funcspath}/{rfid}.mcfunction", "w", encoding="utf-8") as f:
            f.write(command)
            
        pm = self.run_commands([
            "datapack disable \"file/minecraftservercontrolerdatapack\"",
            "datapack enable \"file/minecraftservercontrolerdatapack\"",
            f"function minecraftservercontroler:{rfid}"
        ], False, urcon)
        
        if pm is None:
            pm = LogWaiterPromise(self, lambda line: f"from function 'minecraftservercontroler:{rfid}'" in line)
            
        npm = Promise(-2)
        def waiter():
            npm.resolve(pm.wait())
            self._remove_datapack_function(rfid)
        threading.Thread(target=waiter, daemon=True).start()
        
        return npm
    
    def run_adwl(self, urcon: bool = False):
        pm = self.run_commands(self.waiting_commands, False, urcon)
        self.waiting_commands.clear()
        return pm
    
    def run_adwl_byfunc(self, urcon: bool = False):
        functext = "\n".join(self.waiting_commands)
        return self.run_command_byfunc(functext, False, urcon)
    
    def setblock(self, x: int, y: int, z: int, block: str, extend: str|None = None, adwl: bool = False, urcon: bool = False):
        if extend is None: extend = ""
        else: extend = f" {extend}"
        cstr = f"setblock {x} {y} {z} {block}{extend}"
        return self.run_command(cstr, adwl, urcon)
    
    def get_players(self, urcon: bool = False):
        pm = self.run_command("list", False, urcon)
        
        if pm is None:
            pm = LogWaiterPromise(self, lambda line: f"There are" in line and f"players online: " in line)
        
        return "".join(pm.wait().split("players online: ")[1:]).split(", ")
    
if __name__ == "__main__":
    import fix_workpath as _
    
    import importlib
    import builtins
    import functools
    import shlex
    
    from PIL import Image
    from numba import jit
    
    import standard_plugin
    import midi_parse
    
    plugins: list[standard_plugin] # type: ignore
    ibcd_data: dict[str, list[float, float, float]]
    plugin_commands: list[PluginCommand] = []
    
    DEFAULT_CONFIG = {
        "server_path": None,
        "imblock_colordata_path": None,
        "server_version": "1.19.2",
        "plugins": [
            "./standard_plugin.py",
            "./builtin-plugins/auto-update-server-version.py"
        ],
        "boot_commands": []
    }
    
    if not (exists("mscr_config.json") and isfile("mscr_config.json")):
        with open("mscr_config.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(DEFAULT_CONFIG, indent=4))
    
    class ObjectPacker:
        def __init__(self, obj: typing.Any):
            self.obj = obj

    def parse_shell(cmd: str):
        return list(map(lambda x: x[1:-1] if x.startswith("\"") and x.endswith("\"") else x, shlex.split(cmd, posix=False)))
    
    def load_module(path: str):
        spec = importlib.util.spec_from_file_location(f"module_{randint(0, 2147483647)}", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    
    def reload():
        global config, server_path
        global imblock_colordata_path
        global boot_commands
        global plugins, enable_drawim
        
        with open("mscr_config.json", "r", encoding="utf-8") as f:
            config = DEFAULT_CONFIG.copy()
            config.update(json.load(f))
        
        save_config()
        
        server_path = config.get("server_path", None)
        if server_path is None:
            logging.fatal("server_path is not set.")
            raise SystemExit
        
        if "plugins" in globals():
            for plugin in plugins: plugin.close()
            plugin_commands.clear()
        
        imblock_colordata_path = config.get("imblock_colordata_path", None)
        plugin_paths = config.get("plugins", []).copy()
        boot_commands = config.get("boot_commands", []).copy()
        plugins = []
    
        enable_drawim = imblock_colordata_path is not None

        for plugin in plugin_paths:
            plugin_mod: standard_plugin = load_module(plugin)
            plugin_info = plugin_mod.init(lambda: globals())
            plugins.append(plugin_mod)
            print("\n".join([
                f"loaded plugin: {plugin_info["name"]}",
                f"plugin version: {plugin_info["version"]}",
                f"plugin description: {plugin_info["description"]}",
                ""
            ]))
    
    def save_config():
        with open("mscr_config.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(config, indent=4))
    
    def load_ibcd():
        global getBlock_ByColor, ibcd_data, ibcd_keys, ibcd_values
        
        if not enable_drawim: return
        
        with open(imblock_colordata_path, "r", encoding="utf-8") as f:
            ibcd_data = json.load(f)
            ibcd_keys = tuple(ibcd_data.keys())
            ibcd_values = tuple(map(tuple, tuple(ibcd_data.values())))
    
        @jit
        def getBlock_ByColor(r: int, g: int, b: int) -> str:
            avgs = [(r - v[0]) ** 2 + (g - v[1]) ** 2 + (b - v[2]) ** 2 for v in ibcd_values]
            return ibcd_keys[avgs.index(min(avgs))]
    
    def save_ibcd():
        if not enable_drawim: return
        
        with open(imblock_colordata_path, "w", encoding="utf-8") as f:
            json.dump(ibcd_data, f, indent=4)
        
        load_ibcd()
    
    def loghooker(logline: str):
        logline_packer = ObjectPacker(logline)
        for plugin in plugins:
            plugin.loghooker(logline_packer)
        for command in plugin_commands:
            command.loghooker(logline_packer)
        return ""
    
    def input(*args, **kwargs):
        if input_waittexts: return input_waittexts.pop(0)
        return builtins.input(*args, **kwargs)
    
    def tfunc(f: typing.Callable):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            threading.Thread(target=f, args=args, kwargs=kwargs, daemon=True).start()
        return wrapper
    
    def getplaysoundtype_bynote(note: int):
        note = note if 30 <= note <= 102 else (30 if note < 30 else 102)
        typemap = sorted([
            ("bass", 30, 2),
            ("guitar", 42, 1),
            ("pling", 54, 1),
            ("xylophone", 78, 5),
        ], reverse=True)
        for name, start, num in typemap:
            if start <= note <= start + 24:
                return name, 2 ** ((-12 + note - start) / 12), num
    
    dev_f: typing.Callable[[dict[str, typing.Any]], typing.Any]
    def reload_devhot():
        global dev_f
        dev_f = load_module("./_devhotload.py").f
    
    class PluginCommand:
        def __init__(
            self,
            startswith: str,
            callback: typing.Callable[[MinecraftServer, str, list[str]], typing.Any],
            allow_users: list[str]|None = None,
            need_async: bool = False
        ):
            self.startswith = f"~!{startswith}"
            self.callback = callback
            self.allow_users = allow_users
            
            if need_async:
                self.loghooker = tfunc(self.loghooker)
        
        def loghooker(self, packer: ObjectPacker):
            rawmsg: str = packer.obj
            if "<" not in rawmsg or ">" not in rawmsg: return
            
            sender = rawmsg.split("<")[1].split(">")[0]
            if self.allow_users and sender not in self.allow_users: return
            
            tokens = parse_shell("".join(rawmsg.split("> ")[1:]))
            if tokens[0] == self.startswith:
                self.callback(server, sender, tokens[1:])
    
    reload_devhot()
    reload()
    load_ibcd()
    
    class DebugException(BaseException): ...
    caseException = (Exception, KeyboardInterrupt)
    
    server = MinecraftServer(
        server_path = server_path,
        loghooker = loghooker
    )
    server.start()
    
    rcon_mode = False
    heavy_taskrunner = server.run_adwl_byfunc
    input_waittexts = []
    
    while True:
        try:
            if boot_commands:
                cmd_item = boot_commands.pop(0)
                ctokens = cmd_item["ctokens"]
                input_waittexts.extend(cmd_item["arguments"])
            else:
                ctokens = parse_shell(input(">>> "))
                
            if not ctokens: continue
            
            match ctokens[0]:
                case "stop" | "exit" | "quit":
                    server.stop()
                    break
                
                case "cmd" | "command":
                    result = server.run_command(" ".join(ctokens[1:]), urcon=rcon_mode)
                    if rcon_mode: logging.info(f"rcon result: {result.wait()}")
                
                case "drawim":
                    if not enable_drawim:
                        logging.error("drawim is disabled.")
                        continue
                        
                    img_path = input("\nimage path > ")
                    x, y, z = map(lambda x: int(float(x)), input("start x y z > ").split(" "))
                    dx, dz = map(lambda x: int(float(x)), input("dx, dz > ").split(" "))
                    maxw, maxh = map(lambda x: int(float(x)), input("maxw, maxh > ").split(" "))
                    logging.info("drawing...")
                    
                    im = Image.open(img_path).convert("RGB")
                    if im.width > maxw: im = im.resize((maxw, int(im.height / im.width * maxw)))
                    if im.height > maxh: im = im.resize((int(im.width / im.height * maxh), maxh))
                    
                    for imx in range(im.width):
                        for imy in range(im.height):
                            server.setblock(
                                x + imx * dx, y, z + imy * dz,
                                getBlock_ByColor(*im.getpixel((imx, imy))),
                                adwl = True,
                                urcon = rcon_mode
                            )
                            
                    heavy_taskrunner(rcon_mode)
                    logging.info("drawim success.")
                
                case "play_midi":
                    print("tip: playsound is executed at @e[tag=midi_player]")
                    mid = midi_parse.MidiFile(open(ctokens[1], "rb").read())
                    more_delta = 0.0
                    for msg in mid.play():
                        dt = msg["global_sec_delta"] - more_delta
                        time.sleep(max(dt, 0.0))
                        t = time.perf_counter()
                        print(f"\rnow time: {msg["sec_time"]:.2f}s / {mid.second_length:.2f}s", end="")

                        match msg["type"]:
                            case "note_on":
                                name, note, num = getplaysoundtype_bynote(msg["note"])
                                vol = msg["velocity"] / 127
                                command = f"execute at @e[tag=midi_player] run playsound minecraft:block.note_block.{name} block @a ~ ~ ~ {vol} {note} {vol}"
                                for _ in range(num): server.run_command(command, urcon=rcon_mode)

                        more_delta = time.perf_counter() - t
                        # if dt < 0.0:
                        #     more_delta += -dt
                
                case "_devhot_reload":
                    reload_devhot()
                
                case "reload":
                    reload()
                    logging.info("reload success.")
                
                case "reload-ibcd":
                    if not enable_drawim:
                        logging.error("drawim is disabled.")
                        continue

                    load_ibcd()
                    logging.info("reload ibcd success.")
                
                case "test-ibcd":
                    if not rcon_mode:
                        logging.error("test ibcd requires rcon mode.")
                        continue
                    
                    logging.info("testing ibcd at position (0 0 0) ...")
                    
                    results = {}
                    for block in ibcd_keys:
                        cresult = server.run_command(f"setblock 0 0 0 {block}", urcon=True).wait()
                        results[block] = {
                            "rcon-result": cresult,
                            "pass": "Changed the block" in cresult[-1]
                        }
                        
                    test_ibcd_fn = f"./test-ibcd-results-{time.time()}.json"
                    with open(test_ibcd_fn, "w", encoding="utf-8") as f:
                        json.dump(results, f, indent=4, ensure_ascii=False)
                    
                    logging.info(f"tested ibcd, results saved to {test_ibcd_fn}")
                    
                    if "y" in input("please check the results file.\ndo you want to remove the cannot pass block? (y/n) > ").lower():
                        for block in ibcd_keys:
                            if not results[block]["pass"]:
                                ibcd_data.pop(block)
                                logging.info(f"removed {block}.")
                        save_ibcd()
                
                case "connect-rcon":
                    addr, port = input("addr:port > ").split(":")
                    password = input("password > ")
                    server.connect_rcon(addr, int(port), password)
                    logging.info("connect rcon success.")
                
                case "enable-rcon": rcon_mode = True
                case "disable-rcon": rcon_mode = False
                
                case "set-heavy-task-runner":
                    runners = [
                        "run_adwl (using stdin or rcon)",
                        "run_adwl_byfunc (using datapack function)"
                    ]
                    print()
                    
                    for i, ri in enumerate(runners):
                        print(f"{i + 1}. {ri}")
                    
                    heavy_taskrunner = getattr(server, input("runner function name > "))
                
                case "py-exec":
                    exec(input("code > "))
                
                case "cls" | "clear":
                    print("\033c", end="")
                
                case _:
                    logging.info("unknown command.")
        except caseException as e:
            logging.error(f"exception: {e}")
            