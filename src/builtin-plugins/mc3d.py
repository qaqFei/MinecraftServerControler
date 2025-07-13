import json
import typing
import os
from PIL import Image
import trimesh
import numpy as np

def init(f: typing.Callable[[], dict[str, typing.Any]]):
    global gvars
    
    gvars = f()
    gvars["plugin_commands"].append(gvars["PluginCommand"](startswith="mc3d", callback=main, need_async=True))

    return {
        "name": "mc3d",
        "version": "0.0.1",
        "description": "Show 3d model in minecraft."
    }

def _tellraw(server, sender, raw):
    server.run_command(f"/tellraw {sender} {json.dumps(raw)}")

def voxelize_model(mesh: trimesh.Trimesh, scale: float = 1.0, resolution: float = 64.0):
    bounds = mesh.bounds
    max_extent = max(bounds[1] - bounds[0])
    pitch = max_extent / resolution
    voxels = mesh.voxelized(pitch=pitch / scale)
    return voxels, bounds, pitch

def setblock(server, block: str, x: int, y: int, z: int):
    server.run_command(f"/setblock {x} {y} {z} {block}")

def draw_model_in_minecraft(server, mesh: trimesh.Trimesh, texture: Image.Image, pos: tuple[int, int, int], scale: float = 1.0, resolution: float = 64.0):
    voxels, bounds, pitch = voxelize_model(mesh, scale=scale, resolution=resolution)
    matrix = voxels.matrix
    offset = bounds[0]
    
    uvs = None
    if hasattr(mesh.visual, "uv"):
        uvs = mesh.visual.uv
    
    seted = set()
    
    for x, y, z in np.argwhere(matrix):
        center = offset + np.array([x, y, z]) * pitch + pitch / 2
        
        if uvs is not None:
            _, _, face_idx = mesh.nearest.on_surface([center])[0]
            face = mesh.faces[face_idx]
            uv = np.mean(uvs[face], axis=0)
            u, v = uv[0], 1 - uv[1]
            tex_x = int(u * texture.width)
            tex_y = int(v * texture.height)
            color = texture.getpixel((tex_x, tex_y))
            block_id = gvars["getBlock_ByColor"](color)
        else:
            block_id = "minecraft:stone"
        
        mc_x = pos[0] + int(center[0] - offset[0])
        mc_y = pos[1] + int(center[1] - offset[1])
        mc_z = pos[2] + int(center[2] - offset[2])
        
        mcpos = (mc_x, mc_y, mc_z)
        if mcpos in seted:
            continue
        seted.add(mcpos)
        
        print(f"Rendering block at {mc_x}, {mc_y}, {mc_z} with block id {block_id}")
        setblock(server, block_id, mc_x, mc_y, mc_z)

def main(server, sender: str, tokens: list[str]):
    def postresult(content, color):
        _tellraw(server, sender, {
            "text": content,
            "color": color
        })
    
    if len(tokens) < 3:
        postresult("用法: mc3d <模型> <纹理> <x,y,z> [缩放=1.0] [分辨率=64.0]", "red")
        return
    
    model_path = tokens[0]
    texture_path = tokens[1]
    pos = tuple(map(int, tokens[2].split(",")))
    scale = float(tokens[3]) if len(tokens) > 3 else 1.0
    resolution = float(tokens[4]) if len(tokens) > 4 else 64.0
    
    mesh = trimesh.load(model_path)
    texture = Image.open(texture_path)
    
    draw_model_in_minecraft(server, mesh, texture, pos, scale, resolution)
    postresult("模型已成功渲染", "green")

def __getattr__(name: str) -> typing.Any: 
    return globals().get(name, lambda *args, **kwargs: None)