"""Shared rig code: GLB I/O, the standard skeleton, rest frames, quaternions/Euler, FK and linear blend skinning.

Coordinates: metres, Y-up, character faces +Z, character's own left is +X.
Quaternions are [x, y, z, w] (glTF / three.js order). Euler angles follow three.js order 'XYZ' (R = Rx·Ry·Rz).
NumPy only; no Blender or GUI.
"""
import json
import re
import struct
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RIG = ROOT / "rig"
SKELETON_ID = "pose-library-humanoid-v1"

# ---------------------------------------------------------------- skeleton definition
# (standard name, parent, source DEF name without the exporter suffix, frame class)
_CENTER = [
    ("pelvis", None, "DEF-spine", "center"),
    ("spine_01", "pelvis", "DEF-spine.001", "center"),
    ("spine_02", "spine_01", "DEF-spine.002", "center"),
    ("spine_03", "spine_02", "DEF-spine.003", "center"),
    ("spine_04", "spine_03", "DEF-spine.004", "center"),
    ("neck_01", "spine_04", "DEF-neck", "center"),
    ("head", "neck_01", "DEF-head", "center"),
]
FINGERS = [("thumb", "thumb"), ("index", "f_index"), ("middle", "f_middle"), ("ring", "f_ring"), ("pinky", "f_pinky")]


def _side(s, S):
    b = [(f"clavicle_{s}", "spine_03", f"DEF-shoulder.{S}", "clavicle"),
         (f"upperarm_{s}", f"clavicle_{s}", f"DEF-upper_arm.{S}", "arm"),
         (f"lowerarm_{s}", f"upperarm_{s}", f"DEF-forearm.{S}", "arm"),
         (f"hand_{s}", f"lowerarm_{s}", f"DEF-hand.{S}", "hand")]
    for std, src in FINGERS:
        for k in (1, 2, 3):
            parent = f"hand_{s}" if k == 1 else f"{std}_0{k - 1}_{s}"
            b.append((f"{std}_0{k}_{s}", parent, f"DEF-{src}.0{k}.{S}", "hand"))
    b += [(f"thigh_{s}", "pelvis", f"DEF-thigh.{S}", "leg"),
          (f"calf_{s}", f"thigh_{s}", f"DEF-shin.{S}", "leg"),
          (f"foot_{s}", f"calf_{s}", f"DEF-foot.{S}", "leg"),
          (f"ball_{s}", f"foot_{s}", f"DEF-toe.{S}", "leg")]
    return b


SKELETON = _CENTER + _side("l", "L") + _side("r", "R")
BONES = [b[0] for b in SKELETON]
PARENT = {b[0]: b[1] for b in SKELETON}
DEF_NAME = {b[0]: b[2] for b in SKELETON}
FRAME_CLASS = {b[0]: b[3] for b in SKELETON}
INDEX = {n: i for i, n in enumerate(BONES)}
CHILDREN = {n: [c for c in BONES if PARENT[c] == n] for n in BONES}


def mirror_name(name):
    return name[:-2] + {"_l": "_r", "_r": "_l"}[name[-2:]] if name[-2:] in ("_l", "_r") else name


def strip_suffix(gltf_name):
    """'DEF-upper_arm.L_09' -> 'DEF-upper_arm.L' (removes the exporter's node-index suffix)."""
    return re.sub(r"_\d+$", "", gltf_name)


# ---------------------------------------------------------------- GLB I/O
_SIZES = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}
_DTYPES = {5120: "i1", 5121: "u1", 5122: "<i2", 5123: "<u2", 5125: "<u4", 5126: "<f4"}


def read_glb(path):
    data = Path(path).read_bytes()
    magic, version, total = struct.unpack_from("<III", data, 0)
    assert magic == 0x46546C67 and version == 2 and total == len(data)
    jlen, _ = struct.unpack_from("<II", data, 12)
    gltf = json.loads(data[20:20 + jlen])
    off = 20 + jlen
    blen, _ = struct.unpack_from("<II", data, off)
    return gltf, bytes(data[off + 8:off + 8 + blen])


def accessor(gltf, buf, idx):
    a = gltf["accessors"][idx]
    v = gltf["bufferViews"][a["bufferView"]]
    dt = np.dtype(_DTYPES[a["componentType"]])
    n = _SIZES[a["type"]]
    stride = v.get("byteStride", dt.itemsize * n)
    return np.ndarray((a["count"], n), dtype=dt, buffer=buf, offset=v.get("byteOffset", 0) + a.get("byteOffset", 0),
                      strides=(stride, dt.itemsize)).copy()


class GlbWriter:
    def __init__(self):
        self.gltf = {"asset": {"version": "2.0"}, "buffers": [{"byteLength": 0}], "bufferViews": [], "accessors": []}
        self.bin = bytearray()

    def add(self, data, kind, component, target=None, minmax=False):
        dtype = {5126: "<f4", 5125: "<u4", 5123: "<u2", 5121: "u1"}[component]
        a = np.ascontiguousarray(np.asarray(data).astype(dtype))
        self.bin += b"\0" * ((-len(self.bin)) % 4)
        view = {"buffer": 0, "byteOffset": len(self.bin), "byteLength": a.nbytes}
        if target:
            view["target"] = target
        self.bin += a.tobytes()
        self.gltf["bufferViews"].append(view)
        acc = {"bufferView": len(self.gltf["bufferViews"]) - 1, "componentType": component,
               "count": int(len(a)), "type": kind}
        if minmax:
            flat = a.reshape(len(a), -1)
            acc["min"] = flat.min(0).tolist()
            acc["max"] = flat.max(0).tolist()
        self.gltf["accessors"].append(acc)
        return len(self.gltf["accessors"]) - 1

    def bytes(self):
        self.bin += b"\0" * ((-len(self.bin)) % 4)
        self.gltf["buffers"][0]["byteLength"] = len(self.bin)
        raw = json.dumps(self.gltf, separators=(",", ":")).encode()
        raw += b" " * ((-len(raw)) % 4)
        total = 12 + 8 + len(raw) + 8 + len(self.bin)
        return (struct.pack("<III", 0x46546C67, 2, total) + struct.pack("<II", len(raw), 0x4E4F534A) + raw
                + struct.pack("<II", len(self.bin), 0x004E4942) + bytes(self.bin))


# ---------------------------------------------------------------- rotations
def quat_to_mat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def mat_to_quat(m):
    t = np.trace(m)
    if t > 0:
        s = 2 * np.sqrt(t + 1)
        q = [(m[2, 1] - m[1, 2]) / s, (m[0, 2] - m[2, 0]) / s, (m[1, 0] - m[0, 1]) / s, s / 4]
    else:
        i = int(np.argmax(np.diag(m)))
        j, k = (i + 1) % 3, (i + 2) % 3
        s = 2 * np.sqrt(1 + m[i, i] - m[j, j] - m[k, k])
        q = [0, 0, 0, (m[k, j] - m[j, k]) / s]
        q[i] = s / 4
        q[j] = (m[j, i] + m[i, j]) / s
        q[k] = (m[k, i] + m[i, k]) / s
    q = np.array(q, float)
    q /= np.linalg.norm(q)
    return q if q[3] >= 0 else -q


def axis_angle(axis, deg):
    a = np.radians(deg)
    axis = np.asarray(axis, float) / np.linalg.norm(axis)
    c, s = np.cos(a), np.sin(a)
    x, y, z = axis
    return np.array([[c + x * x * (1 - c), x * y * (1 - c) - z * s, x * z * (1 - c) + y * s],
                     [y * x * (1 - c) + z * s, c + y * y * (1 - c), y * z * (1 - c) - x * s],
                     [z * x * (1 - c) - y * s, z * y * (1 - c) + x * s, c + z * z * (1 - c)]])


def euler_xyz_to_mat(deg):
    """three.js Euler order 'XYZ': R = Rx(x) · Ry(y) · Rz(z) (intrinsic X, then Y, then Z)."""
    return axis_angle([1, 0, 0], deg[0]) @ axis_angle([0, 1, 0], deg[1]) @ axis_angle([0, 0, 1], deg[2])


def mat_to_euler_xyz(m):
    """Inverse of euler_xyz_to_mat, same branch rules as three.js Euler.setFromRotationMatrix('XYZ')."""
    y = np.arcsin(np.clip(m[0, 2], -1, 1))
    if abs(m[0, 2]) < 0.9999999:
        x = np.arctan2(-m[1, 2], m[2, 2])
        z = np.arctan2(-m[0, 1], m[0, 0])
    else:
        x = np.arctan2(m[2, 1], m[1, 1])
        z = 0.0
    return np.degrees([x, y, z])


# ---------------------------------------------------------------- rest skeleton
def _unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def rest_frames(heads, leaf_dirs):
    """Global rest rotation (columns X, Y, Z) of every bone from joint head positions.

    heads: {bone: xyz}; leaf_dirs: {bone: direction} for bones without a single chain child
    (head, ball_*, *_03 fingers). Rules (README 'Rest frames'):
      +Y  head -> tail (tail = head of the chain child, hand -> middle_01).
      center, leg:  X = world +X projected perpendicular to Y.
      clavicle:     X = Y x (world +Z)               (Z faces front).
      upper/lower arm: X = Y_upperarm x Y_lowerarm   (the rest elbow-bend axis; +X = elbow flexion).
      hand, fingers, thumb: Z = palm normal projected (+X = flexion towards the palm).
    """
    tail_child = {}
    for b in BONES:
        kids = CHILDREN[b]
        if b.startswith("hand_"):
            tail_child[b] = "middle_01_" + b[-1]
        elif b == "spine_03":
            tail_child[b] = "spine_04"
        elif b == "pelvis":
            tail_child[b] = "spine_01"
        elif len(kids) == 1:
            tail_child[b] = kids[0]
    ydir = {}
    for b in BONES:
        ydir[b] = _unit(heads[tail_child[b]] - heads[b]) if b in tail_child else _unit(leaf_dirs[b])
    frames = {}
    for b in BONES:
        Y = ydir[b]
        cls = FRAME_CLASS[b]
        side = b[-1]
        if cls in ("center", "leg"):
            X = _unit(np.array([1.0, 0, 0]) - Y[0] * Y)
            Z = np.cross(X, Y)
        elif cls == "clavicle":
            X = _unit(np.cross(Y, [0.0, 0, 1]))
            Z = np.cross(X, Y)
        elif cls == "arm":
            X = _unit(np.cross(ydir["upperarm_" + side], ydir["lowerarm_" + side]))
            X = _unit(X - (X @ Y) * Y)
            Z = np.cross(X, Y)
        else:  # hand chain
            sgn = 1.0 if side == "l" else -1.0
            hand = "hand_" + side
            palm = sgn * np.cross(ydir[hand], heads["index_01_" + side] - heads["pinky_01_" + side])
            Zr = _unit(palm)
            X = _unit(np.cross(Y, Zr))
            Z = np.cross(X, Y)
        frames[b] = np.column_stack([X, Y, Z])
    return frames


class Skeleton:
    """Rest skeleton of one model: global rest matrices, local rest TRS, inverse bind matrices."""

    def __init__(self, heads, frames):
        self.heads = {b: np.asarray(heads[b], float) for b in BONES}
        self.frames = frames
        self.rest_global = np.zeros((len(BONES), 4, 4))
        for i, b in enumerate(BONES):
            M = np.eye(4)
            M[:3, :3] = frames[b]
            M[:3, 3] = self.heads[b]
            self.rest_global[i] = M
        self.local_t, self.local_q = {}, {}
        for i, b in enumerate(BONES):
            P = np.eye(4) if PARENT[b] is None else self.rest_global[INDEX[PARENT[b]]]
            L = np.linalg.inv(P) @ self.rest_global[i]
            self.local_t[b] = L[:3, 3]
            self.local_q[b] = mat_to_quat(L[:3, :3])
        self.inverse_bind = np.linalg.inv(self.rest_global)
        self.hips_height = float(self.heads["pelvis"][1])

    @classmethod
    def from_glb(cls, path):
        """Rest skeleton read back from a rig/*.glb (node TRS)."""
        g, _ = read_glb(path)
        nodes = {n["name"]: n for n in g["nodes"]}
        G = {}
        for b in BONES:
            n = nodes[b]
            L = np.eye(4)
            L[:3, :3] = quat_to_mat(n.get("rotation", [0, 0, 0, 1]))
            L[:3, 3] = n.get("translation", [0, 0, 0])
            G[b] = L if PARENT[b] is None else G[PARENT[b]] @ L
        return cls({b: G[b][:3, 3] for b in BONES}, {b: G[b][:3, :3] for b in BONES})

    def pose_globals(self, pose):
        """Global 4x4 of every bone for a pose {'bones': {name: quat}, 'root_offset': xyz metres}.

        local = T(rest translation [+ root offset for pelvis]) · R(rest_local_q) · R(pose_q)
        """
        G = np.zeros((len(BONES), 4, 4))
        rots = pose.get("bones", {})
        for i, b in enumerate(BONES):
            L = np.eye(4)
            R = quat_to_mat(self.local_q[b])
            if b in rots:
                R = R @ quat_to_mat(rots[b])
            L[:3, :3] = R
            L[:3, 3] = self.local_t[b]
            if PARENT[b] is None:
                L[:3, 3] = L[:3, 3] + np.asarray(pose.get("root_offset", [0, 0, 0]), float)
                G[i] = L
            else:
                G[i] = G[INDEX[PARENT[b]]] @ L
        return G

    def skin(self, pose, pos, joints, weights):
        """Linear blend skinning (glTF): v' = sum_k w_k · G_k · IBM_k · v."""
        S = self.pose_globals(pose) @ self.inverse_bind
        hom = np.column_stack([pos, np.ones(len(pos))])
        out = np.zeros((len(pos), 3))
        for k in range(joints.shape[1]):
            M = S[joints[:, k]]
            out += weights[:, k:k + 1] * np.einsum("nij,nj->ni", M, hom)[:, :3]
        return out


# ---------------------------------------------------------------- rigged model loading
class RigModel:
    """A rig/*.glb: one canonical vertex pool, primitives (material, triangles), skin."""

    def __init__(self, path):
        g, b = read_glb(path)
        self.path = Path(path)
        self.gltf = g
        prim = g["meshes"][0]["primitives"]
        at = prim[0]["attributes"]
        self.pos = accessor(g, b, at["POSITION"]).astype(float)
        self.nrm = accessor(g, b, at["NORMAL"]).astype(float)
        self.joints = accessor(g, b, at["JOINTS_0"]).astype(int)
        self.weights = accessor(g, b, at["WEIGHTS_0"]).astype(float)
        self.tris, self.tri_mat = [], []
        for p in prim:
            t = accessor(g, b, p["indices"]).reshape(-1, 3).astype(int)
            self.tris.append(t)
            self.tri_mat.append(np.full(len(t), p.get("material", 0)))
        self.tri = np.vstack(self.tris)
        self.tri_mat = np.concatenate(self.tri_mat)
        skin = g["skins"][0]
        assert [g["nodes"][j]["name"] for j in skin["joints"]] == BONES, "joint order differs from SKELETON"
        self.skeleton = Skeleton.from_glb(path)

    def dominant_bone(self):
        return np.array(BONES)[self.joints[np.arange(len(self.pos)), self.weights.argmax(1)]]


def load_pose(path):
    """Pose JSON -> {'bones': {name: quat}, 'root_offset_ratio': xyz}. The viewer uses quaternions only."""
    d = json.loads(Path(path).read_text())
    bones = {k: np.array(v["quaternion"], float) for k, v in d.get("bones", {}).items()}
    return {"bones": bones, "root_offset_ratio": np.array(d.get("root", {}).get("translation", [0, 0, 0]), float),
            "raw": d}


def pose_for(skel, pose):
    """Resolve hips-height-relative root translation for one model."""
    return {"bones": pose["bones"], "root_offset": pose["root_offset_ratio"] * skel.hips_height}


def shell_components(pos, tri):
    """Connected shells (vertices welded by position at 0.01 mm). Returns (component per vertex, per triangle)."""
    _, weld = np.unique(np.round(pos / 1e-5).astype(np.int64), axis=0, return_inverse=True)
    weld = weld.ravel()
    parent = np.arange(weld.max() + 1)

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for a, b, c in weld[tri]:
        for u, v in ((a, b), (b, c)):
            ru, rv = find(u), find(v)
            if ru != rv:
                parent[max(ru, rv)] = min(ru, rv)
    comp_w = np.array([find(i) for i in range(len(parent))])
    _, comp_w = np.unique(comp_w, return_inverse=True)
    comp_v = comp_w[weld]
    return comp_v, comp_v[tri[:, 0]]
