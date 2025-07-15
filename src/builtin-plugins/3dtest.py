import math
import typing
import json
import time
import random
import numpy as np

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

color = (0x39, 0xbb, 0xc5)

def float2str(x: float):
    return f"{x:.5f}"

def summon_parallelogram(server, trans: Transform3D, pos: tuple[float, float, float], color: tuple):
    c = (0xff, *color)
    c = c[0] << 24 | c[1] << 16 | c[2] << 8 | c[3]
    trans.scale(40, 40, 40)
    return server.run_command(f'summon text_display {" ".join(map(float2str, pos))} {{"background": {c}l, "text": " ", "transformation": [{",".join(map(float2str, trans.matrix))}], "Tags": []}}', adwl=True)

def calculate_normal(p1, p2, p3):
    """计算三角形的法向量"""
    # 计算三角形的两条边向量
    v1 = np.array([p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2]])
    v2 = np.array([p3[0] - p1[0], p3[1] - p1[1], p3[2] - p1[2]])
    
    # 计算法向量（两个向量的叉乘）
    normal = np.cross(v1, v2)
    
    # 归一化法向量
    norm = np.linalg.norm(normal)
    if norm == 0:
        return [0, 0, 1]  # 避免除零错误，返回默认法向量
    return normal / norm

def calculate_lighting(normal, light_dir, light_color, ambient_intensity=0.2):
    """计算光照强度
    
    参数:
    normal - 表面法向量
    light_dir - 光源方向向量（已归一化）
    light_color - 光源颜色 (r,g,b) 元组，值在0-255之间
    ambient_intensity - 环境光强度，默认0.2
    
    返回:
    最终的颜色 (r,g,b) 元组
    """
    # 计算漫反射光照强度 (Lambert's Cosine Law)
    # max(0, dot(N, L)) 确保负值被视为0（表面背向光源）
    diffuse_intensity = max(0, np.dot(normal, light_dir))
    
    # 计算最终颜色 = 环境光 + 漫反射光
    r, g, b = light_color
    intensity = ambient_intensity + diffuse_intensity * (1 - ambient_intensity)
    
    # 限制颜色值在0-255范围内
    final_r = min(255, int(r * intensity))
    final_g = min(255, int(g * intensity))
    final_b = min(255, int(b * intensity))
    
    return (final_r, final_g, final_b)

def summon_triangle_with_lighting(server, p1, p2, p3, base_color=(0x39, 0xbb, 0xc5), 
                                light_dir=(0.5, 0.7, 0.5), light_color=(255, 255, 255), 
                                ambient_intensity=0.3):
    """使用三个平行四边形渲染一个带光照的三角形
    
    参数:
    p1, p2, p3: 三角形的三个顶点坐标
    base_color: 基础颜色 (r,g,b)
    light_dir: 光源方向
    light_color: 光源颜色
    ambient_intensity: 环境光强度
    """
    # 计算三角形法向量
    normal = calculate_normal(p1, p2, p3)
    
    # 归一化光源方向
    light_dir = np.array(light_dir)
    light_dir = light_dir / np.linalg.norm(light_dir)
    
    # 计算应用光照后的颜色
    lit_color = calculate_lighting(normal, light_dir, base_color, ambient_intensity)
    
    # 缩放顶点以适应显示
    p1 = [p/2 for p in p1]
    p2 = [p/2 for p in p2]
    p3 = [p/2 for p in p3]
    
    # 第一个平行四边形：以p1为原点，p1→p2和p1→p3为方向向量
    trans1 = Transform3D()
    # 计算从p1到p2和p1到p3的向量
    v1_to_p2 = (p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2])
    v1_to_p3 = (p3[0] - p1[0], p3[1] - p1[1], p3[2] - p1[2])
    
    # 平移到p1位置
    trans1.translate(p1[0], p1[1], p1[2])
    # 设置变换矩阵，将单位正方形变换为所需的平行四边形
    matrix1 = (
        v1_to_p2[0], v1_to_p3[0], 0.0, 0.0,
        v1_to_p2[1], v1_to_p3[1], 0.0, 0.0,
        v1_to_p2[2], v1_to_p3[2], 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0
    )
    trans1.transform(*matrix1)
    summon_parallelogram(server, trans1, p1, lit_color)
    
    # 第二个平行四边形：以p2为原点，p2→p3和p2→p1为方向向量
    trans2 = Transform3D()
    # 计算从p2到p3和p2到p1的向量
    v2_to_p3 = (p3[0] - p2[0], p3[1] - p2[1], p3[2] - p2[2])
    v2_to_p1 = (p1[0] - p2[0], p1[1] - p2[1], p1[2] - p2[2])
    
    # 平移到p2位置
    trans2.translate(p2[0], p2[1], p2[2])
    # 设置变换矩阵
    matrix2 = (
        v2_to_p3[0], v2_to_p1[0], 0.0, 0.0,
        v2_to_p3[1], v2_to_p1[1], 0.0, 0.0,
        v2_to_p3[2], v2_to_p1[2], 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0
    )
    trans2.transform(*matrix2)
    summon_parallelogram(server, trans2, p2, lit_color)
    
    # 第三个平行四边形：以p3为原点，p3→p1和p3→p2为方向向量
    trans3 = Transform3D()
    # 计算从p3到p1和p3到p2的向量
    v3_to_p1 = (p1[0] - p3[0], p1[1] - p3[1], p1[2] - p3[2])
    v3_to_p2 = (p2[0] - p3[0], p2[1] - p3[1], p2[2] - p3[2])
    
    # 平移到p3位置
    trans3.translate(p3[0], p3[1], p3[2])
    # 设置变换矩阵
    matrix3 = (
        v3_to_p1[0], v3_to_p2[0], 0.0, 0.0,
        v3_to_p1[1], v3_to_p2[1], 0.0, 0.0,
        v3_to_p1[2], v3_to_p2[2], 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0
    )
    trans3.transform(*matrix3)
    summon_parallelogram(server, trans3, p3, lit_color)
    
    return [p1, p2, p3]

def main(server, sender, args):
    global dim
    
    _tellraw(server, sender, {"text": "正在渲染带光照的3D模型...", "color": "green"})
    
    import trimesh
    
    mesh = trimesh.load(r"C:\Users\QAQ\Desktop\七七.stl")
    topy = lambda p: tuple(map(float, p))
    
    # 设置光照参数
    light_dir = (0.5, 0.7, 0.5)  # 光源方向
    light_color = (255, 255, 255)  # 白光
    ambient_intensity = 0.3  # 环境光强度
    
    for face in mesh.faces:
        p1, p2, p3 = mesh.vertices[face]
        # 使用带光照的三角形渲染函数
        summon_triangle_with_lighting(
            server, 
            topy(p1), topy(p2), topy(p3), 
            base_color=color,
            light_dir=light_dir,
            light_color=light_color,
            ambient_intensity=ambient_intensity
        )
    
    cmds = server.waiting_commands.copy()
    pocket = []
    for cmd in tqdm(cmds):
        if len(pocket) > 5000:
            server.run_command_byfunc("\n".join(pocket))
            pocket.clear()
            input("enter to continue")
            
        pocket.append(cmd)
    
    if pocket:
        server.run_command_byfunc("\n".join(pocket))
    
    _tellraw(server, sender, {"text": "已渲染", "color": "aqua"})
    
def __getattr__(name: str) -> typing.Any: return globals().get(name, lambda *args, **kwargs: None)
