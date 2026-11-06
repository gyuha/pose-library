"""Headless preview renderer for a rigged model in a pose (NumPy z-buffer rasterizer + Pillow PNG).

    /tmp/pose-qa-venv/bin/python rig/tools/render_pose.py poses/pose_01_contrapposto_hand_on_head.json [--models female male]

Writes rig/previews/<pose id>_<model>_<view>.png and <pose id>_<model>_compare.png (reference image | front | ref view).
Flat shading by face normal; dark lines where the visible body part changes or depth jumps (line-art look).
Without a pose argument the rest pose is rendered (id 'rest').
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from rigcore import RIG, ROOT, RigModel, load_pose, pose_for, shell_components

W, H = 600, 800
FEMALE_HIPS = 0.8666490058194041
# name: (camera position, look-at target, vertical field of view in degrees). Model space, +Z = character's front.
VIEWS = {
    "front": ((0.0, 0.95, 6.0), (0.0, 0.88, 0.0), 18.0),
    "ref": ((0.35, 0.95, 3.6), (0.03, 0.88, 0.0), 29.0),   # close to the reference drawing: near-frontal, slight yaw, low camera
    "three_quarter": ((2.6, 1.2, 3.6), (0.0, 0.88, 0.0), 26.0),
    "side": ((6.0, 0.95, 0.0), (0.0, 0.88, 0.0), 18.0),
}


def part_ids(model):
    """Line-art region id per triangle: connected mesh shell (each shell is one mannequin piece)."""
    return shell_components(model.pos, model.tri)[1]


def look_at(eye, target):
    eye, target = np.asarray(eye, float), np.asarray(target, float)
    f = target - eye
    f /= np.linalg.norm(f)
    r = np.cross(f, [0, 1, 0])
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    return np.array([r, u, -f]), eye


def camera(view, scale):
    """View preset scaled to the model (presets are framed for the female, pelvis height 0.8666 m)."""
    eye, target, fov = VIEWS[view]
    return np.asarray(eye) * scale, np.asarray(target) * scale, fov


def render(verts, tri, tri_mat, parts, view, scale=1.0):
    eye, target, fov = camera(view, scale)
    R, e = look_at(eye, target)
    v = (verts - e) @ R.T                       # camera space, looking down -Z
    f = 0.5 * H / np.tan(np.radians(fov) / 2)
    sx = W / 2 + f * v[:, 0] / -v[:, 2]
    sy = H / 2 - f * v[:, 1] / -v[:, 2]
    inv_z = 1.0 / -v[:, 2]
    img = np.full((H, W, 3), 250, np.float64)
    depth = np.zeros((H, W))                    # stores 1/z (bigger = nearer)
    pid = np.full((H, W), -1)
    light = np.array([-0.35, 0.55, 0.75])
    light /= np.linalg.norm(light)
    n = np.cross(verts[tri[:, 1]] - verts[tri[:, 0]], verts[tri[:, 2]] - verts[tri[:, 0]])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-15)
    to_cam = eye - verts[tri].mean(1)
    facing = np.sign(np.sum(n * to_cam, axis=1))
    n *= facing[:, None]                        # double-sided materials
    world_light = light @ R                     # light fixed relative to the camera
    shade = 0.45 + 0.55 * np.clip(n @ world_light, 0, 1)
    base = np.where(tri_mat[:, None] == 0, [[205, 200, 195]], [[95, 100, 108]])
    for t in range(len(tri)):
        a, b, c = tri[t]
        xs, ys = sx[[a, b, c]], sy[[a, b, c]]
        x0, x1 = max(int(np.floor(xs.min())), 0), min(int(np.ceil(xs.max())), W - 1)
        y0, y1 = max(int(np.floor(ys.min())), 0), min(int(np.ceil(ys.max())), H - 1)
        if x0 > x1 or y0 > y1:
            continue
        den = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
        if abs(den) < 1e-12:
            continue
        X, Y = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        l0 = ((ys[1] - ys[2]) * (X - xs[2]) + (xs[2] - xs[1]) * (Y - ys[2])) / den
        l1 = ((ys[2] - ys[0]) * (X - xs[2]) + (xs[0] - xs[2]) * (Y - ys[2])) / den
        l2 = 1 - l0 - l1
        z = l0 * inv_z[a] + l1 * inv_z[b] + l2 * inv_z[c]
        sl = np.s_[y0:y1 + 1, x0:x1 + 1]
        m = (l0 >= -1e-9) & (l1 >= -1e-9) & (l2 >= -1e-9) & (z > depth[sl])
        depth[sl][m] = z[m]
        pid[sl][m] = parts[t]
        img[sl][m] = base[t] * shade[t]
    # line art: part boundaries, silhouettes, depth discontinuities
    edge = np.zeros((H, W), bool)
    for dy, dx in ((0, 1), (1, 0)):
        a, b = pid[: H - dy, : W - dx], pid[dy:, dx:]
        za, zb = depth[: H - dy, : W - dx], depth[dy:, dx:]
        jump = np.abs(1 / np.maximum(za, 1e-9) - 1 / np.maximum(zb, 1e-9)) > 0.04
        e = (a != b) | ((a >= 0) & (b >= 0) & jump)
        edge[: H - dy, : W - dx] |= e
        edge[dy:, dx:] |= e
    img[edge] = [30, 30, 30]
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))


def floor_line(img, view, scale=1.0):
    """Thin line on the floor plane y = 0 through the origin (visual grounding cue)."""
    eye, target, fov = camera(view, scale)
    R, e = look_at(eye, target)
    pts = (np.array([[-0.6, 0, 0.0], [0.6, 0, 0.0]]) - e) @ R.T
    f = 0.5 * H / np.tan(np.radians(fov) / 2)
    xy = [(W / 2 + f * p[0] / -p[2], H / 2 - f * p[1] / -p[2]) for p in pts]
    ImageDraw.Draw(img).line(xy, fill=(150, 170, 220), width=1)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pose", nargs="?")
    ap.add_argument("--models", nargs="+", default=["female"])
    ap.add_argument("--views", nargs="+", default=["front", "ref", "three_quarter", "side"])
    a = ap.parse_args()
    pose = load_pose(a.pose) if a.pose else {"bones": {}, "root_offset_ratio": np.zeros(3), "raw": {"meta": {}}}
    pose_id = Path(a.pose).stem if a.pose else "rest"
    ref = pose["raw"].get("meta", {}).get("sourceImage")
    out = RIG / "previews"
    out.mkdir(exist_ok=True)
    for name in a.models:
        m = RigModel(RIG / f"{name}.glb")
        verts = m.skeleton.skin(pose_for(m.skeleton, pose), m.pos, m.joints, m.weights)
        parts = part_ids(m)
        imgs = {}
        for view in a.views:
            scale = m.skeleton.hips_height / FEMALE_HIPS
            imgs[view] = floor_line(render(verts, m.tri, m.tri_mat, parts, view, scale), view, scale)
            imgs[view].save(out / f"{pose_id}_{name}_{view}.png")
        if ref and "front" in imgs and "ref" in imgs:
            r = Image.open(ROOT / ref["path"]).convert("RGB")
            r = r.resize((int(r.width * H / r.height), H))
            comp = Image.new("RGB", (r.width + 2 * W, H), "white")
            comp.paste(r, (0, 0))
            comp.paste(imgs["front"], (r.width, 0))
            comp.paste(imgs["ref"], (r.width + W, 0))
            comp.save(out / f"{pose_id}_{name}_compare.png")
        print(name, pose_id, "lowest y", round(float(verts[:, 1].min()), 4))


if __name__ == "__main__":
    main()
