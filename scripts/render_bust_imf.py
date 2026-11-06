"""작업 1 근거 이미지: 정점 열(x=apex) 앞면 높이 z(y), 이차 흉벽 적합, 초과 높이 E, 이전(E>3mm)/수정(기울기) 경계. 출력 tests/artifacts/10_bust_imf_profile.png"""
import sys
from pathlib import Path

import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import bust_eval as be
import bust_metrics as bm
from qa_metrics import full_female, tri_labels_full

A = be.evaluate("female")["analysis"]; d = A["right"]
xs, ys, Z, E = A["_grid"]
i = int(round((d["apex"][0] - xs[0]) / bm.STEP))
f = full_female(); tl = tri_labels_full()
Zs = {lab: bm.heightfield(f.pos[f.tri[tl == lab]], xs, ys) for lab in ("body:chest", "body:abdomen")}
wall = Z[:, i] - E[:, i]
fig, ax = plt.subplots(1, 2, figsize=(13, 6))
for lab, c in (("body:chest", "#c8864a"), ("body:abdomen", "#4a7fc8")):
    ax[0].plot(Zs[lab][:, i] * 1000, ys, c, label=lab.split(":")[1] + " 셸")
ax[0].plot(wall * 1000, ys, "k--", label="이차 흉벽 적합")
for y, c, t in ((d["y_bottom"], "r", "이전 하단 E>3mm"), (d["imf_y"], "g", "수정 IMF"), (d["crown_y"], "g", "수정 상단")):
    ax[0].axhline(y, color=c, lw=1); ax[0].text(2, y + 0.002, f"{t} y={y:.3f}", color=c, fontsize=8)
ax[0].set_xlabel("앞면 z [mm] (x=apex)"); ax[0].set_ylabel("y [m]"); ax[0].set_ylim(1.08, 1.40); ax[0].legend(loc="lower right")
ax[0].set_title("앞면 프로파일: 판 선반(y 1.15~1.20)이 흉벽 적합 위로 약 10 mm")
ax[1].plot(E[:, i] * 1000, ys, "k"); ax[1].axvline(3, color="r", ls=":", lw=1)
for y, c in ((d["y_bottom"], "r"), (d["imf_y"], "g"), (d["crown_y"], "g")):
    ax[1].axhline(y, color=c, lw=1)
ax[1].set_xlabel("초과 높이 E [mm]"); ax[1].set_ylim(1.08, 1.40); ax[1].set_title("E: 선반은 완만(기울기 0.1), 컵 벽은 가파름(기울기 1)")
plt.tight_layout(); out = Path(__file__).resolve().parents[1] / "tests" / "artifacts" / "10_bust_imf_profile.png"
plt.savefig(out, dpi=110); print(out)
