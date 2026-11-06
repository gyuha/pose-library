"""Author poses/pose_01_contrapposto_hand_on_head.json from poses/reference/pose_reference_01.png.

    PYTHONDONTWRITEBYTECODE=1 /tmp/pose-qa-venv/bin/python rig/tools/author_pose_01.py

Fitted on rig/female.glb, deterministic:
 * Hand-set Euler angles (degrees, three.js 'XYZ', each bone's rest frame; signs in rig/README.md) for the
   pelvis tilt, the counter-bending spine, neck/head, clavicles and fingers.
 * A projected Levenberg-Marquardt solver (finite differences over Euler DOFs, joint limits as hard bounds)
   places the limbs on contact targets: right sole flat on the floor with a straight knee (support leg), left
   foot on the ball with the heel raised and toes flat, left palm on the crown, right palm on the right hip.
   Elbow directions and the left wrist position are soft targets read from the drawing. A second pass adds
   'hand and touched shell do not interpenetrate' (both directions, 1 mm clearance).
 * The root height is then set so that the lowest vertex of the support foot is exactly on y = 0.
"""
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np

from check_penetration import point_tri_dist, winding
from rigcore import (BONES, INDEX, RIG, ROOT, SKELETON_ID, RigModel, axis_angle, euler_xyz_to_mat, mat_to_quat,
                     shell_components)

POSE_ID = "pose_01_contrapposto_hand_on_head"
REF_ORIGINAL = Path("/tmp/pose-ref/pose_reference_01.png")
REF = ROOT / "poses" / "reference" / "pose_reference_01.png"

# ---------------------------------------------------------------- hand-set rotations (degrees)
FIXED = {
    # contrapposto: weight on the right leg, right hip up / left hip down; pelvis turned slightly to its left
    "pelvis": [2.0, 6.0, -7.0],
    # spine bends back to the right so the shoulder line tilts the other way (left shoulder up)
    "spine_01": [0.0, -1.0, 2.0],
    "spine_02": [-2.0, -1.0, 3.0],
    "spine_03": [-2.0, -2.0, 2.0],
    "spine_04": [0.0, -1.0, 2.0],
    # head tilted to the character's right, chin up
    "neck_01": [-6.0, 3.0, 2.0],
    "head": [-12.0, 4.0, 4.0],
    # raised left arm: shoulder girdle elevated; hand-on-hip side slightly retracted
    "clavicle_l": [-5.0, 0.0, 20.0],
    "clavicle_r": [-6.0, 0.0, 0.0],
    "calf_r": [-7.0, 0.0, 0.0],          # support knee straight (rest is ~8 deg flexed)
}
FINGERS = {  # (proximal, middle, distal) flexion; thumb (01 xyz, 02 x, 03 x)
    "l": {"curl": (8.0, 12.0, 8.0), "thumb": ([-25.0, 0.0, 0.0], 0.0, 0.0)},     # cupping the crown; thumb lifted off the skull
    "r": {"curl": (2.0, 5.0, 3.0), "thumb": ([-25.0, 0.0, 15.0], 0.0, 0.0)},      # flat on the hip, thumb opened back off the surface
}
ROOT_XZ = np.array([-0.035, 0.0])   # female metres: pelvis shifted over the support (right) foot

# ---------------------------------------------------------------- contact / placement targets (female, metres)
RIGHT_ANKLE_XZ = np.array([-0.165, -0.06])  # support foot under the right hip
RIGHT_TOE_OUT = -8.0                         # yaw of the right foot (deg, - = toes to the character's right)
LEFT_BALL_XZ = np.array([0.255, 0.045])      # left forefoot placed out to the side, a little forward
LEFT_TOE_OUT = 12.0
LEFT_HEEL_RAISE = 28.0                       # extra plantarflexion of the left foot (deg); toes stay flat
CROWN_LOCAL_XZ = (0.03, -0.01)             # palm centre on the crown, head-local (x: towards the left)
LEFT_FINGER_DIR = np.array([-1.0, -0.25, 0.55])  # fingers over the crown, towards the character's right/front
LEFT_ELBOW_DIR = np.array([0.46, 0.87, -0.15])  # shoulder -> elbow: out, up, slightly back (reachable; drawing has it lower)
HIP_HEIGHT = 0.95                            # right palm height on the pelvis shell (rest model space)
HIP_AZIMUTH = 20.0                           # deg from the lateral direction towards the front
RIGHT_FINGER_DIR = np.array([0.6, -0.6, 0.4])   # towards the navel and down
RIGHT_ELBOW_DIR = np.array([-0.70, -0.70, -0.15])  # out to the side and a little back
LEFT_WRIST_HEAD_LOCAL = (0.075, 0.135, -0.01)  # wrist at the upper-left side of the skull, head-local (soft)
LEFT_ARM_STARTS = [([0, 0, 0], [0, 0, 0]), ([40, 0, 110], [90, -40, 0]), ([100, 0, 70], [80, -80, 0]),
                   ([60, -30, 100], [100, 0, 0]), ([20, 20, 130], [100, 60, 0])]
ELBOW_W = 4.0                                # weight of the soft elbow-direction targets
GAP = 0.004                                  # palm stand-off from the surface


def unit(v):
    return np.asarray(v, float) / np.linalg.norm(v)


def quat(e):
    return mat_to_quat(euler_xyz_to_mat(e))


class Poser:
    def __init__(self, model):
        self.m = model
        self.sk = model.skeleton
        _, self.comp_t = shell_components(model.pos, model.tri)
        self.dom = model.dominant_bone()

    def globals(self, euler, root):
        return self.sk.pose_globals({"bones": {b: quat(e) for b, e in euler.items()}, "root_offset": root})

    def shell_of(self, bone, material=0):
        best, n = None, 0
        for k in np.unique(self.comp_t[self.m.tri_mat == material]):
            verts = np.unique(self.m.tri[self.comp_t == k])
            c = int((self.dom[verts] == bone).sum())
            if c > n:
                best, n = k, c
        return self.m.tri[self.comp_t == best]

    def local(self, bone, p):
        G = self.sk.rest_global[INDEX[bone]]
        return G[:3, :3].T @ (p - G[:3, 3])

    def ray_hit(self, bone, origin, direction, nearest, material=0):
        """Nearest (ray from outside) or farthest (ray from inside) intersection of a ray (model space, rest) with
        the bone's shell -> (point, outward normal)."""
        T = self.m.pos[self.shell_of(bone, material)]
        e1, e2 = T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]
        p = np.cross(direction, e2)
        det = np.einsum("ij,ij->i", e1, p)
        ok = np.abs(det) > 1e-12
        inv = np.where(ok, 1 / np.where(ok, det, 1), 0)
        s = origin - T[:, 0]
        u = np.einsum("ij,ij->i", s, p) * inv
        qv = np.cross(s, e1)
        v = (qv @ direction) * inv
        t = np.einsum("ij,ij->i", e2, qv) * inv
        hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 0)
        i = np.where(hit)[0][(np.argmin if nearest else np.argmax)(t[hit])]
        n = unit(np.cross(e1[i], e2[i]))
        if (n @ direction < 0) != nearest:
            n = -n
        return origin + t[i] * direction, n

    def palm_local(self, side):
        """Palm centre on the palm surface, in the hand bone's local frame (+Z = out of the palm): a ray from the
        middle of the hand shell along +Z, at 55 % of the hand length."""
        hand = "hand_" + side
        verts = np.unique(self.shell_of(hand))
        L = np.array([self.local(hand, p) for p in self.m.pos[verts]])
        length = np.linalg.norm(self.sk.heads["middle_01_" + side] - self.sk.heads[hand])
        G = self.sk.rest_global[INDEX[hand]]
        o = G[:3, :3] @ np.array([L[:, 0].mean(), 0.55 * length, L[:, 2].mean()]) + G[:3, 3]
        hit, _ = self.ray_hit(hand, o, G[:3, 2], nearest=False)
        return self.local(hand, hit)


def solve(poser, euler, root, dofs, objectives, limits, prefer, iters=150):
    """Levenberg-Marquardt over Euler DOFs (bone, axis) and ('root', 1). Residuals are pre-scaled.
    A weak prior pulls every DOF towards its preferred value (hand-set angle, else rest)."""
    euler = {b: list(map(float, e)) for b, e in euler.items()}
    root = np.array(root, float)

    def get():
        return np.array([root[a] if b == "root" else euler.setdefault(b, [0.0, 0.0, 0.0])[a] for b, a in dofs])

    def put(x):
        for (b, a), v in zip(dofs, x):
            if b == "root":
                root[a] = v
            else:
                euler[b][a] = v

    def residual(x):
        put(x)
        G = poser.globals(euler, root)
        r = [f(G) for f in objectives]
        for b, a in dofs:
            if b != "root":
                lo, hi = limits[b]["xyz"[a]]
                v = euler[b][a]
                v0 = prefer.get(b, [0.0, 0.0, 0.0])[a]
                r.append([max(0.0, lo + 1 - v, v - (hi - 1)) * 5.0, (v - v0) / 120.0])   # limit penalty (1 deg inside), weak prior
        return np.concatenate([np.atleast_1d(np.asarray(v, float)) for v in r])

    lo = np.array([-np.inf if b == "root" else limits[b]["xyz"[a]][0] for b, a in dofs])
    hi = np.array([np.inf if b == "root" else limits[b]["xyz"[a]][1] for b, a in dofs])
    x = np.clip(get(), lo, hi)       # joint limits are hard: every step is projected back inside
    r = residual(x)
    mu = 1e-2
    for _ in range(iters):
        J = np.zeros((len(r), len(x)))
        for k in range(len(x)):
            h = 1e-5 if dofs[k][0] == "root" else 1e-3
            xh = x.copy()
            xh[k] += h
            J[:, k] = (residual(xh) - r) / h
        A = J.T @ J
        g = J.T @ r
        while True:
            dx = np.clip(x - np.linalg.solve(A + mu * np.diag(np.diag(A) + 1e-9), g), lo, hi) - x
            rn = residual(x + dx)
            if rn @ rn < r @ r:
                x, r, mu = x + dx, rn, max(mu / 3, 1e-7)
                break
            mu *= 4
            if mu > 1e8:
                break
        if mu > 1e8 or np.abs(dx).max() < 1e-6:
            break
    put(x)
    return euler, root, float(r @ r)


def main():
    m = RigModel(RIG / "female.glb")
    P = Poser(m)
    sk = m.skeleton
    limits = json.loads((RIG / "joint_limits.json").read_text())["joints"]
    euler = {b: list(e) for b, e in FIXED.items()}
    for s, f in FINGERS.items():
        for k in ("index", "middle", "ring", "pinky"):
            for j, c in enumerate(f["curl"]):
                euler[f"{k}_0{j + 1}_{s}"] = [c, 0.0, 0.0]
        t1, t2, t3 = f["thumb"]
        euler[f"thumb_01_{s}"], euler[f"thumb_02_{s}"], euler[f"thumb_03_{s}"] = list(t1), [t2, 0, 0], [t3, 0, 0]
    root = np.array([ROOT_XZ[0], 0.0, ROOT_XZ[1]])
    prefer = {b: list(e) for b, e in euler.items()}

    rest = sk.rest_global
    yaw = lambda d: euler_xyz_to_mat([0, d, 0])                       # rotation about world Y
    R_foot_r = yaw(RIGHT_TOE_OUT) @ rest[INDEX["foot_r"]][:3, :3]
    R_ball_l = yaw(LEFT_TOE_OUT) @ rest[INDEX["ball_l"]][:3, :3]
    lateral_l = R_ball_l[:, 0]                                        # foot's +X (character's left)
    R_foot_l = axis_angle(lateral_l, LEFT_HEEL_RAISE) @ yaw(LEFT_TOE_OUT) @ rest[INDEX["foot_l"]][:3, :3]
    ankle_y = sk.heads["foot_r"][1]
    ball_y = sk.heads["ball_l"][1]
    foot_l_vec = sk.heads["ball_l"] - sk.heads["foot_l"]               # rest ankle -> ball, rotated with the foot
    foot_l_vec = axis_angle(lateral_l, LEFT_HEEL_RAISE) @ yaw(LEFT_TOE_OUT) @ foot_l_vec

    def rot_err(G, bone, R_target, w=1 / np.radians(2)):
        Rm = G[INDEX[bone]][:3, :3] @ R_target.T
        ang = np.arccos(np.clip((np.trace(Rm) - 1) / 2, -1, 1))
        ax = np.array([Rm[2, 1] - Rm[1, 2], Rm[0, 2] - Rm[2, 0], Rm[1, 0] - Rm[0, 1]])
        return (ax / (2 * np.sin(ang)) * ang if ang > 1e-9 else ax / 2) * w

    pos = lambda G, b, p=np.zeros(3): G[INDEX[b]][:3, :3] @ p + G[INDEX[b]][:3, 3]
    wp = 1 / 0.002

    # --- legs and root height
    leg_obj = [
        lambda G: (pos(G, "foot_r") - [RIGHT_ANKLE_XZ[0], ankle_y, RIGHT_ANKLE_XZ[1]]) * wp,
        lambda G: rot_err(G, "foot_r", R_foot_r),
        lambda G: (pos(G, "ball_l") - [LEFT_BALL_XZ[0], ball_y, LEFT_BALL_XZ[1]]) * wp,
        lambda G: rot_err(G, "foot_l", R_foot_l),
        lambda G: rot_err(G, "ball_l", R_ball_l),
    ]
    leg_dofs = [("root", 1)] + [(b, a) for b in ("thigh_r", "foot_r", "thigh_l", "foot_l") for a in range(3)] + \
               [("calf_l", 0), ("ball_l", 0)]
    euler, root, cost_legs = solve(P, euler, root, leg_dofs, leg_obj, limits, prefer)

    # --- arms: contacts relative to the (already posed) head and pelvis
    head_rest = rest[INDEX["head"]]
    crown_o = head_rest[:3, :3] @ np.array([CROWN_LOCAL_XZ[0], 0.5, CROWN_LOCAL_XZ[1]]) + head_rest[:3, 3]
    crown, _ = P.ray_hit("head", crown_o, -head_rest[:3, 1], nearest=True)
    # contact normal averaged over a palm-sized patch, so the flat palm does not dig into a neighbouring facet
    crown_n = unit(sum(P.ray_hit("head", crown_o + head_rest[:3, :3] @ np.array([dx, 0, dz]), -head_rest[:3, 1], nearest=True)[1]
                       for dx in (-0.025, 0, 0.025) for dz in (-0.025, 0, 0.025)))
    crown_l, crown_nl = P.local("head", crown + GAP * crown_n), head_rest[:3, :3].T @ crown_n
    a = np.radians(HIP_AZIMUTH)
    hip_dir = np.array([-np.cos(a), 0.0, np.sin(a)])
    hip_o = np.array([0.0, HIP_HEIGHT, -0.015])   # inside the pelvis shell, near its centre
    hip, _ = P.ray_hit("pelvis", hip_o, hip_dir, nearest=False)
    hip_n = unit(sum(P.ray_hit("pelvis", hip_o + [0, dy, 0], np.array([-np.cos(a + da), 0.0, np.sin(a + da)]), nearest=False)[1]
                     for dy in (-0.02, 0, 0.02) for da in np.radians([-15, 0, 15])))
    pel_rest = rest[INDEX["pelvis"]]
    hip_l, hip_nl = P.local("pelvis", hip + GAP * hip_n), pel_rest[:3, :3].T @ hip_n
    palm = {s: P.palm_local(s) for s in "lr"}

    def hand_frame(n_out, finger):
        Z = -unit(n_out)                       # palm faces the surface
        Y = unit(finger - (finger @ Z) * Z)
        return np.column_stack([np.cross(Y, Z), Y, Z])

    def arm_obj(side, bone, p_local, n_local, finger, elbow_dir, wrist_local=None):
        def contact(G):
            Gb = G[INDEX[bone]]
            return (pos(G, "hand_" + side, palm[side]) - (Gb[:3, :3] @ p_local + Gb[:3, 3])) * wp

        def orient(G):
            n = G[INDEX[bone]][:3, :3] @ n_local
            return rot_err(G, "hand_" + side, hand_frame(n, finger), w=1 / np.radians(6))

        def elbow(G):
            d = unit(pos(G, "lowerarm_" + side) - pos(G, "upperarm_" + side))
            return (d - unit(elbow_dir)) * ELBOW_W

        def wrist(G):
            Gb = G[INDEX[bone]]
            return (pos(G, "hand_" + side) - (Gb[:3, :3] @ wrist_local + Gb[:3, 3])) / 0.01
        return [contact, orient, elbow] + ([wrist] if wrist_local is not None else [])

    def no_penetration(side, obstacles):
        """Both directions: hand/finger vertices outside the obstacle shells, obstacle vertices outside the hand
        shells. Every involved shell is rigid on one bone, so each test runs in that bone's rest space."""
        hand_bones = [b for b in BONES if b.endswith("_" + side) and (b.startswith("hand") or b[:-2].split("_")[0] in
                      ("thumb", "index", "middle", "ring", "pinky"))]
        def rigid_set(bones):
            idx = np.where(np.isin(P.dom, bones))[0]
            return np.array([INDEX[b] for b in P.dom[idx]]), np.column_stack([m.pos[idx], np.ones(len(idx))])
        movers = [rigid_set(hand_bones), rigid_set(obstacles)]
        shells = [[(INDEX[b], m.pos[P.shell_of(b)]) for b in obstacles], [(INDEX[b], m.pos[P.shell_of(b)]) for b in hand_bones]]

        def f(G):
            S = G @ sk.inverse_bind
            out = []
            for (bidx, hom), targets in zip(movers, shells):
                pts = np.einsum("nij,nj->ni", S[bidx], hom)
                for bi, T in targets:
                    local = (np.linalg.inv(S[bi]) @ pts.T).T[:, :3]
                    lo, hi = T.reshape(-1, 3).min(0), T.reshape(-1, 3).max(0)
                    near = np.all((local > lo - 0.01) & (local < hi + 0.01), axis=1)
                    depth = np.zeros(len(local))
                    if near.any():
                        inside = np.abs(winding(local[near], T)) > 0.5
                        for k in np.where(near)[0][inside]:
                            depth[k] = point_tri_dist(local[k], T).min() + 0.001   # keep 1 mm clear
                    out.append(depth / 0.0005)
            return np.concatenate(out)
        return f

    arm_dofs = lambda s: [(f"{b}_{s}", a) for b in ("upperarm", "hand") for a in range(3)] + [(f"lowerarm_{s}", 0), (f"lowerarm_{s}", 1)] \
        + [(f"{f}_0{k}_{s}", 0) for f in ("index", "middle", "ring", "pinky") for k in (1, 2, 3)]
    obj_l = arm_obj("l", "head", crown_l, crown_nl, LEFT_FINGER_DIR, LEFT_ELBOW_DIR, np.array(LEFT_WRIST_HEAD_LOCAL))
    obj_r = arm_obj("r", "pelvis", hip_l, hip_nl, RIGHT_FINGER_DIR, RIGHT_ELBOW_DIR)
    pen_l, pen_r = no_penetration("l", ["head"]), no_penetration("r", ["pelvis", "spine_01"])
    # the raised arm has several local minima: solve from fixed starting guesses, keep the lowest cost
    best = None
    for ua, la in LEFT_ARM_STARTS:
        trial = {**{b: list(e) for b, e in euler.items()}, "upperarm_l": list(ua), "lowerarm_l": list(la), "hand_l": [0.0, 0.0, 0.0]}
        res = solve(P, trial, root, arm_dofs("l"), obj_l, limits, prefer)
        if best is None or res[2] < best[2]:
            best = res
    euler, root, _ = best
    euler, root, _ = solve(P, euler, root, arm_dofs("r"), obj_r, limits, prefer)
    # second pass: same targets plus 'hand stays outside the touched shell'
    euler, root, cost_l = solve(P, euler, root, arm_dofs("l"), obj_l + [pen_l], limits, prefer)
    euler, root, cost_r = solve(P, euler, root, arm_dofs("r"), obj_r + [pen_r], limits, prefer)
    arm_objs = obj_l[:3] + obj_r

    # --- ground: lowest support-foot vertex on y = 0
    pose = {"bones": {b: quat(e) for b, e in euler.items()}, "root_offset": root}
    V = sk.skin(pose, m.pos, m.joints, m.weights)
    feet_r = np.isin(P.dom, ["foot_r", "ball_r"])
    root[1] -= V[feet_r, 1].min()
    pose["root_offset"] = root
    V = sk.skin(pose, m.pos, m.joints, m.weights)
    G = sk.pose_globals(pose)
    diag = {
        "solver_cost": {"legs": round(cost_legs, 4), "left_arm": round(cost_l, 4), "right_arm": round(cost_r, 4)},
        "right_sole_min_y_m": round(float(V[feet_r, 1].min()), 5),
        "left_toes_min_y_m": round(float(V[np.isin(P.dom, ["ball_l"]), 1].min()), 5),
        "left_heel_height_m": round(float(V[(P.dom == "foot_l") & (m.pos[:, 2] < sk.heads["foot_l"][2] - 0.02), 1].min()), 4),
        "right_heel_height_m": round(float(V[(P.dom == "foot_r") & (m.pos[:, 2] < sk.heads["foot_r"][2] - 0.02), 1].min()), 4),
        "left_palm_to_crown_target_mm": round(float(np.linalg.norm(arm_objs[0](G)) / wp * 1e3), 2),
        "right_palm_to_hip_target_mm": round(float(np.linalg.norm(arm_objs[3](G)) / wp * 1e3), 2),
    }

    # --- write
    REF.parent.mkdir(parents=True, exist_ok=True)
    if REF_ORIGINAL.exists() and not REF.exists():
        shutil.copyfile(REF_ORIGINAL, REF)
    bones = {}
    for b in BONES:
        if b in euler and np.abs(euler[b]).max() > 1e-6:
            q = quat(euler[b])
            bones[b] = {"quaternion": [round(float(v), 7) for v in q],
                        "euler": {"order": "XYZ", "degrees": [round(float(v), 3) for v in euler[b]]}}
    doc = {
        "$schema": "./schema.json",
        "formatVersion": 1,
        "skeleton": SKELETON_ID,
        "meta": {
            "id": POSE_ID,
            "name": "Contrapposto, hand on head",
            "description": "Standing contrapposto. Weight on the straight right leg with the right hip raised; left leg "
                           "out to the side with a bent knee, on the ball of the foot with the heel lifted. Spine bends "
                           "back so the left shoulder is higher. Right hand rests on the right hip with the elbow out; "
                           "left hand is raised and rests on the crown. Head tilted to the right, chin up. "
                           "Left/right are the character's own.",
            "sourceImage": {"path": "poses/reference/pose_reference_01.png", "originalPath": str(REF_ORIGINAL),
                            "sha256": hashlib.sha256(REF.read_bytes()).hexdigest()},
            "targetModels": ["female", "male"],
            "assumptions": [
                "Single front view, so depth is assumed: both elbows ~5 cm behind their shoulder; right palm on the "
                "front-lateral hip (pelvis shell, ~20 deg in front of the side) with fingers towards the navel and the "
                "thumb opened back; left palm on the upper-left of the crown, fingers across to the right/front.",
                "Left leg reads as abducted, not drawn crossing inwards: knee and foot outside the hip line, ankles "
                "0.40 m apart, left knee bent ~44 deg, left foot ~5 cm forward and turned out 12 deg.",
                "Left heel raised (foot 28 deg beyond rest plantarflexion, heel ~9 cm off the floor) with the toes flat; "
                "right foot flat, right knee straight (~1 deg).",
                "Pelvis line tilts ~6 deg (right hip up) and turns slightly to its left; ~9 deg of spine lateral bend "
                "makes the shoulder line tilt ~9 deg the other way (left shoulder up); head rolls ~12 deg to the right "
                "and looks up ~19 deg.",
                "Left elbow ends near crown height (y 1.715 m on the female), higher than the eye-level elbow of the "
                "drawing: with this model's arm lengths a palm on the crown and a lateral elbow at eye level are not "
                "reachable together. The palm-down hand on the crown needs a nearly fully supinated left forearm "
                "(~85 deg), at the edge of the joint limit.",
                "Fitted on rig/female.glb (contacts and grounding solved there). The male uses the same rotations and "
                "the hips-height-relative root offset; his contact gaps are reported in rig/validation.",
            ],
            "generator": "rig/tools/author_pose_01.py",
        },
        "root": {"translation": [round(float(v), 6) for v in root / sk.hips_height], "unit": "hipsHeight"},
        "bones": bones,
    }
    out = ROOT / "poses" / f"{POSE_ID}.json"
    out.write_text(json.dumps(doc, indent=2) + "\n")
    (RIG / "validation" / f"author_{POSE_ID}.json").write_text(json.dumps(diag, indent=1))
    print(json.dumps(diag, indent=1))


if __name__ == "__main__":
    main()
