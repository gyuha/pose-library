"""Viewer-formula check: apply a pose straight from the glTF data, the way a three.js viewer does, and compare
with rigcore's skinning.

    /tmp/pose-qa-venv/bin/python rig/tools/check_gltf_pose.py poses/pose_01_contrapposto_hand_on_head.json

Independent of rigcore.Skeleton: reads node TRS, hierarchy, JOINTS_0/WEIGHTS_0 and the inverseBindMatrices
accessor from rig/<model>.glb, then per bone
    bone.quaternion = node.rotation * pose.quaternion          (three.js: restQ.clone().multiply(q))
    pelvis.position = node.translation + root.translation * pelvis rest height (= node.translation[1])
and skins with jointWorld * inverseBindMatrix. Prints the largest vertex difference to rigcore (metres).
"""
import json
import sys

import numpy as np

from rigcore import RIG, RigModel, accessor, load_pose, pose_for, quat_to_mat, read_glb


def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return np.array([aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
                     aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz])


def viewer_skin(path, pose_json):
    g, b = read_glb(path)
    nodes = g["nodes"]
    skin = g["skins"][0]
    ibm = accessor(g, b, skin["inverseBindMatrices"]).reshape(-1, 4, 4).transpose(0, 2, 1)
    parent = {c: i for i, n in enumerate(nodes) for c in n.get("children", [])}
    root = nodes[skin["skeleton"]]
    world = {}

    def W(i):
        if i not in world:
            n = nodes[i]
            q = np.array(n.get("rotation", [0, 0, 0, 1]), float)
            t = np.array(n.get("translation", [0, 0, 0]), float)
            if n["name"] in pose_json.get("bones", {}):
                q = qmul(q, pose_json["bones"][n["name"]]["quaternion"])
            if n is root:
                t = t + np.array(pose_json["root"]["translation"]) * root["translation"][1]
            L = np.eye(4)
            L[:3, :3] = quat_to_mat(q / np.linalg.norm(q))
            L[:3, 3] = t
            world[i] = W(parent[i]) @ L if i in parent else L
        return world[i]

    S = np.array([W(j) for j in skin["joints"]]) @ ibm
    at = g["meshes"][0]["primitives"][0]["attributes"]
    P = accessor(g, b, at["POSITION"]).astype(float)
    J = accessor(g, b, at["JOINTS_0"]).astype(int)
    Wt = accessor(g, b, at["WEIGHTS_0"]).astype(float)
    hom = np.column_stack([P, np.ones(len(P))])
    return sum(Wt[:, k:k + 1] * np.einsum("nij,nj->ni", S[J[:, k]], hom)[:, :3] for k in range(4))


def main(paths):
    status = 0
    for p in paths:
        d = json.loads(open(p).read())
        for name in ("female", "male"):
            m = RigModel(RIG / f"{name}.glb")
            ref = m.skeleton.skin(pose_for(m.skeleton, load_pose(p)), m.pos, m.joints, m.weights)
            err = float(np.abs(viewer_skin(RIG / f"{name}.glb", d) - ref).max())
            print(f"{p} {name}: max |viewer - rigcore| = {err:.2e} m")
            status |= err > 1e-5
    sys.exit(status)


if __name__ == "__main__":
    main(sys.argv[1:])
