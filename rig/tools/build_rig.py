"""Build rig/male.glb and rig/female.glb: skinned GLBs on the standard skeleton (rig/README.md).

Reads model/male.glb and model/female.glb (never writes model/). Deterministic, NumPy only:

    PYTHONDONTWRITEBYTECODE=1 /tmp/pose-qa-venv/bin/python rig/tools/build_rig.py

Steps per model:
 1. Joint heads. Male: source DEF-* bind positions (pelvis moved to x=0, L/R made exact mirrors).
    Female: every male head is carried through a local affine map fitted (robust, distance-weighted least
    squares) to the male->female correspondence of original vertices 0-4105 owned by the bone and its parent.
 2. Rest frames by the rules in rigcore.rest_frames; inverse bind matrices = inverse(global rest).
 3. Weights: source JOINTS_0/WEIGHTS_0 remapped DEF -> standard, made left/right symmetric (left side is the
    reference), then the chest/axilla adjustment (adjust_weights) for raised-arm poses.
"""
import json
import hashlib

import numpy as np

from rigcore import (BONES, DEF_NAME, INDEX, PARENT, ROOT, RIG, SKELETON_ID, GlbWriter, Skeleton, accessor,
                     mirror_name, read_glb, rest_frames, shell_components, strip_suffix)

MODEL = ROOT / "model"
N_ORIGINAL = 4106  # canonical vertices 0-4105 are the male source vertices (model/README.md)


# ---------------------------------------------------------------- source reading
def load_source(path):
    """Canonical vertex pool (shared accessors read once, as in tests/glb_io.Model) + per-material triangles."""
    g, b = read_glb(path)
    pools, base_of, tris = {}, {}, {0: [], 1: []}
    base = 0
    for m in g["meshes"]:
        for p in m["primitives"]:
            at = p["attributes"]
            key = at["POSITION"]
            if key not in base_of:
                base_of[key] = base
                d = {k: accessor(g, b, at[k]) for k in ("POSITION", "NORMAL", "TEXCOORD_0", "JOINTS_0", "WEIGHTS_0")}
                pools[key] = d
                base += len(d["POSITION"])
            tris[p.get("material", 0)].append(accessor(g, b, p["indices"]).reshape(-1, 3).astype(np.int64) + base_of[key])
    order = sorted(pools, key=lambda k: base_of[k])
    cat = lambda k: np.vstack([pools[o][k] for o in order])
    return {"gltf": g, "pos": cat("POSITION").astype(float), "nrm": cat("NORMAL").astype(float),
            "uv": cat("TEXCOORD_0").astype(float), "joints": cat("JOINTS_0").astype(int),
            "weights": cat("WEIGHTS_0").astype(float), "tris": {k: np.vstack(v) for k, v in tris.items()}}


def source_bind(g):
    """Global bind matrices of the source joints (node hierarchy), keyed by DEF name without suffix."""
    from rigcore import quat_to_mat
    par = {c: i for i, n in enumerate(g["nodes"]) for c in n.get("children", [])}
    memo = {}

    def world(i):
        if i not in memo:
            n = g["nodes"][i]
            L = np.eye(4)
            L[:3, :3] = quat_to_mat(n.get("rotation", [0, 0, 0, 1])) * np.array(n.get("scale", [1, 1, 1]))
            L[:3, 3] = n.get("translation", [0, 0, 0])
            memo[i] = world(par[i]) @ L if i in par else L
        return memo[i]

    joints = g["skins"][0]["joints"]
    names = [strip_suffix(g["nodes"][j]["name"]) for j in joints]
    return names, {n: world(j) for n, j in zip(names, joints)}


def symmetrize_heads(heads):
    out = {}
    for b, p in heads.items():
        if b[-2:] not in ("_l", "_r"):
            out[b] = np.array([0.0, p[1], p[2]])
        else:
            m = heads[mirror_name(b)] * [-1, 1, 1]
            out[b] = (p + m) / 2
    return out


# ---------------------------------------------------------------- female skeleton fit
def fit_affine(src, dst, w):
    A = np.column_stack([src, np.ones(len(src))]) * np.sqrt(w)[:, None]
    X, *_ = np.linalg.lstsq(A, dst * np.sqrt(w)[:, None], rcond=None)
    return X  # 4x3: dst = [src 1] @ X


def female_heads(male_heads, male_leaf, male_src, female_src, male_owner):
    """Carry male joint heads into the female through local robust affine fits (see module docstring)."""
    Pm, Pf = male_src["pos"][:N_ORIGINAL], female_src["pos"][:N_ORIGINAL]
    heads, leaf, report = {}, {}, {}
    for b in BONES:
        own = {b} | ({PARENT[b]} if PARENT[b] else set())
        sel = np.isin(male_owner[:N_ORIGINAL], list(own))
        sigma = 0.015 if ("_0" in b) else 0.03 if b.startswith("hand") else 0.06
        d = np.linalg.norm(Pm[sel] - male_heads[b], axis=1)
        w = np.exp(-(d / sigma) ** 2) + 1e-6
        src, dst = Pm[sel], Pf[sel]
        for _ in range(4):  # IRLS: down-weight vertices the chest refinement moved off the smooth morph
            X = fit_affine(src, dst, w)
            r = np.linalg.norm(np.column_stack([src, np.ones(len(src))]) @ X - dst, axis=1)
            w = np.exp(-(d / sigma) ** 2) * (1 / (1 + (r / 0.002) ** 2)) + 1e-6
        heads[b] = np.append(male_heads[b], 1) @ X
        if b in male_leaf:
            leaf[b] = male_leaf[b] @ X[:3]
        report[b] = {"effective_vertices": round(float(w.sum() ** 2 / (w ** 2).sum()), 1),
                     "weighted_rms_residual_mm": round(float(np.sqrt((w * r ** 2).sum() / w.sum())) * 1e3, 3)}
    return heads, leaf, report


# ---------------------------------------------------------------- weights
def remap_weights(src, src_names):
    """Source joint indices -> standard indices; at most 4 influences; sums renormalised."""
    lut = np.array([INDEX[next(b for b in BONES if DEF_NAME[b] == n)] if n.startswith("DEF-") else -1 for n in src_names])
    J = lut[src["joints"]]
    W = src["weights"].copy()
    assert not (W[J < 0] > 0).any(), "weights on non-deforming source joints"
    J[J < 0] = 0
    return J, W / W.sum(1, keepdims=True)


def dense(J, W):
    D = np.zeros((len(J), len(BONES)))
    for k in range(J.shape[1]):
        np.add.at(D, (np.arange(len(J)), J[:, k]), W[:, k])
    return D


def mirror_map(pos, nrm):
    """For each vertex, the vertex at the mirrored position with the mirrored normal (-1 if none within 0.1 mm)."""
    key = np.round(pos / 1e-4).astype(np.int64)
    mpos = pos * [-1, 1, 1]
    out = np.full(len(pos), -1)
    lookup = {}
    for i, k in enumerate(map(tuple, key)):
        lookup.setdefault(k, []).append(i)
    for i in range(len(pos)):
        k0 = np.round(mpos[i] / 1e-4).astype(np.int64)
        best, bd = -1, 1e9
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for j in lookup.get((k0[0] + dx, k0[1] + dy, k0[2] + dz), []):
                        dp = np.linalg.norm(pos[j] - mpos[i])
                        dn = np.linalg.norm(nrm[j] - nrm[i] * [-1, 1, 1])
                        if dp < 1e-4 and dp + 1e-3 * dn < bd:
                            best, bd = j, dp + 1e-3 * dn
        out[i] = best
    return out


def symmetrize_weights(D, pos, mirror):
    """Right-side (x < 0) vertices take the mirrored weights of their left partner."""
    perm = np.array([INDEX[mirror_name(b)] for b in BONES])
    out = D.copy()
    right = (pos[:, 0] < -1e-5) & (mirror >= 0)
    out[right] = D[mirror[right]][:, perm]
    changed = np.abs(out - D).max(1) > 1e-4
    return out, int(changed.sum()), int(((pos[:, 0] < -1e-5) & (mirror < 0)).sum())


PECTORAL_MAX = 0.30      # clavicle share at the axilla edge of the chest shell
PECTORAL_R = (0.06, 0.16)  # full share inside R0, none beyond R1 (m from the shoulder joint on the male; scaled by pelvis height)


def adjust_weights(D, src, skel):
    """Raised-arm fixes (measured with check_deformation.py).

    1. Shoulder filler shells (Joints material) that are split between clavicle_* (medial half) and
       upperarm_* (lateral half) stretch up to 5.5x when the arm is raised. They are made rigid on upperarm_*,
       so they turn with the arm and keep covering the open top of the upper-arm shell.
    2. Chest shell (majority spine_03): a smooth clavicle_* share (max PECTORAL_MAX) near the shoulder joint,
       like the pectoral/axillary tail following the shoulder girdle. Clavicle rotations are small, so this
       lifts the upper-lateral chest without the blend collapse a large upper-arm share would cause.
    """
    D = D.copy()
    comp_v, _ = shell_components(src["pos"], np.vstack([src["tris"][0], src["tris"][1]]))
    dom = D.argmax(1)
    scale = skel.hips_height / 0.936917836708306   # radii are tuned on the male; scaled to the model
    info = {"shoulder_filler_vertices_made_rigid": 0, "pectoral_vertices": 0, "pectoral_max_share": 0.0}
    for s in "lr":
        cl, ua = INDEX["clavicle_" + s], INDEX["upperarm_" + s]
        for c in np.unique(comp_v[(D[:, cl] > 0) & (D[:, ua] > 0)]):
            sel = comp_v == c
            D[sel] = 0
            D[sel, ua] = 1
            info["shoulder_filler_vertices_made_rigid"] += int(sel.sum())
    chest = np.bincount(comp_v[dom == INDEX["spine_03"]]).argmax()
    for s, sign in (("l", 1), ("r", -1)):
        sel = (comp_v == chest) & (np.sign(src["pos"][:, 0]) == sign)
        d = np.linalg.norm(src["pos"][sel] - skel.heads["upperarm_" + s], axis=1) / scale
        t = np.clip((PECTORAL_R[1] - d) / (PECTORAL_R[1] - PECTORAL_R[0]), 0, 1)
        share = PECTORAL_MAX * t * t * (3 - 2 * t)
        rows = np.where(sel)[0]
        D[rows] *= (1 - share)[:, None]
        D[rows, INDEX["clavicle_" + s]] += share
        info["pectoral_vertices"] += int((share > 1e-3).sum())
        info["pectoral_max_share"] = round(float(max(info["pectoral_max_share"], share.max())), 4)
    return D, info


def to_top4(D):
    J = np.argsort(-D, axis=1, kind="stable")[:, :4]
    W = np.take_along_axis(D, J, 1)
    W[W < 1e-4] = 0
    W = W / W.sum(1, keepdims=True)
    J[W == 0] = 0
    return J, W


# ---------------------------------------------------------------- writing
def write_rig(name, src, skel, J, W, extras):
    w = GlbWriter()
    g = w.gltf
    sg = src["gltf"]
    g["asset"] = {"version": "2.0", "generator": "rig/tools/build_rig.py (pose-library)",
                  "extras": {**sg["asset"].get("extras", {}), "rig": extras}}
    g["materials"] = sg["materials"]
    nodes = []
    for b in BONES:
        n = {"name": b, "translation": [float(v) for v in skel.local_t[b]], "rotation": [float(v) for v in skel.local_q[b]]}
        kids = [INDEX[c] for c in BONES if PARENT[c] == b]
        if kids:
            n["children"] = kids
        nodes.append(n)
    nodes.append({"name": f"{name}_mesh", "mesh": 0, "skin": 0})
    g["nodes"] = nodes
    g["scenes"] = [{"name": name, "nodes": [INDEX["pelvis"], len(BONES)]}]
    g["scene"] = 0
    pos32 = src["pos"].astype(np.float32)
    attrs = {"POSITION": w.add(pos32, "VEC3", 5126, 34962, minmax=True),
             "NORMAL": w.add(src["nrm"], "VEC3", 5126, 34962),
             "TEXCOORD_0": w.add(src["uv"], "VEC2", 5126, 34962),
             "JOINTS_0": w.add(J, "VEC4", 5121, 34962),
             "WEIGHTS_0": w.add(W, "VEC4", 5126, 34962)}
    prims = [{"attributes": attrs, "indices": w.add(src["tris"][m].reshape(-1), "SCALAR", 5125, 34963), "material": m, "mode": 4}
             for m in (0, 1)]
    g["meshes"] = [{"name": f"{name}_mesh", "primitives": prims}]
    ibm = np.ascontiguousarray(skel.inverse_bind.transpose(0, 2, 1)).reshape(len(BONES), 16)
    g["skins"] = [{"name": SKELETON_ID, "joints": list(range(len(BONES))), "skeleton": INDEX["pelvis"],
                   "inverseBindMatrices": w.add(ibm, "MAT4", 5126)}]
    data = w.bytes()
    (RIG / f"{name}.glb").write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def main():
    male_src = load_source(MODEL / "male.glb")
    female_src = load_source(MODEL / "female.glb")
    names, bind = source_bind(male_src["gltf"])
    heads_m = symmetrize_heads({b: bind[DEF_NAME[b]][:3, 3] for b in BONES})
    leaf_m = {b: bind[DEF_NAME[b]][:3, 1] for b in BONES if b.startswith("ball_") or b.endswith(("_03_l", "_03_r"))}
    leaf_m = {b: (v if b[-2:] == "_l" else leaf_m[mirror_name(b)] * [-1, 1, 1]) for b, v in leaf_m.items()}
    leaf_m["head"] = np.array([0.0, 1, 0])

    Jm, Wm = remap_weights(male_src, names)
    owner = np.array(BONES)[Jm[np.arange(len(Jm)), Wm.argmax(1)]]
    heads_f, leaf_f, fit_report = female_heads(heads_m, leaf_m, male_src, female_src, owner)
    heads_f = symmetrize_heads(heads_f)
    leaf_f = {b: (v if b[-2:] != "_r" else leaf_f[mirror_name(b)] * [-1, 1, 1]) for b, v in leaf_f.items()}
    leaf_f["head"] = np.array([0.0, 1, 0])

    report = {"skeleton": SKELETON_ID, "bones": len(BONES), "female_joint_fit": fit_report, "models": {}}
    for name, src, heads, leaf in (("male", male_src, heads_m, leaf_m), ("female", female_src, heads_f, leaf_f)):
        skel = Skeleton(heads, rest_frames(heads, leaf))
        J, W = remap_weights(src, names)
        D = dense(J, W)
        mirror = mirror_map(src["pos"], src["nrm"])
        D, n_sym, n_unpaired = symmetrize_weights(D, src["pos"], mirror)
        D, adj = adjust_weights(D, src, skel)
        J, W = to_top4(D)
        extras = {"skeleton": SKELETON_ID, "source": f"model/{name}.glb", "builder": "rig/tools/build_rig.py",
                  "hipsHeight": skel.hips_height}
        sha = write_rig(name, src, skel, J, W, extras)
        report["models"][name] = {
            "sha256": sha, "vertices": len(src["pos"]), "triangles": int(sum(len(t) for t in src["tris"].values())),
            "height_m": float(np.ptp(src["pos"][:, 1])), "hips_height_m": skel.hips_height,
            "weights": {"symmetrized_vertices": n_sym, "right_vertices_without_mirror_partner": n_unpaired,
                        "max_influences": int((W > 0).sum(1).max()), "adjustment": adj},
            "joint_heads": {b: np.round(heads[b], 5).tolist() for b in BONES}}
    (RIG / "validation").mkdir(exist_ok=True)
    (RIG / "validation" / "build_report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps({k: v for k, v in report.items() if k != "models"} | {
        m: {k: v for k, v in r.items() if k != "joint_heads"} for m, r in report["models"].items()}, indent=1))


if __name__ == "__main__":
    main()
