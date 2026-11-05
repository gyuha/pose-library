"""QA 근거 이미지 렌더러 (OpenGL/Blender 불필요, numpy+PIL+matplotlib). 출력: tests/artifacts/*.png
사용: python scripts/render_qa.py
- 면 음영은 저장된 NORMAL 이 아니라 '실제 기하 면 법선'으로 계산한다 (저장 NORMAL 이 어긋난 곳을 숨기지 않기 위해).
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from qa_metrics import (SCALE, girth_profile, intersection_sets, label_of_welded, models, parts, proportions,
                        torso_measures, umbrella_delta, welded_edges, chest_groove)

OUT = Path(__file__).resolve().parents[1] / "tests" / "artifacts"
OUT.mkdir(parents=True, exist_ok=True)
LIGHT = np.array([-0.35, 0.6, 0.72]); LIGHT /= np.linalg.norm(LIGHT)


def rot(P, deg):
    a = np.radians(deg)
    return np.c_[P[:, 0] * np.cos(a) + P[:, 2] * np.sin(a), P[:, 1], -P[:, 0] * np.sin(a) + P[:, 2] * np.cos(a)]


def render(model, deg, box, ppm, vcolor=None, tcolor=None, base=(190, 186, 182), scale=1.0, flat=True):
    """box=(x0,x1,y0,y1)[m] (회전 후 화면 좌표). vcolor: (n,3) 정점색, tcolor: {tri_index: (r,g,b)}."""
    x0, x1, y0, y1 = box
    W, H = int((x1 - x0) * ppm), int((y1 - y0) * ppm)
    img = np.full((H, W, 3), 238.0); depth = np.full((H, W), -1e9)
    P = rot(model.pos * scale, deg)
    S = np.c_[(P[:, 0] - x0) * ppm, (y1 - P[:, 1]) * ppm, P[:, 2]]
    cam = np.array([np.sin(np.radians(deg)) * 0 + 0, 0, 1.0])
    for ti, t in enumerate(model.tri):
        tri = S[t]
        lo = np.maximum(np.floor(tri[:, :2].min(0)).astype(int), 0); hi = np.minimum(np.ceil(tri[:, :2].max(0)).astype(int), [W - 1, H - 1])
        if np.any(hi < lo):
            continue
        (xa, ya), (xb, yb), (xc, yc) = tri[:, :2]
        den = (yb - yc) * (xa - xc) + (xc - xb) * (ya - yc)
        if abs(den) < 1e-9:
            continue
        X, Y = np.meshgrid(np.arange(lo[0], hi[0] + 1) + .5, np.arange(lo[1], hi[1] + 1) + .5)
        u = ((yb - yc) * (X - xc) + (xc - xb) * (Y - yc)) / den; v = ((yc - ya) * (X - xc) + (xa - xc) * (Y - yc)) / den; w = 1 - u - v
        z = u * tri[0, 2] + v * tri[1, 2] + w * tri[2, 2]
        sl = np.s_[lo[1]:hi[1] + 1, lo[0]:hi[0] + 1]
        mask = (u >= 0) & (v >= 0) & (w >= 0) & (z > depth[sl])
        n = np.cross(P[t[1]] - P[t[0]], P[t[2]] - P[t[0]]); n /= max(np.linalg.norm(n), 1e-12)
        if n[2] < 0:
            n = -n
        shade = 0.40 + 0.60 * max(0.0, float(n @ LIGHT))
        if tcolor and ti in tcolor:
            col = np.broadcast_to(np.array(tcolor[ti], float) * (0.75 + 0.25 * shade), (*mask.shape, 3))
        elif vcolor is not None:
            col = (u[..., None] * vcolor[t[0]] + v[..., None] * vcolor[t[1]] + w[..., None] * vcolor[t[2]]) * shade
        else:
            col = np.broadcast_to(np.array(base, float) * shade, (*mask.shape, 3))
        img[sl][mask] = np.clip(col, 0, 255)[mask]; depth[sl][mask] = z[mask]
    return Image.fromarray(img.astype(np.uint8))


def label(im, text):
    d = ImageDraw.Draw(im); d.rectangle([0, 0, im.width, 16], fill=(255, 255, 255)); d.text((4, 2), text, fill=(0, 0, 0)); return im


def side_by_side(ims, path):
    W = sum(i.width for i in ims) + 6 * (len(ims) - 1); H = max(i.height for i in ims)
    out = Image.new("RGB", (W, H), (255, 255, 255)); x = 0
    for i in ims:
        out.paste(i, (x, 0)); x += i.width + 6
    out.save(path); print("saved", path.name)


def diverging(v, rng):
    """-rng(파랑) .. 0(회색) .. +rng(빨강)"""
    t = np.clip(v / rng, -1, 1)[:, None]
    pos = np.array([225, 60, 50]); neg = np.array([50, 90, 225]); mid = np.array([200, 200, 200])
    return np.where(t >= 0, mid + t * (pos - mid), mid + (-t) * (neg - mid))


def main():
    m, f = models(); L = parts(); inv, _ = welded_edges()
    # ---------------------------------------------------------------- 1) 가슴: 돌출/함몰 히트맵 + male 비교
    dn, _, _ = umbrella_delta()
    vcol = diverging(dn[inv], 0.03)
    box = (-0.28, 0.28, 1.0, 1.52)
    ims = [label(render(m, 0, box, 700, scale=SCALE), "male x0.925 (reference), front"),
           label(render(f, 0, box, 700), "female front (flat shading from geometry)"),
           label(render(f, 0, box, 700, vcolor=vcol), "female: red=bump, blue=dent (umbrella delta, +-30mm)")]
    side_by_side(ims, OUT / "01_chest_front_heatmap.png")
    box = (-0.30, 0.30, 1.0, 1.52)
    ims = [label(render(m, 90, box, 700, scale=SCALE), "male x0.925, side (+Z -> right)"),
           label(render(f, 90, box, 700), "female side"),
           label(render(f, 35, (-0.30, 0.30, 1.0, 1.52), 700), "female 3/4 view (35 deg)")]
    side_by_side(ims, OUT / "02_chest_side_and_three_quarter.png")

    # ---------------------------------------------------------------- 2) 교차: 신규 교차 삼각형 강조
    a, b = intersection_sets(); new = b - a
    tc = {}
    for i, j in new:
        for t in (i, j):
            tc[t] = (235, 40, 40)
    for deg, name, box in ((0, "front", (-0.35, 0.35, 0.7, 1.7)), (180, "back", (-0.35, 0.35, 0.7, 1.7)), (90, "side", (-0.3, 0.3, 0.7, 1.7))):
        ims = [label(render(f, deg, box, 520), f"female {name} plain"), label(render(f, deg, box, 520, tcolor=tc), f"female {name}: red = new intersections")]
        side_by_side(ims, OUT / f"03_new_intersections_{name}.png")
    # 허리/골반 확대 (파트색: Body=회색, Joints=남색)
    joint_col = np.array([[60, 80, 140] if l.startswith("joint:") else [190, 186, 182] for l in L], float)
    box = (-0.22, 0.22, 0.78, 1.22)
    ims = [label(render(m, 0, box, 900, vcolor=joint_col, scale=SCALE), "male x0.925: waist/pelvis (navy = Joints)"),
           label(render(f, 0, box, 900, vcolor=joint_col), "female: waist/pelvis (navy = Joints)"),
           label(render(f, 0, box, 900, tcolor=tc), "female: red = new intersections")]
    side_by_side(ims, OUT / "04_waist_pelvis_closeup.png")

    # ---------------------------------------------------------------- 3) 실루엣 비교 + 기준 폭 (정면)
    Hm, Hf = m.pos[:, 1].max(), f.pos[:, 1].max()
    box = (-0.75, 0.75, 0.0, 1.95)
    a_img = np.array(render(m, 0, box, 380, scale=SCALE, base=(120, 150, 220)))
    b_img = np.array(render(f, 0, box, 380, base=(230, 140, 90)))
    bgm = (a_img.sum(2) < 3 * 236); bgf = (b_img.sum(2) < 3 * 236)
    out = np.full(a_img.shape, 255, np.uint8)
    out[bgm] = (140, 170, 235); out[bgf] = (240, 160, 100); out[bgm & bgf] = (170, 150, 150)
    im = Image.fromarray(out); d = ImageDraw.Draw(im)
    pf = proportions(f); Hh = pf["H"]
    ppm = 380
    for frac, wfrac, name in ((0.818, 0.259, "Winter shoulder 0.259H"), (0.53, 0.191, "Winter hip 0.191H")):
        y = (1.95 - frac * Hh) * ppm; half = wfrac * Hh / 2 * ppm; cx = 0.75 * ppm
        d.line([(cx - half, y), (cx + half, y)], fill=(0, 140, 0), width=3); d.text((cx + half + 4, y - 6), name, fill=(0, 110, 0))
    # 머리 단위 눈금 (7.5 head 기준)
    head = Hh / 7.7
    for k in range(0, 9):
        y = (1.95 - k * head) * ppm; d.line([(5, y), (25, y)], fill=(80, 80, 80)); d.text((28, y - 6), f"{k}", fill=(80, 80, 80))
    d.text((60, 4), "blue=male x0.925  orange=female  grey=overlap", fill=(0, 0, 0))
    d.text((60, 18), "green=Winter Fig4.1 ref widths; ruler=head units (H/7.7)", fill=(0, 0, 0))
    im.save(OUT / "05_silhouette_female_vs_male.png"); print("saved 05")

    # ---------------------------------------------------------------- 4) 둘레/폭 프로파일 그래프
    ys = np.linspace(0.40, 0.80, 161)
    gm = girth_profile(m, ys * pf["H"] * 0 + ys * m.pos[:, 1].max()); gf = girth_profile(f, ys * Hf)
    fig, ax = plt.subplots(1, 3, figsize=(13, 4.5), sharey=True)
    for k, (t, un) in enumerate((("girth (convex hull perimeter) / H", 1), ("width x / H", 1), ("depth z / H", 1))):
        ax[k].plot(gm[:, k] / Hm, ys, label="male", color="tab:blue"); ax[k].plot(gf[:, k] / Hf, ys, label="female", color="tab:orange")
        ax[k].set_title(t); ax[k].grid(alpha=.3)
    ax[0].set_ylabel("height / H"); ax[0].legend()
    for a_ in ax:
        a_.axhline(0.53, color="g", lw=.6, ls=":"); a_.axhline(0.72, color="g", lw=.6, ls=":")
    fig.suptitle("Torso (chest+abdomen+pelvis+waist band+hip joints) profile, normalised by height")
    fig.tight_layout(); fig.savefig(OUT / "06_torso_profile.png", dpi=110); plt.close(fig); print("saved 06")

    # ---------------------------------------------------------------- 5) 비율 막대 (female/male 키 정규화 비)
    keys = ["shoulder_width", "hip_width", "head_width", "head_height", "upper_arm_len", "forearm_len", "thigh_len", "shin_len", "knee_height", "chin_height"]
    pm = proportions(m); tm = torso_measures(m); tf = torso_measures(f)
    vals = [(k, (pf[k] / pf["H"]) / (pm[k] / pm["H"])) for k in keys]
    vals += [("waist girth", (tf["waist"][0] / Hf) / (tm["waist"][0] / Hm)), ("hip girth", (tf["hip"][0] / Hf) / (tm["hip"][0] / Hm)), ("bust girth", (tf["bust"][0] / Hf) / (tm["bust"][0] / Hm))]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.barh([k for k, _ in vals], [v for _, v in vals], color=["tab:red" if abs(v - 1) > .15 else "tab:gray" for _, v in vals])
    ax.axvline(1, color="k", lw=.8); ax.set_xlabel("(female / H) / (male / H)   1.0 = unchanged relative to height"); ax.invert_yaxis()
    ax.set_title("What the morph changed, normalised by body height"); fig.tight_layout(); fig.savefig(OUT / "07_ratio_change.png", dpi=110); plt.close(fig); print("saved 07")


if __name__ == "__main__":
    main()
