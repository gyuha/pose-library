"""Pose authoring helpers. Imports rig/tools read-only; never writes into rig/.

Moved into the repository from /tmp/pose-author/lib.py (pose-gallery-3d-1of2 follow-up).
Render sheets go to $POSE_AUTHOR_OUT (default /tmp/pose-author/out)."""
import os
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "rig" / "tools"))
sys.path.insert(0, str(REPO / "tests"))
import rigcore  # noqa: E402
import render_pose  # noqa: E402
import check_penetration as cp  # noqa: E402
from author_pose_01 import Poser, solve, quat  # noqa: E402,F401

LIMITS = json.loads((REPO / "rig" / "joint_limits.json").read_text())["joints"]
OUT = Path(os.environ.get("POSE_AUTHOR_OUT", "/tmp/pose-author/out"))
OUT.mkdir(parents=True, exist_ok=True)

_M, _P, _PARTS, _PID = {}, {}, {}, {}


def model(name):
    if name not in _M:
        _M[name] = rigcore.RigModel(REPO / "rig" / f"{name}.glb")
    return _M[name]


def poser(name):
    if name not in _P:
        _P[name] = Poser(model(name))
    return _P[name]


def parts(name):
    if name not in _PARTS:
        _PARTS[name] = cp.Parts(model(name))
    return _PARTS[name]


def pose_dict(euler, root_ratio, name):
    m = model(name)
    return {"bones": {b: quat(e) for b, e in euler.items()},
            "root_offset": np.asarray(root_ratio, float) * m.skeleton.hips_height}


def skin(name, euler, root_ratio):
    m = model(name)
    return m.skeleton.skin(pose_dict(euler, root_ratio, name), m.pos, m.joints, m.weights)


def globals_(name, euler, root_ratio):
    return model(name).skeleton.pose_globals(pose_dict(euler, root_ratio, name))


def sole_mask(name):
    return np.isin(model(name).dominant_bone(), ["foot_l", "foot_r", "ball_l", "ball_r"])


def lows(euler, root_ratio):
    """{model: (lowest sole y, lowest body y)} in metres."""
    out = {}
    for n in ("female", "male"):
        V = skin(n, euler, root_ratio)
        out[n] = (float(V[sole_mask(n), 1].min()), float(V[:, 1].min()))
    return out


def ground(euler, root_ratio, mode="sole", airborne=0.0):
    """Shift root y (hips-height ratio) so the lowest sole ('sole') or body vertex ('body') sits at y=airborne.
    Uses the mean of the female and male required ratios so both models land inside the tolerance."""
    r = np.array(root_ratio, float)
    need = []
    for n in ("female", "male"):
        V = skin(n, euler, r)
        low = V[sole_mask(n), 1].min() if mode == "sole" else V[:, 1].min()
        need.append(r[1] - (low - airborne) / model(n).skeleton.hips_height)
    r[1] = float(np.mean(need))
    return r


def limit_errors(euler):
    errs = []
    for b, e in euler.items():
        lim = LIMITS[b]
        # check the Euler that the quaternion decomposes back to (what check_limits does)
        back = rigcore.mat_to_euler_xyz(rigcore.quat_to_mat(quat(e)))
        for a, v in zip("xyz", back):
            lo, hi = lim[a]
            if v < lo - 0.05 or v > hi + 0.05:
                errs.append(f"{b}.{a}={v:.2f} not in [{lo},{hi}]")
    return errs


EXTRA_PAIRS = [
    ("leg_l", "torso", "avoid"), ("leg_r", "torso", "avoid"),
    ("hand_l", "leg_l", "avoid"), ("hand_l", "leg_r", "avoid"), ("hand_r", "leg_l", "avoid"),
    ("upperarm_l", "pelvis", "avoid"), ("lowerarm_l", "pelvis", "avoid"), ("hand_l", "pelvis", "avoid"),
]
PAIRS = [p for p in cp.PAIRS if p[2] != "hidden"] + EXTRA_PAIRS
_REST = {}


def penetration(euler, root_ratio, show_all=False):
    res = {}
    for n in ("female", "male"):
        V = skin(n, euler, root_ratio)
        rows = {}
        for a, b, kind in PAIRS:
            key = (n, a, b)
            if key not in _REST:
                _REST[key] = parts(n).measure(model(n).pos, a, b)
            rp = parts(n).measure(V, a, b)
            d = max(0.0, rp["max_depth_mm"] - _REST[key]["max_depth_mm"])
            if d > 0 or show_all:
                rows[f"{a}~{b}"] = (round(d, 1), rp["inside_vertices"] - _REST[key]["inside_vertices"], rp["min_gap_mm"])
        res[n] = rows
    return res


VIEWS_EXTRA = {"back_three_quarter": ((-2.6, 1.2, -3.6), (0.0, 0.88, 0.0), 26.0),
               "top": ((0.0, 4.5, 3.0), (0.0, 0.5, 0.0), 30.0)}
render_pose.VIEWS.update(VIEWS_EXTRA)


def render_sheet(euler, root_ratio, tag, views=("front", "three_quarter", "side")):
    cells = []
    for n in ("female", "male"):
        m = model(n)
        if n not in _PID:
            _PID[n] = render_pose.part_ids(m)
        V = skin(n, euler, root_ratio)
        scale = m.skeleton.hips_height / render_pose.FEMALE_HIPS
        for v in views:
            img = render_pose.render(V, m.tri, m.tri_mat, _PID[n], v, scale)
            img = render_pose.floor_line(img, v, scale).resize((300, 400), Image.LANCZOS)
            ImageDraw.Draw(img).text((4, 4), f"{n} {v}", fill=(20, 20, 20))
            cells.append(img)
    sheet = Image.new("RGB", (300 * len(views), 800), "white")
    for i, c in enumerate(cells):
        sheet.paste(c, ((i % len(views)) * 300, (i // len(views)) * 400))
    p = OUT / f"{tag}.png"
    sheet.save(p)
    return p


def report(euler, root_ratio, tag, render=True, views=("front", "three_quarter", "side")):
    print("limits:", limit_errors(euler) or "OK")
    print("lows (sole, body) mm:", {n: tuple(round(v * 1e3, 1) for v in t) for n, t in lows(euler, root_ratio).items()})
    print("penetration (new depth mm, new inside, gap):", json.dumps(penetration(euler, root_ratio), ensure_ascii=False))
    if render:
        print("sheet:", render_sheet(euler, root_ratio, tag, views))


def write_pose(pose_id, name, description, assumptions, euler, root_ratio, generator):
    bones = {}
    for b in rigcore.BONES:
        if b in euler and np.abs(euler[b]).max() > 1e-6:
            q = quat(euler[b])
            bones[b] = {"quaternion": [round(float(v), 7) for v in q],
                        "euler": {"order": "XYZ", "degrees": [round(float(v), 3) for v in euler[b]]}}
    doc = {
        "$schema": "./schema.json",
        "formatVersion": 1,
        "skeleton": rigcore.SKELETON_ID,
        "meta": {"id": pose_id, "name": name, "description": description, "targetModels": ["female", "male"],
                 "assumptions": assumptions, "generator": generator},
        "root": {"translation": [round(float(v), 6) for v in root_ratio], "unit": "hipsHeight"},
        "bones": bones,
    }
    p = REPO / "poses" / f"{pose_id}.json"
    p.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    return p


def ik(euler, root_ratio, dofs, targets, name="female", extra=(), iters=150, bounds=None):
    """targets: [(bone, world xyz of the bone head, weight)] (+ extra objective callables of G).
    bounds: {bone: {axis: [lo, hi]}} tighter than the joint limits."""
    lim = {b: dict(v) for b, v in LIMITS.items()}
    for b, ax in (bounds or {}).items():
        lim[b].update(ax)
    P = poser(name)
    hh = model(name).skeleton.hips_height
    objs = [(lambda G, b=b, t=np.asarray(t, float), w=w: (G[rigcore.INDEX[b]][:3, 3] - t) * w) for b, t, w in targets]
    objs += list(extra)
    prefer = {b: list(e) for b, e in euler.items()}
    e, r, c = solve(P, {b: list(v) for b, v in euler.items()}, np.asarray(root_ratio, float) * hh, dofs, objs, lim,
                    prefer, iters=iters)
    return e, r / hh, c


def heads_posed(name, euler, root_ratio, bones):
    G = globals_(name, euler, root_ratio)
    return {b: np.round(G[rigcore.INDEX[b]][:3, 3], 3) for b in bones}


def arm_dofs(s, hand=True):
    d = [(f"upperarm_{s}", a) for a in range(3)] + [(f"lowerarm_{s}", 0), (f"lowerarm_{s}", 1)]
    return d + ([(f"hand_{s}", a) for a in range(3)] if hand else [])


def fingers(euler, s, curl=(10, 15, 10), thumb=((0, 0, 0), 0, 0)):
    for k in ("index", "middle", "ring", "pinky"):
        for j, c in enumerate(curl):
            euler[f"{k}_0{j + 1}_{s}"] = [float(c), 0.0, 0.0]
    t1, t2, t3 = thumb
    euler[f"thumb_01_{s}"] = list(map(float, t1))
    euler[f"thumb_02_{s}"] = [float(t2), 0.0, 0.0]
    euler[f"thumb_03_{s}"] = [float(t3), 0.0, 0.0]
    return euler


def _unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def local_q_mat(name, b):
    return rigcore.quat_to_mat(model(name).skeleton.local_q[b])


def set_global(euler, root_ratio, bone, R_target, name="female"):
    """Set euler[bone] so the bone's global rotation equals R_target (parent chain from current euler)."""
    G = globals_(name, euler, root_ratio)
    par = rigcore.PARENT[bone]
    Rp = G[rigcore.INDEX[par]][:3, :3] if par else np.eye(3)
    q = (Rp @ local_q_mat(name, bone)).T @ R_target
    euler[bone] = [float(v) for v in rigcore.mat_to_euler_xyz(q)]
    return euler


def place_limb(euler, root_ratio, upper, lower, mid, end, hint_x=None, lower_twist=0.0, name="female"):
    """Two-bone placement: upper bone head -> mid (elbow/knee) -> end (wrist/ankle). The bend axis is
    X = Y_upper x (forearm/shin direction); +X on the lower bone is the flexion."""
    G = globals_(name, euler, root_ratio)
    S = G[rigcore.INDEX[upper]][:3, 3]
    Y = _unit(np.asarray(mid, float) - S)
    f = _unit(np.asarray(end, float) - np.asarray(mid, float))
    perp = f - (f @ Y) * Y
    if np.linalg.norm(perp) < 1e-3:
        X = _unit(np.asarray(hint_x, float) - (np.asarray(hint_x, float) @ Y) * Y)
    else:
        Z = _unit(perp)
        X = np.cross(Y, Z)
    R_up = np.column_stack([X, Y, np.cross(X, Y)])
    set_global(euler, root_ratio, upper, R_up, name)
    euler[lower] = [0.0, 0.0, 0.0]
    G = globals_(name, euler, root_ratio)
    Rl = G[rigcore.INDEX[lower]][:3, :3]
    fl = Rl.T @ f
    th = np.degrees(np.arctan2(fl[2], fl[1]))
    euler[lower] = [float(th), float(lower_twist), 0.0]
    return euler


def yaw(deg):
    return rigcore.euler_xyz_to_mat([0, deg, 0])


def rest_global_R(bone, name="female"):
    return model(name).skeleton.rest_global[rigcore.INDEX[bone]][:3, :3]


def bone_len(a, b, name="female"):
    h = model(name).skeleton.heads
    return float(np.linalg.norm(h[a] - h[b]))


def two_bone(euler, root_ratio, upper, lower, end, target, pole, lower_twist=0.0, name="female", stretch=0.999):
    """Analytic 2-bone IK: put the head of `end` at `target`, bending towards `pole` (world direction)."""
    h = model(name).skeleton.heads
    L1 = np.linalg.norm(h[lower] - h[upper])
    L2 = np.linalg.norm(h[end] - h[lower])
    G = globals_(name, euler, root_ratio)
    H = G[rigcore.INDEX[upper]][:3, 3]
    t = np.asarray(target, float)
    d = np.linalg.norm(t - H)
    d = min(d, stretch * (L1 + L2))
    u = _unit(t - H)
    t = H + u * d
    p = np.asarray(pole, float)
    v = _unit(p - (p @ u) * u)
    ca = np.clip((L1 * L1 + d * d - L2 * L2) / (2 * L1 * d), -1, 1)
    knee = H + L1 * (ca * u + np.sqrt(1 - ca * ca) * v)
    return place_limb(euler, root_ratio, upper, lower, knee, t, hint_x=np.cross(u, v), lower_twist=lower_twist, name=name)


def flat_foot(euler, root_ratio, s, toe_yaw, name="female", extra_pitch=0.0):
    """Foot flat like at rest, toes yawed (deg, + = towards the character's left), optional heel raise."""
    R = yaw(toe_yaw) @ rest_global_R(f"foot_{s}", name)
    if extra_pitch:
        R = rigcore.axis_angle(yaw(toe_yaw)[:, 0], extra_pitch) @ R
    return set_global(euler, root_ratio, f"foot_{s}", R, name)


def ankle_y(name="female"):
    return float(model(name).skeleton.heads["foot_l"][1])


ARMS_DOWN = {"upperarm_l": [0.0, 0.0, -28.0], "upperarm_r": [0.0, 0.0, 28.0],
             "lowerarm_l": [-12.0, 0.0, 0.0], "lowerarm_r": [-12.0, 0.0, 0.0]}


def violation(euler, bones):
    v = 0.0
    for b in bones:
        back = rigcore.mat_to_euler_xyz(rigcore.quat_to_mat(quat(euler[b])))
        for a, x in zip("xyz", back):
            lo, hi = LIMITS[b][a]
            v += max(0.0, lo - x, x - hi)
    return v


def arm_with_hand(euler, root_ratio, s, elbow, wrist, R_hand, name="female"):
    """Place the arm (elbow, wrist targets), then pick the forearm twist so the hand reaches R_hand
    with the least joint-limit violation (hand y range is small)."""
    best = None
    for tw in range(-85, 86, 5):
        e = {b: list(v) for b, v in euler.items()}
        place_limb(e, root_ratio, f"upperarm_{s}", f"lowerarm_{s}", elbow, wrist, lower_twist=tw, name=name)
        set_global(e, root_ratio, f"hand_{s}", R_hand, name)
        cost = violation(e, [f"upperarm_{s}", f"lowerarm_{s}", f"hand_{s}"]) * 10 + abs(e[f"hand_{s}"][1])
        if best is None or cost < best[0]:
            best = (cost, e)
    euler.clear()
    euler.update(best[1])
    return best[0]


def frame_from(y_dir, z_dir):
    Y = _unit(y_dir)
    Z = _unit(np.asarray(z_dir, float) - (np.asarray(z_dir, float) @ Y) * Y)
    return np.column_stack([np.cross(Y, Z), Y, Z])


def arm_ik(euler, root_ratio, s, wrist, pole, R_hand, name="female", stretch=0.999):
    """two_bone arm to the wrist + forearm twist search so the hand reaches R_hand within limits."""
    best = None
    for tw in range(-85, 86, 5):
        e = {b: list(v) for b, v in euler.items()}
        two_bone(e, root_ratio, f"upperarm_{s}", f"lowerarm_{s}", f"hand_{s}", wrist, pole, lower_twist=tw, name=name,
                 stretch=stretch)
        set_global(e, root_ratio, f"hand_{s}", R_hand, name)
        cost = violation(e, [f"upperarm_{s}", f"lowerarm_{s}", f"hand_{s}"]) * 10 + abs(e[f"hand_{s}"][1])
        if best is None or cost < best[0]:
            best = (cost, e)
    euler.clear()
    euler.update(best[1])
    return best[0]


def axis_obj(bone, col, direction, w=10.0):
    """objective: column `col` (0=X,1=Y,2=Z) of the bone's global rotation points along `direction`."""
    d = _unit(direction)
    return lambda G: (G[rigcore.INDEX[bone]][:3, col] - d) * w


def lowest(name, euler, root_ratio, bones):
    V = skin(name, euler, root_ratio)
    return float(V[np.isin(model(name).dominant_bone(), bones), 1].min())


HAND_BONES = {s: [f"hand_{s}"] + [f"{f}_0{k}_{s}" for f in ("thumb", "index", "middle", "ring", "pinky") for k in (1, 2, 3)]
              for s in "lr"}


def foot_on_ball(s, ball_xz, toe_yaw, heel_raise, name="female"):
    """Ankle target and foot rotation for a foot standing on its ball (heel raised by heel_raise deg)."""
    h = model(name).skeleton.heads
    R = rigcore.axis_angle(yaw(toe_yaw)[:, 0], heel_raise) @ yaw(toe_yaw) @ rest_global_R(f"foot_{s}", name)
    Rrest = rest_global_R(f"foot_{s}", name)
    v = R @ Rrest.T @ (h[f"foot_{s}"] - h[f"ball_{s}"])
    ball = np.array([ball_xz[0], h[f"ball_{s}"][1], ball_xz[1]])
    return ball + v, R


def place_leg(euler, root_ratio, s, ankle, pole, R_foot, name="female"):
    two_bone(euler, root_ratio, f"thigh_{s}", f"calf_{s}", f"foot_{s}", ankle, pole, name=name)
    set_global(euler, root_ratio, f"foot_{s}", R_foot, name)
    return euler
