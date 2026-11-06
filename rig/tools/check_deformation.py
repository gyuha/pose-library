"""Raised-arm deformation check: source weights vs the adjusted rig weights.

    /tmp/pose-qa-venv/bin/python rig/tools/check_deformation.py [poses/*.json ...]

Stress pose 'arms_overhead' (clavicle elevation 25 deg, upper-arm abduction 115 deg -> arms near vertical) plus any
pose files given. For each model and weight set: edge-length ratio (posed / rest) per mesh shell, reported for the
shells that change (> 2 %), the chest shell and the shoulder filler. Rigid shells keep ratio 1.
Writes rig/validation/deformation_check.json and rig/previews/arms_overhead_<model>_<weights>.png.
"""
import json
import sys
from pathlib import Path

import numpy as np

from build_rig import MODEL, dense, load_source, mirror_map, remap_weights, source_bind, symmetrize_weights, to_top4
from rigcore import BONES, INDEX, RIG, RigModel, euler_xyz_to_mat, load_pose, mat_to_quat, pose_for, read_glb, shell_components
from render_pose import render


def q(deg):
    return mat_to_quat(euler_xyz_to_mat(deg))


ARMS_OVERHEAD = {"bones": {"clavicle_l": q([0, 0, 25]), "upperarm_l": q([0, 0, 115]),
                           "clavicle_r": q([0, 0, -25]), "upperarm_r": q([0, 0, -115])}, "root_offset": [0, 0, 0]}


def source_weights(name, model):
    """Source weights on the standard skeleton (remapped + symmetrized, no adjustment)."""
    src = load_source(MODEL / f"{name}.glb")
    names, _ = source_bind(read_glb(MODEL / "male.glb")[0])
    J, W = remap_weights(src, names)
    D, *_ = symmetrize_weights(dense(J, W), src["pos"], mirror_map(src["pos"], src["nrm"]))
    return to_top4(D)


def shell_stats(model, V, comp_t):
    E = np.vstack([model.tri[:, [0, 1]], model.tri[:, [1, 2]], model.tri[:, [2, 0]]])
    et = np.concatenate([comp_t] * 3)
    rest = np.linalg.norm(model.pos[E[:, 0]] - model.pos[E[:, 1]], axis=1)
    ok = rest > 1e-6
    r = np.linalg.norm(V[E[:, 0]] - V[E[:, 1]], axis=1)[ok] / rest[ok]
    et = et[ok]
    dom = model.dominant_bone()
    out = {}
    for k in np.unique(et):
        rk = r[et == k]
        if np.abs(rk - 1).max() > 0.02:
            verts = np.unique(model.tri[comp_t == k])
            names, counts = np.unique(dom[verts], return_counts=True)
            label = "+".join(names[np.argsort(-counts)][:2])
            out[f"shell{k}:{label}"] = {"edge_ratio_min": round(float(rk.min()), 3), "edge_ratio_max": round(float(rk.max()), 3),
                                         "edges_over_1.2x": int((rk > 1.2).sum()), "edges_under_0.8x": int((rk < 0.8).sum())}
    return out


def main(pose_paths):
    poses = {"arms_overhead": lambda skel: ARMS_OVERHEAD}
    for p in pose_paths:
        pp = load_pose(p)
        poses[Path(p).stem] = lambda skel, pp=pp: pose_for(skel, pp)
    report = {}
    for name in ("female", "male"):
        m = RigModel(RIG / f"{name}.glb")
        _, comp_t = shell_components(m.pos, m.tri)
        weight_sets = {"source": source_weights(name, m), "rig": (m.joints, m.weights)}
        report[name] = {}
        for pname, make in poses.items():
            pose = make(m.skeleton)
            report[name][pname] = {}
            for wname, (J, W) in weight_sets.items():
                V = m.skeleton.skin(pose, m.pos, J, W)
                report[name][pname][wname] = shell_stats(m, V, comp_t)
                if pname == "arms_overhead":
                    img = render(V, m.tri, m.tri_mat, comp_t, "three_quarter")
                    img.save(RIG / "previews" / f"arms_overhead_{name}_{wname}_weights.png")
    out = RIG / "validation" / "deformation_check.json"
    out.write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
