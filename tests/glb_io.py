"""GLB 읽기/부위 분류 공용 모듈 (읽기 전용: model/ 에셋은 수정하지 않는다)."""
import json
import os
import re
import struct
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "model"
MALE = MODEL / "male.glb"
# FEMALE_GLB 환경변수로 다른 파일(예: git 이전 버전)을 검사할 수 있다.
FEMALE = Path(os.environ["FEMALE_GLB"]) if os.environ.get("FEMALE_GLB") else MODEL / "female.glb"

_SIZES = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}
_DTYPES = {5120: "i1", 5121: "u1", 5122: "<i2", 5123: "<u2", 5125: "<u4", 5126: "<f4"}


def read_glb(path):
    data = Path(path).read_bytes()
    magic, version, total = struct.unpack_from("<III", data, 0)
    assert magic == 0x46546C67 and version == 2 and total == len(data), "GLB 헤더 불일치"
    jlen, jtype = struct.unpack_from("<II", data, 12)
    assert jtype == 0x4E4F534A
    gltf = json.loads(data[20:20 + jlen])
    off = 20 + jlen
    blen, btype = struct.unpack_from("<II", data, off)
    assert btype == 0x004E4942
    return gltf, bytes(data[off + 8:off + 8 + blen])


def accessor(gltf, buf, idx):
    a = gltf["accessors"][idx]
    v = gltf["bufferViews"][a["bufferView"]]
    dt = np.dtype(_DTYPES[a["componentType"]])
    n = _SIZES[a["type"]]
    stride = v.get("byteStride", dt.itemsize * n)
    return np.ndarray((a["count"], n), dtype=dt, buffer=buf,
                      offset=v.get("byteOffset", 0) + a.get("byteOffset", 0),
                      strides=(stride, dt.itemsize)).copy()


class Model:
    """glTF 의 모든 프리미티브를 하나의 정점 배열/삼각형 배열로 합친 뷰.

    - 프리미티브마다 정점 배열이 따로면(원본 male) 정점 풀을 순서대로 이어 붙인다.
    - 여러 프리미티브가 같은 POSITION accessor(공유 정점 풀)를 쓰면(modeler 의 refined female) 풀은 한 번만 읽는다.
    - tri_mat: 삼각형별 material 번호 (0=Body, 1=Joints). prim_id: 정점별 소속(Joints 삼각형에만 쓰이면 1).
    - pools: [(base, end)] 정점 풀 범위.
    """

    def __init__(self, path):
        self.gltf, self.buf = read_glb(path)
        pos, nrm, uv, jnt, wgt, tri, tri_mat = [], [], [], [], [], [], []
        base_of, self.pools = {}, []
        base = 0
        for m in self.gltf["meshes"]:
            for p in m["primitives"]:
                at = p["attributes"]
                key = at["POSITION"]
                if key not in base_of:
                    base_of[key] = base
                    P = accessor(self.gltf, self.buf, key).astype(np.float64)
                    pos.append(P)
                    nrm.append(accessor(self.gltf, self.buf, at["NORMAL"]).astype(np.float64))
                    uv.append(accessor(self.gltf, self.buf, at["TEXCOORD_0"]).astype(np.float64))
                    jnt.append(accessor(self.gltf, self.buf, at["JOINTS_0"]).astype(np.int64))
                    wgt.append(accessor(self.gltf, self.buf, at["WEIGHTS_0"]).astype(np.float64))
                    self.pools.append((base, base + len(P)))
                    base += len(P)
                t = accessor(self.gltf, self.buf, p["indices"]).reshape(-1, 3).astype(np.int64) + base_of[key]
                tri.append(t)
                tri_mat.append(np.full(len(t), p.get("material", 0)))
        self.pos = np.vstack(pos)
        self.nrm = np.vstack(nrm)
        self.uv = np.vstack(uv)
        self.joints = np.vstack(jnt)
        self.weights = np.vstack(wgt)
        self.tri = np.vstack(tri)
        self.tri_mat = np.concatenate(tri_mat)
        self.prim_id = np.zeros(len(self.pos), int)
        self.prim_id[np.unique(self.tri[self.tri_mat == 1])] = 1
        self.prims = [("pool", a, b) for a, b in self.pools]  # 하위 호환

    @property
    def n_verts(self):
        return len(self.pos)


def joint_names_from_male():
    g, _ = read_glb(MALE)
    return [g["nodes"][i]["name"] for i in g["skins"][0]["joints"]]


def part_of_joint(name):
    """DEF-* 본 이름 -> 신체 부위 라벨 (좌우 포함)."""
    s = name
    side = "L" if re.search(r"\.L(_|$)", s) else "R" if re.search(r"\.R(_|$)", s) else ""
    if "thigh" in s: k = "thigh"
    elif "shin" in s: k = "shin"
    elif "foot" in s: k = "foot"
    elif "toe" in s: k = "foot"
    elif "upper_arm" in s: k = "upper_arm"
    elif "forearm" in s: k = "forearm"
    elif "hand" in s or s.startswith("DEF-f_") or "thumb" in s: k = "hand"
    elif "shoulder" in s: k = "shoulder"
    elif "head" in s: k = "head"
    elif "neck" in s: k = "neck"
    elif s.startswith("DEF-spine.004") or s.startswith("DEF-spine.003"): k = "chest"
    elif s.startswith("DEF-spine.002"): k = "abdomen"
    elif s.startswith("DEF-spine.001"): k = "waist"
    elif s.startswith("DEF-spine"): k = "pelvis"
    else: k = "pelvis"
    return k + (("_" + side) if side else "")


def vertex_parts(model, names=None):
    """각 정점의 지배 본(JOINTS_0 최대 가중치) 기준 부위 라벨 배열."""
    names = names or joint_names_from_male()
    labels = np.array([part_of_joint(n) for n in names])
    dom = model.joints[np.arange(model.n_verts), model.weights.argmax(1)]
    return labels[dom], dom
