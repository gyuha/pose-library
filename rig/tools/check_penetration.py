"""Penetration / contact check of a posed rig between body parts (rest pose as the baseline).

    /tmp/pose-qa-venv/bin/python rig/tools/check_penetration.py poses/pose_01_contrapposto_hand_on_head.json

Each closed mesh shell belongs to the part of its majority dominant bone. For every checked pair (A, B), in the
pose and at rest:
  * inside_vertices / max_depth_mm: vertices of A inside a closed shell of B (generalized winding number > 0.5,
    shells of B tested one by one) and their deepest distance to that shell's surface; both directions;
  * crossing_edges: edges of A that cross a triangle of B, and vice versa;
  * min_gap_mm: smallest vertex-to-surface distance between A and B (0 when they intersect).
'new' = pose minus rest, so overlaps already built into the rest mannequin (e.g. shoulder filler inside the
chest) are not counted as pose problems. Writes rig/validation/penetration_<pose id>.json.
"""
import json
import sys
from pathlib import Path

import numpy as np

from rigcore import RIG, RigModel, load_pose, pose_for, shell_components

PARTS = {
    "head": ["head", "neck_01"],
    "torso": ["spine_01", "spine_02", "spine_03", "spine_04"],
    "pelvis": ["pelvis"],
}
for s in "lr":
    PARTS[f"upperarm_{s}"] = [f"upperarm_{s}", f"clavicle_{s}"]
    PARTS[f"lowerarm_{s}"] = [f"lowerarm_{s}"]
    PARTS[f"hand_{s}"] = [f"hand_{s}"] + [f"{f}_0{k}_{s}" for f in ("thumb", "index", "middle", "ring", "pinky") for k in (1, 2, 3)]
    PARTS[f"leg_{s}"] = [f"thigh_{s}", f"calf_{s}", f"foot_{s}", f"ball_{s}"]
PAIRS = [  # (A, B, kind) kind: 'avoid' = should not touch, 'contact' = intended contact, 'hidden' = built-in overlap
    ("shoulder_filler_l", "torso", "hidden"), ("shoulder_filler_r", "torso", "hidden"),
    ("upperarm_l", "head", "avoid"), ("lowerarm_l", "head", "avoid"), ("hand_l", "head", "contact"),
    ("upperarm_r", "head", "avoid"), ("lowerarm_r", "head", "avoid"), ("hand_r", "head", "avoid"),
    ("upperarm_l", "torso", "avoid"), ("lowerarm_l", "torso", "avoid"), ("hand_l", "torso", "avoid"),
    ("upperarm_r", "torso", "avoid"), ("lowerarm_r", "torso", "avoid"), ("hand_r", "torso", "avoid"),
    ("lowerarm_r", "pelvis", "avoid"), ("hand_r", "pelvis", "contact"), ("upperarm_r", "pelvis", "avoid"),
    ("leg_l", "leg_r", "avoid"), ("hand_r", "leg_r", "avoid"),
]


def winding(points, tris):
    """Generalized winding number of points w.r.t. a triangle soup (Van Oosterom-Strackee solid angles)."""
    a = tris[None, :, 0] - points[:, None]
    b = tris[None, :, 1] - points[:, None]
    c = tris[None, :, 2] - points[:, None]
    la, lb, lc = (np.linalg.norm(v, axis=2) for v in (a, b, c))
    det = np.einsum("pti,pti->pt", a, np.cross(b, c))
    den = la * lb * lc + np.einsum("pti,pti->pt", a, b) * lc + np.einsum("pti,pti->pt", b, c) * la + \
        np.einsum("pti,pti->pt", c, a) * lb
    return np.arctan2(det, den).sum(1) / (2 * np.pi)


def point_tri_dist(p, T):
    """Distance from one point to each triangle: plane distance if the projection is inside, else nearest edge."""
    a, b, c = T[:, 0], T[:, 1], T[:, 2]
    n = np.cross(b - a, c - a)
    nn = np.maximum(np.einsum("ij,ij->i", n, n), 1e-30)
    t = np.einsum("ij,ij->i", p - a, n) / nn
    q = p - t[:, None] * n
    inside = np.ones(len(T), bool)
    for u, v in ((a, b), (b, c), (c, a)):
        inside &= np.einsum("ij,ij->i", np.cross(v - u, q - u), n) >= 0
    d = np.abs(t) * np.sqrt(nn)

    def seg(u, v):
        uv = v - u
        s = np.clip(np.einsum("ij,ij->i", p - u, uv) / np.maximum(np.einsum("ij,ij->i", uv, uv), 1e-30), 0, 1)
        return np.linalg.norm(p - (u + s[:, None] * uv), axis=1)
    return np.where(inside, d, np.minimum(np.minimum(seg(a, b), seg(b, c)), seg(c, a)))


def crossing_edges(V, edges, T):
    """Number of segments (edges) that cross any triangle of T."""
    p0, p1 = V[edges[:, 0]], V[edges[:, 1]]
    d = p1 - p0
    e1, e2 = T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]
    n = 0
    for i in range(len(edges)):
        h = np.cross(d[i], e2)
        det = np.einsum("ij,ij->i", e1, h)
        ok = np.abs(det) > 1e-14
        inv = np.where(ok, 1 / np.where(ok, det, 1), 0)
        s = p0[i] - T[:, 0]
        u = np.einsum("ij,ij->i", s, h) * inv
        q = np.cross(s, e1)
        v = (q @ d[i]) * inv
        t = np.einsum("ij,ij->i", e2, q) * inv
        n += bool((ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t >= 0) & (t <= 1)).any())
    return n


class Parts:
    def __init__(self, model):
        self.m = model
        _, self.comp_t = shell_components(model.pos, model.tri)
        dom = model.dominant_bone()
        bone_part = {b: p for p, bones in PARTS.items() for b in bones}
        self.shells = {p: [] for p in list(PARTS) + ["shoulder_filler_l", "shoulder_filler_r"]}
        for k in np.unique(self.comp_t):
            tri = model.tri[self.comp_t == k]
            names, counts = np.unique(dom[np.unique(tri)], return_counts=True)
            part = bone_part.get(names[counts.argmax()])
            if part:
                self.shells[part].append(tri)
        # the dark shoulder filler (Joints material) sits inside the chest at rest by design; report it apart
        for s in "lr":
            joint = model.skeleton.heads["upperarm_" + s]
            joints_mat = [t for t in self.shells["upperarm_" + s] if model.tri_mat[np.all(model.tri == t[0], axis=1)][0] == 1]
            filler = min(joints_mat, key=lambda t: np.linalg.norm(model.pos[np.unique(t)].mean(0) - joint))
            self.shells["upperarm_" + s] = [t for t in self.shells["upperarm_" + s] if t is not filler]
            self.shells["shoulder_filler_" + s] = [filler]

    def measure(self, V, A, B):
        res = {"inside_vertices": 0, "max_depth_mm": 0.0, "crossing_edges": 0}
        for X, Y in ((A, B), (B, A)):
            vx = np.unique(np.vstack(self.shells[X]))
            for tri in self.shells[Y]:
                T = V[tri]
                lo, hi = T.reshape(-1, 3).min(0) - 1e-3, T.reshape(-1, 3).max(0) + 1e-3
                cand = vx[np.all((V[vx] > lo) & (V[vx] < hi), axis=1)]
                if len(cand):
                    inside = cand[np.abs(winding(V[cand], T)) > 0.5]
                    res["inside_vertices"] += len(inside)
                    for i in inside:
                        res["max_depth_mm"] = max(res["max_depth_mm"], float(point_tri_dist(V[i], T).min()) * 1e3)
                ex = np.vstack([np.sort(t[:, [0, 1]], 1) for t in self.shells[X]] + [np.sort(t[:, [1, 2]], 1) for t in self.shells[X]]
                               + [np.sort(t[:, [0, 2]], 1) for t in self.shells[X]])
                ex = np.unique(ex, axis=0)
                ex = ex[np.all((np.minimum(V[ex[:, 0]], V[ex[:, 1]]) < hi) & (np.maximum(V[ex[:, 0]], V[ex[:, 1]]) > lo), axis=1)]
                if len(ex):
                    res["crossing_edges"] += crossing_edges(V, ex, T)
        gap = np.inf
        for X, Y in ((A, B), (B, A)):   # symmetric: vertices of either part to the other part's surface
            vx = np.unique(np.vstack(self.shells[X]))
            TY = V[np.vstack(self.shells[Y])]
            near = vx[np.argsort(np.min(np.linalg.norm(V[vx][:, None] - TY.reshape(-1, 3)[None], axis=2), axis=1))[:40]]
            gap = min(gap, min(float(point_tri_dist(V[i], TY).min()) for i in near))
        res["min_gap_mm"] = 0.0 if res["inside_vertices"] or res["crossing_edges"] else round(gap * 1e3, 2)
        res["max_depth_mm"] = round(res["max_depth_mm"], 2)
        return res


def main(paths):
    for p in paths:
        pose = load_pose(p)
        report = {"pose": str(p), "models": {}}
        for name in ("female", "male"):
            m = RigModel(RIG / f"{name}.glb")
            parts = Parts(m)
            Vp = m.skeleton.skin(pose_for(m.skeleton, pose), m.pos, m.joints, m.weights)
            rows = {}
            for A, B, kind in PAIRS:
                r_rest = parts.measure(m.pos, A, B)
                r_pose = parts.measure(Vp, A, B)
                rows[f"{A}~{B}"] = {"kind": kind, "pose": r_pose, "rest": r_rest,
                                    "new_inside_vertices": r_pose["inside_vertices"] - r_rest["inside_vertices"],
                                    "new_crossing_edges": r_pose["crossing_edges"] - r_rest["crossing_edges"]}
            report["models"][name] = rows
            print(f"{name}:")
            for k, r in rows.items():
                if r["pose"]["inside_vertices"] or r["pose"]["crossing_edges"] or r["kind"] == "contact" or r["pose"]["min_gap_mm"] < 10:
                    print(f"  {k:24s} {r['kind']:7s} pose: in={r['pose']['inside_vertices']:3d} depth={r['pose']['max_depth_mm']:6.2f}mm "
                          f"cross={r['pose']['crossing_edges']:3d} gap={r['pose']['min_gap_mm']:6.2f}mm | rest: in={r['rest']['inside_vertices']} "
                          f"depth={r['rest']['max_depth_mm']}mm cross={r['rest']['crossing_edges']}")
        (RIG / "validation" / f"penetration_{Path(p).stem}.json").write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
