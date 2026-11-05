"""GLB 읽기/부위 분류 공용 모듈 (읽기 전용: model/ 에셋은 수정하지 않는다)."""
import json
import re
import struct
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "model"
MALE = MODEL / "male.glb"
FEMALE = MODEL / "female.glb"

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
    """두 프리미티브(Body, Joints)를 하나의 정점 배열로 이어 붙인 뷰."""

    def __init__(self, path, joint_names=None):
        self.gltf, self.buf = read_glb(path)
        self.prims = []
        pos, nrm, tri, jnt, wgt, src = [], [], [], [], [], []
        base = 0
        for mi, m in enumerate(self.gltf["meshes"]):
            p = m["primitives"][0]
            at = p["attributes"]
            P = accessor(self.gltf, self.buf, at["POSITION"]).astype(np.float64)
            pos.append(P)
            nrm.append(accessor(self.gltf, self.buf, at["NORMAL"]).astype(np.float64))
            tri.append(accessor(self.gltf, self.buf, p["indices"]).reshape(-1, 3).astype(np.int64) + base)
            jnt.append(accessor(self.gltf, self.buf, at["JOINTS_0"]).astype(np.int64))
            wgt.append(accessor(self.gltf, self.buf, at["WEIGHTS_0"]).astype(np.float64))
            src.append(np.full(len(P), mi))
            self.prims.append((m["name"], base, base + len(P)))
            base += len(P)
        self.pos = np.vstack(pos)
        self.nrm = np.vstack(nrm)
        self.tri = np.vstack(tri)
        self.joints = np.vstack(jnt)
        self.weights = np.vstack(wgt)
        self.prim_id = np.concatenate(src)  # 0=Body, 1=Joints

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
