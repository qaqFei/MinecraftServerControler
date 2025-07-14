import math
import typing
import json
import time
import random

from tqdm import tqdm

class Transform3D:
    def __init__(self, matrix: typing.Optional[typing.Tuple[float, ...]] = None):
        # 使用行主序存储4x4矩阵 (16个元素)
        self.matrix = matrix if matrix is not None else (
            1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            0.0, 0.0, 0.0, 1.0
        )
    
    def resetTransform(self):
        """重置为单位矩阵"""
        self.matrix = (
            1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            0.0, 0.0, 0.0, 1.0
        )
        return self

    def setTransform(self, *elements: float):
        """直接设置变换矩阵"""
        if len(elements) != 16:
            raise ValueError("3D transform requires 16 matrix elements")
        self.matrix = tuple(elements)
        return self

    def transform(self, *other: float):
        """乘以另一个变换矩阵"""
        if len(other) != 16:
            raise ValueError("3D transform requires 16 matrix elements")
        
        # 矩阵乘法: current = current * other
        a = self.matrix
        b = other
        result = [0.0] * 16
        
        for i in range(4):
            for j in range(4):
                for k in range(4):
                    result[i*4 + j] += a[i*4 + k] * b[k*4 + j]
        
        self.matrix = tuple(result)
        return self
    
    def scale(self, x: float, y: float, z: float):
        """应用缩放变换"""
        scale_matrix = (
            x,   0.0, 0.0, 0.0,
            0.0, y,   0.0, 0.0,
            0.0, 0.0, z,   0.0,
            0.0, 0.0, 0.0, 1.0
        )
        return self.transform(*scale_matrix)
    
    def translate(self, x: float, y: float, z: float):
        """应用平移变换"""
        trans_matrix = (
            1.0, 0.0, 0.0, x,
            0.0, 1.0, 0.0, y,
            0.0, 0.0, 1.0, z,
            0.0, 0.0, 0.0, 1.0
        )
        return self.transform(*trans_matrix)
    
    def rotateX(self, angle: float):
        """绕X轴旋转 (弧度)"""
        c = math.cos(angle)
        s = math.sin(angle)
        rot_matrix = (
            1.0, 0.0, 0.0, 0.0,
            0.0, c,   -s,  0.0,
            0.0, s,   c,   0.0,
            0.0, 0.0, 0.0, 1.0
        )
        return self.transform(*rot_matrix)
    
    def rotateY(self, angle: float):
        """绕Y轴旋转 (弧度)"""
        c = math.cos(angle)
        s = math.sin(angle)
        rot_matrix = (
            c,   0.0, s,   0.0,
            0.0, 1.0, 0.0, 0.0,
            -s,  0.0, c,   0.0,
            0.0, 0.0, 0.0, 1.0
        )
        return self.transform(*rot_matrix)
    
    def rotateZ(self, angle: float):
        """绕Z轴旋转 (弧度)"""
        c = math.cos(angle)
        s = math.sin(angle)
        rot_matrix = (
            c,   -s,  0.0, 0.0,
            s,   c,   0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            0.0, 0.0, 0.0, 1.0
        )
        return self.transform(*rot_matrix)
    
    def rotateAxis(self, axis: typing.Tuple[float, float, float], angle: float):
        """绕任意轴旋转 (轴向量, 弧度)"""
        x, y, z = axis
        length = math.sqrt(x*x + y*y + z*z)
        if length == 0:
            return self
        
        # 归一化轴向量
        x /= length
        y /= length
        z /= length
        
        c = math.cos(angle)
        s = math.sin(angle)
        t = 1 - c
        
        # 旋转矩阵
        rot_matrix = (
            t*x*x + c,   t*x*y - s*z, t*x*z + s*y, 0.0,
            t*x*y + s*z, t*y*y + c,   t*y*z - s*x, 0.0,
            t*x*z - s*y, t*y*z + s*x, t*z*z + c,   0.0,
            0.0,         0.0,         0.0,         1.0
        )
        return self.transform(*rot_matrix)
    
    def rotateDegreeX(self, angle: float):
        """绕X轴旋转 (角度)"""
        return self.rotateX(angle * math.pi / 180.0)
    
    def rotateDegreeY(self, angle: float):
        """绕Y轴旋转 (角度)"""
        return self.rotateY(angle * math.pi / 180.0)
    
    def rotateDegreeZ(self, angle: float):
        """绕Z轴旋转 (角度)"""
        return self.rotateZ(angle * math.pi / 180.0)
    
    def rotateDegreeAxis(self, axis: typing.Tuple[float, float, float], angle: float):
        """绕任意轴旋转 (轴向量, 角度)"""
        return self.rotateAxis(axis, angle * math.pi / 180.0)
    
    def skewX(self, k: float):
        """应用X轴倾斜变换"""
        skew_matrix = (
            1.0, k, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            0.0, 0.0, 0.0, 1.0
        )
        return self.transform(*skew_matrix)

    def skewY(self, k: float):
        """应用Y轴倾斜变换"""
        skew_matrix = (
            1.0, 0.0, 0.0, 0.0,
            k,   1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            0.0, 0.0, 0.0, 1.0
        )
        return self.transform(*skew_matrix)

    def skewZ(self, k: float):
        """应用Z轴倾斜变换"""
        skew_matrix = (
            1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            k,   0.0, 1.0, 0.0,
            0.0, 0.0, 0.0, 1.0
        )
        return self.transform(*skew_matrix)

    def skewAxis(self, axis: typing.Tuple[float, float, float], k: float):
        """应用任意轴倾斜变换"""
        x, y, z = axis
        length = math.sqrt(x*x + y*y + z*z)
        if length == 0:
            return self

        # 归一化轴向量
        x /= length
        y /= length
        z /= length

        skew_matrix = (
            1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            x*k, y*k, z*k, 1.0
        )
        
        return self.transform(*skew_matrix)
    
    def getPoint(self, x: float, y: float, z: float):
        """变换3D点 (返回齐次坐标)"""
        m = self.matrix
        wx = m[0]*x + m[1]*y + m[2]*z + m[3]
        wy = m[4]*x + m[5]*y + m[6]*z + m[7]
        wz = m[8]*x + m[9]*y + m[10]*z + m[11]
        ww = m[12]*x + m[13]*y + m[14]*z + m[15]
        
        # 齐次坐标归一化
        if ww != 1 and ww != 0:
            return (wx/ww, wy/ww, wz/ww)
        return (wx, wy, wz)
    
    def getCubePoints(self, x: float, y: float, z: float, width: float, height: float, depth: float):
        """获取立方体的8个顶点"""
        return [
            self.getPoint(x, y, z),
            self.getPoint(x + width, y, z),
            self.getPoint(x + width, y + height, z),
            self.getPoint(x, y + height, z),
            self.getPoint(x, y, z + depth),
            self.getPoint(x + width, y, z + depth),
            self.getPoint(x + width, y + height, z + depth),
            self.getPoint(x, y + height, z + depth)
        ]
    
    def getCCubePoints(self, cx: float, cy: float, cz: float, width: float, height: float, depth: float):
        """获取中心在(cx,cy,cz)的立方体顶点"""
        hw = width / 2
        hh = height / 2
        hd = depth / 2
        return self.getCubePoints(cx - hw, cy - hh, cz - hd, width, height, depth)

def init(f: typing.Callable[[], dict[str, typing.Any]]):
    global gvars
    
    gvars = f()
    gvars["plugin_commands"].append(gvars["PluginCommand"](startswith="3dtest", callback=main, need_async=True))

    return {
        "name": "3dtest",
        "version": "0.0.1",
        "description": ""
    }

def _tellraw(server, sender, raw):
    server.run_command(f"/tellraw {sender} {json.dumps(raw)}")

def main(server, sender: str, tokens: list[str]):
    tg = f"test-{random.randint(0, int(1e5))}"
    color = (0xff, *(random.randint(0, 255) for _ in range(3)))
    color = color[0] << 24 | color[1] << 16 | color[2] << 8 | color[3]
    trans = Transform3D()
    x, y, z = 0, 0, 0
    server.run_command(f'summon text_display {x} {y} {z} {{"background": {color}l, "text": " ", "transformation": {list(trans.matrix)}, "Tags": ["{tg}"]}}')
    
    trans.scale(40, 40, 40)
    
    def update():
        server.run_command(f"data merge entity @e[tag={tg}, limit=1] {{\"transformation\": {list(trans.matrix)}}}")
    
    # for _ in tqdm(range(360)):
    #     trans.rotateDegreeY(1)
    #     update()
    #     time.sleep(1 / 120)
    
    # for _ in tqdm(range(360)):
    #     trans.rotateDegreeX(1)
    #     update()
    #     time.sleep(1 / 120)
    
    for _ in range(5):
        for v in tqdm(range(360)):
            trans.rotateDegreeZ(abs(math.sin(v / 180 * math.pi)))
            trans.scale(1.001, 1.001, 1.001)
            trans.skewZ(math.sin(v / 180 * math.pi) / 50)
            trans.skewY(math.sin(v / 180 * math.pi) / 400)
            update()
            time.sleep(1 / 240)
            
    server.run_command(f"kill @e[tag={tg}]")
    
def __getattr__(name: str) -> typing.Any: return globals().get(name, lambda *args, **kwargs: None)