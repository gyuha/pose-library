"""Check pose files against rig/joint_limits.json.

    /tmp/pose-qa-venv/bin/python rig/tools/check_limits.py poses/*.json

For every bone in a pose: the quaternion must be unit length, the optional 'euler' must describe the same rotation,
and the quaternion decomposed as three.js Euler 'XYZ' must lie inside [min, max] on every axis (tolerance 0.05 deg).
Validates poses/schema.json when 'jsonschema' is importable. Also checks that the limits file covers the whole skeleton and that right limits mirror left limits.
Exit status 1 on any violation. Writes rig/validation/limits_<pose id>.json.
"""
import json
import sys
from pathlib import Path

import numpy as np

from rigcore import BONES, RIG, SKELETON_ID, euler_xyz_to_mat, mat_to_euler_xyz, mirror_name, quat_to_mat

TOL = 0.05


def check_limits_file(limits):
    errors = []
    if limits.get("skeleton") != SKELETON_ID:
        errors.append("skeleton id mismatch")
    j = limits["joints"]
    for b in BONES:
        if b not in j:
            errors.append(f"no limits for {b}")
    for b in j:
        if b not in BONES:
            errors.append(f"unknown bone {b}")
        if b.endswith("_l"):
            L, R = j[b], j[mirror_name(b)]
            ok = L["x"] == R["x"] and L["y"] == [-R["y"][1], -R["y"][0]] and L["z"] == [-R["z"][1], -R["z"][0]]
            if not ok:
                errors.append(f"{mirror_name(b)} does not mirror {b}")
    return errors


def schema_errors(d):
    """poses/schema.json validation when the 'jsonschema' package is importable (it is not in /tmp/pose-qa-venv;
    run this script with a python3 that has it, see rig/README.md)."""
    try:
        import jsonschema
    except ImportError:
        print("  schema: skipped (jsonschema not installed in this interpreter)")
        return []
    schema = json.loads((RIG.parent / "poses" / "schema.json").read_text())
    return [f"schema: {e.message} at {list(e.absolute_path)}" for e in jsonschema.Draft202012Validator(schema).iter_errors(d)]


def check_pose(path, limits):
    d = json.loads(Path(path).read_text())
    rows, errors = {}, schema_errors(d)
    if d.get("skeleton") != SKELETON_ID:
        errors.append(f"skeleton {d.get('skeleton')!r} != {SKELETON_ID!r}")
    for b, v in d.get("bones", {}).items():
        if b not in BONES:
            errors.append(f"unknown bone {b}")
            continue
        q = np.array(v["quaternion"], float)
        if abs(np.linalg.norm(q) - 1) > 1e-4:
            errors.append(f"{b}: quaternion not unit ({np.linalg.norm(q):.6f})")
        R = quat_to_mat(q / np.linalg.norm(q))
        e = mat_to_euler_xyz(R)
        if "euler" in v:
            Re = euler_xyz_to_mat(v["euler"]["degrees"])
            ang = np.degrees(np.arccos(np.clip((np.trace(Re.T @ R) - 1) / 2, -1, 1)))
            if v["euler"].get("order") != "XYZ" or ang > 0.05:
                errors.append(f"{b}: euler and quaternion disagree by {ang:.3f} deg")
        lim = limits["joints"][b]
        viol = {}
        for k, ax in enumerate("xyz"):
            lo, hi = lim[ax]
            if e[k] < lo - TOL or e[k] > hi + TOL:
                viol[ax] = round(float(e[k] - (lo if e[k] < lo else hi)), 2)
        margin = min(min(e[k] - lim[ax][0], lim[ax][1] - e[k]) for k, ax in enumerate("xyz"))
        rows[b] = {"euler_xyz_deg": np.round(e, 2).tolist(), "limits": [lim["x"], lim["y"], lim["z"]],
                   "min_margin_deg": round(float(margin), 2), **({"violation_deg": viol} if viol else {})}
        if viol:
            errors.append(f"{b}: outside limits {viol} (euler {np.round(e, 1).tolist()})")
    return rows, errors


def main(paths):
    limits = json.loads((RIG / "joint_limits.json").read_text())
    errors = check_limits_file(limits)
    for e in errors:
        print("LIMITS FILE:", e)
    status = 1 if errors else 0
    for p in paths:
        rows, errs = check_pose(p, limits)
        out = RIG / "validation" / f"limits_{Path(p).stem}.json"
        out.write_text(json.dumps({"pose": str(p), "passed": not errs, "errors": errs, "bones": rows}, indent=1))
        tight = sorted(rows.items(), key=lambda kv: kv[1]["min_margin_deg"])[:5]
        print(f"{p}: {'PASS' if not errs else 'FAIL'} ({len(rows)} bones); tightest margins:",
              ", ".join(f"{b} {r['min_margin_deg']}" for b, r in tight))
        for e in errs:
            print("  ", e)
        status |= bool(errs)
    sys.exit(status)


if __name__ == "__main__":
    main(sys.argv[1:])
