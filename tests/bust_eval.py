"""가슴 평가: 합성/실측 공통 파이프라인 위에 둘레, 메시 매끄러움, 좌우 대칭을 얹는다."""
import functools

import numpy as np

import bust_metrics as bm
from qa_metrics import (SCALE, full_female, height, hull_area_perimeter, models, parts, parts_full, section_points,
                        tri_labels_full, torso_triangles)

BUST_TRI_LABELS = ("body:chest", "body:abdomen")


def surface_tris(which):
    if which == "male":
        m = models()[0]; tl = parts()[m.tri[:, 0]]
        return m.pos[m.tri[np.isin(tl, BUST_TRI_LABELS)]]
    f = full_female()
    return f.pos[f.tri[np.isin(tri_labels_full(), BUST_TRI_LABELS)]]


def girth(model, y):
    P = section_points(torso_triangles(model), np.array([0, 1.0, 0]), y)
    return hull_area_perimeter(P[:, [0, 2]])[1] if len(P) >= 3 else float("nan")


def _weld(pos, tol=1e-5):
    key = np.round(pos / tol).astype(np.int64)
    _, inv = np.unique(key, axis=0, return_inverse=True)
    return inv.ravel()


SPIKE_D, SPIKE_R = 0.008, 0.5   # 스파이크 판정: 이웃 평균 대비 편차 d > 8 mm 이고 비율 r = d/이웃 평균 거리 > 0.5


def spike_stats(inv, T, P, fn):
    """[v4] 정점 스파이크. 정점 v 의 편차 d = |(v - 이웃 평균) . 법선|, 비율 r = d / (이웃까지 평균 거리).
    d 만 보면 촘촘한 smooth 면에서는 수 mm 돌기를 잡지만, 변 길이 40 mm 인 로우폴리 면에서는 정상 모서리
    정점이 10 mm 이상 나온다(예: 판 모서리 15 mm / 변 44 mm = r 0.35). r 은 '이웃 대비 얼마나 뾰족한가'(원뿔 기울기)라 해상도와 무관하다.
    점수 = min(d/8 mm, r/0.5), 1 을 넘으면 스파이크(둘 다 넘어야 함). 반환: 점수가 가장 큰 정점의 (점수, d, r, 위치)."""
    nb = {}
    for t in inv[T]:
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            if a != b:
                nb.setdefault(a, set()).add(b); nb.setdefault(b, set()).add(a)
    Wp = np.zeros((inv.max() + 1, 3)); Wp[inv] = P
    vn = np.zeros_like(Wp)
    for k in range(3):
        np.add.at(vn, inv[T[:, k]], fn)
    vn /= np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-15)
    best = (0.0, 0.0, 0.0, None)
    for v, ns in nb.items():
        if len(ns) >= 3:
            ns = list(ns)
            d = abs(float((Wp[v] - Wp[ns].mean(0)) @ vn[v]))
            r = d / max(float(np.linalg.norm(Wp[ns] - Wp[v], axis=1).mean()), 1e-9)
            sc = min(d / SPIKE_D, r / SPIKE_R)
            if sc > best[0]:
                best = (sc, d, r, Wp[v].tolist())
    return best, Wp


def mesh_smoothness(box):
    """full_female 의 가슴 쉘 중 box=(x0,x1,y0,y1) 안에 중심이 있는 삼각형의 인접 면 이면각(도)과 정점 스파이크[m].
    box 가 None 이면 가슴 앞면(z>0.03) 전체."""
    f = full_female(); tl = tri_labels_full()
    chest = np.where(tl == "body:chest")[0]
    cen = f.pos[f.tri[chest]].mean(1)
    sel = (cen[:, 2] > 0.03) if box is None else ((cen[:, 2] > 0.03) & (cen[:, 0] >= box[0]) & (cen[:, 0] <= box[1]) & (cen[:, 1] >= box[2]) & (cen[:, 1] <= box[3]))
    tris = chest[sel]
    T = f.tri[tris]
    inv = _weld(f.pos)
    P = f.pos
    fn = np.cross(P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]])
    fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-15)
    edge = {}
    for k, t in enumerate(inv[T]):
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            if a != b:
                edge.setdefault((min(a, b), max(a, b)), []).append(k)
    ang, where = [], []
    for e, ks in edge.items():
        if len(ks) == 2:
            c = float(np.clip(fn[ks[0]] @ fn[ks[1]], -1, 1))
            ang.append(np.degrees(np.arccos(c))); where.append(e)
    ang = np.array(ang) if ang else np.zeros(1)
    # 정점 스파이크: 이웃 평균 대비 법선 방향 편차 (절대값 mm 와 변 길이로 정규화한 비율, spike_stats)
    (sc, sd, sr, sv), Wp = spike_stats(inv, T, P, fn)
    worst_edge = where[int(np.argmax(ang))] if where else None
    return {"max_dihedral": float(ang.max()), "p95_dihedral": float(np.percentile(ang, 95)), "n_edges": len(ang),
            "frac_over_25": float((ang > 25).mean()),
            "spike_score": sc, "max_spike": sd, "max_spike_ratio": sr, "spike_xyz": sv,
            "worst_edge_xyz": None if worst_edge is None else Wp[list(worst_edge)].mean(0).tolist()}


@functools.lru_cache(None)
def evaluate(which):
    """which: 'male' | 'female'. 높이장 분석 + 둘레 + (female 만) 메시 매끄러움."""
    m, c = models()
    model = m if which == "male" else c
    H = height(model)
    a = bm.analyse(surface_tris(which), H)
    out = {"H": H, "analysis": a}
    sides = [s for s in (a["left"], a["right"]) if s]
    if sides:
        ya = float(np.mean([s["apex"][1] for s in sides])); yb = float(np.mean([s["y_bottom"] for s in sides]))
        yimf = float(np.mean([s["imf_y"] for s in sides]))   # [v4] 밑가슴둘레는 E>3mm 하단(yb)이 아니라 형상에서 검출한 IMF 기준
        out["bust_girth"] = girth(model, ya); out["underbust_girth"] = girth(model, yimf - 0.01)
        out["bust_girth_y"], out["underbust_girth_y"] = ya, yimf - 0.01
        if which == "female":
            xs = [abs(s["apex"][0]) for s in sides]
            out["smoothness"] = mesh_smoothness((-(max(xs) + 0.07), max(xs) + 0.07, yb - 0.02, max(s["y_top"] for s in sides) + 0.02))
    elif which == "female":
        out["smoothness"] = mesh_smoothness(None)
    return out


def front_asymmetry(which):
    """가슴 앞면 높이장의 좌우 차 |z(x,y) - z(-x,y)| 의 최대값과 99백분위 [m] (|x|<=0.17).
    정점 최근접 거리 대신 표면 높이를 비교한다: 세분화 격자는 원본 삼각분할(대각선 방향)이 좌우 대칭이 아니라서
    정점 위치는 표면이 완전히 대칭이어도 수 mm 어긋난다."""
    xs, ys, Z, E = evaluate(which)["analysis"]["_grid"]
    n = len(xs)
    d = np.abs(Z - Z[:, ::-1])
    d = np.where((np.abs(xs)[None, :] <= 0.17) & np.isfinite(d), d, np.nan)
    d = d[:, : n // 2 + 1]
    return float(np.nanmax(d)), float(np.nanpercentile(d, 99))


def sharp_edges(T, thr=30.0):
    """삼각형 집합 T(m,3,3) 에서 인접 두 면의 이면각이 thr(도)를 넘는 모서리의 (개수, 총 길이[m])."""
    key = np.round(T.reshape(-1, 3) / 1e-5).astype(np.int64)
    _, inv = np.unique(key, axis=0, return_inverse=True)
    inv = inv.ravel().reshape(-1, 3)
    P = np.zeros((inv.max() + 1, 3)); P[inv.ravel()] = T.reshape(-1, 3)
    fn = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-15)
    ed = {}
    for k, t in enumerate(inv.tolist()):
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            if a != b:
                ed.setdefault((min(a, b), max(a, b)), []).append(k)
    n, tot = 0, 0.0
    for (a, b), ks in ed.items():
        if len(ks) == 2 and np.degrees(np.arccos(np.clip(fn[ks[0]] @ fn[ks[1]], -1, 1))) > thr:
            n += 1; tot += float(np.linalg.norm(P[a] - P[b]))
    return n, tot


@functools.lru_cache(None)
def lower_rim_sharp_edges(which):
    """가슴 쉘 하단(최하단 +8 cm, 앞면 z>0.03, |x|<=0.13)의 날카로운(>30°) 모서리. male 은 0.925 배로 줄여 female 과 같은 크기로 비교.
    계단/사각형 노치는 짧고 날카로운 모서리를 많이 만든다."""
    if which == "male":
        m = models()[0]; pos, tri, tl = m.pos * SCALE, m.tri, parts()[m.tri[:, 0]]
    else:
        f = full_female(); pos, tri, tl = f.pos, f.tri, tri_labels_full()
    ch = np.where(tl == "body:chest")[0]
    ymin = pos[tri[ch]].reshape(-1, 3)[:, 1].min()
    cen = pos[tri[ch]].mean(1)
    sel = ch[(cen[:, 1] < ymin + 0.08) & (cen[:, 2] > 0.03) & (np.abs(cen[:, 0]) < 0.13)]
    return sharp_edges(pos[tri[sel]])
