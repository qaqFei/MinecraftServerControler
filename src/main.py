from __future__ import annotations

import importlib.util
import subprocess
import socket
import typing
import threading
import time
from os.path import abspath, dirname
from random import randint

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

class MinecraftServer:
    def __init__(self, server_path: str, server_rundir: str = None):
        self.server_path = server_path
        self.server_rundir = server_rundir if server_rundir is not None else dirname(abspath(self.server_path))
        self.waiting_commands = []
        
        self._spopen = None
        self._rcon = None
        self._rcon_logindata = None
    
    def start(self, args: typing.Iterable[str] = ()):
        if self._spopen is not None:
            raise Exception("Server is already running")
        
        self._spopen = subprocess.Popen([
                "java", "-jar",
                self.server_path,
                *args
            ], 
            stdin = subprocess.PIPE,
            cwd = self.server_rundir
        )
    
    def stop(self):
        self._check_running()
        
        if self._spopen.poll() is None:
            self._spopen.stdin.write(b"stop\n")
            self._spopen.stdin.flush()
            self._spopen.wait()
        self._spopen = None
    
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
                if isinstance(e, ConnectionAbortedError):
                    self.connect_rcon(*self._rcon_logindata)
                    return
                
                time.sleep(1 / 15)
            
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
    
    def run_adwl(self, urcon: bool = False):
        pm = self.run_commands(self.waiting_commands, False, urcon)
        self.waiting_commands.clear()
        return pm
    
    def setblock(self, x: int, y: int, z: int, block: str, extend: str|None = None, adwl: bool = False, urcon: bool = False):
        if extend is None: extend = ""
        else: extend = f" {extend}"
        cstr = f"setblock {x} {y} {z} {block}{extend}"
        self.run_command(cstr, adwl, urcon)
    
if __name__ == "__main__":
    import fix_workpath as _
    
    import sys
    import json
    import importlib
    from os.path import exists, isfile
    
    from PIL import Image
    from numba import jit
    
    import standard_plugin
    
    DEFAULT_CONFIG = {
        "server_path": None,
        "imblock_colordata_path": None,
        "plugins": [
            ".\\standard_plugin.py"
        ],
        "boot_commands": []
    }
    
    if not (exists("mscr_config.json") and isfile("mscr_config.json")):
        with open("mscr_config.json", "w", encoding = "utf-8") as f:
            f.write(json.dumps(DEFAULT_CONFIG, indent=4))
    
    def reload():
        global config, server_path
        global imblock_colordata_path
        global boot_commands
        global plugins, enable_drawim
        
        with open("mscr_config.json", "r", encoding = "utf-8") as f:
            config = DEFAULT_CONFIG.copy()
            config.update(json.load(f))
        
        with open("mscr_config.json", "w", encoding = "utf-8") as f:
            f.write(json.dumps(config, indent=4))
        
        server_path = config.get("server_path", None)
        if server_path is None:
            print("server_path is not set.")
            raise SystemExit
        
        if "plugins" in globals():
            for plugin in plugins: plugin.close()
        
        imblock_colordata_path = config.get("imblock_colordata_path", None)
        plugin_paths = config.get("plugins", [])
        boot_commands = config.get("boot_commands", [])
        plugins = []
    
        enable_drawim = imblock_colordata_path is not None

        for plugin in plugin_paths:
            spec = importlib.util.spec_from_file_location(f"plugin_{randint(0, 2147483647)}", plugin)
            plugin_mod: standard_plugin = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(plugin_mod)
            plugin_info = plugin_mod.init(lambda: globals())
            plugins.append(plugin_mod)
            print("\n".join([
                f"loaded plugin: {plugin_info["name"]}",
                f"plugin version: {plugin_info["version"]}",
                f"plugin description: \n{plugin_info["description"]}",
                ""
            ]))
    
    def load_ibcd():
        global getBlock_ByColor, ibcd_keys, ibcd_values
        
        if not enable_drawim: return
        
        with open(imblock_colordata_path, "r", encoding = "utf-8") as f:
            ibcd_data: dict[str, list[float, float, float]] = json.load(f)
            ibcd_keys = tuple(ibcd_data.keys())
            ibcd_values = tuple(map(tuple, tuple(ibcd_data.values())))
    
        @jit
        def getBlock_ByColor(r: int, g: int, b: int) -> str:
            avgs = [(r - v[0]) ** 2 + (g - v[1]) ** 2 + (b - v[2]) ** 2 for v in ibcd_values]
            return ibcd_keys[avgs.index(min(avgs))]
    
    reload()
    load_ibcd()
    
    class DebugException(BaseException): ...
    caseException = Exception
    
    server = MinecraftServer(server_path)
    server.start()
    rcon_mode = False
    
    while True:
        try:
            if boot_commands:
                cmd_item = boot_commands.pop(0)
                ctokens = cmd_item[0]
                sys.stdin.write("\n".join(cmd_item[1:] + ""))
            else:
                ctokens = list(filter(bool, input(">>> ").split(" ")))
                
            if not ctokens: continue
            
            match ctokens[0]:
                case "stop" | "exit" | "quit":
                    server.stop()
                    break
                
                case "cmd" | "command":
                    result = server.run_command(" ".join(ctokens[1:]), urcon=rcon_mode)
                    if rcon_mode: print(result.wait())
                
                case "drawim":
                    if not enable_drawim:
                        print("drawim is disabled.")
                        continue
                        
                    img_path = input("\nimage path > ")
                    x, y, z = map(lambda x: int(float(x)), input("start x y z > ").split(" "))
                    dx, dz = map(lambda x: int(float(x)), input("dx, dz > ").split(" "))
                    maxw, maxh = map(lambda x: int(float(x)), input("maxw, maxh > ").split(" "))
                    print("drawing...")
                    
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
                            
                    server.run_adwl(rcon_mode)
                    print("drawim success.")
                
                case "reload-ibcd":
                    if not enable_drawim:
                        print("drawim is disabled.")
                        continue

                    load_ibcd()
                    print("reload ibcd success.")
                
                case "connect-rcon":
                    addr, port = input("addr:port > ").split(":")
                    password = input("password > ")
                    server.connect_rcon(addr, int(port), password)
                    print("connect rcon success.")
                
                case "enable-rcon": rcon_mode = True
                case "disable-rcon": rcon_mode = False
                
                case "cls" | "clear":
                    print("\033c", end="")
                
                case _:
                    print("unknown command.")
        except caseException as e:
            print(f"exception: {e}")