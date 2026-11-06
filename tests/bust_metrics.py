"""가슴(유방) 측정. 입력은 몸통 앞면 삼각형 집합(가슴+배 쉘)이고 메시 구조에 의존하지 않는다 (세분화/추가 정점과 무관).

측정 원리
 1. 높이장: 2 mm 격자에서 (x,y) 마다 가장 앞쪽(+z) 표면의 z 를 구한다 (수직 레이캐스트와 동일).
 2. 흉벽 기준면: 한쪽 유방마다, 유방 중심(젖꼭지) 주위 환형 구간(반지름 R_IN~R_OUT, 반대쪽 유방 쪽은 제외)의
    높이장에 이차 곡면 z = a + b*dx + c*dy + d*dx^2 + e*dy^2 + f*dx*dy (dx,dy = 중심 기준 좌표)를 최소제곱으로 맞춰
    유방 자리까지 외삽한다 (평면으로는 볼록한 흉곽 때문에 남자 가슴도 큰 부피로 나온다). 환형 구간은 유방 바깥의 흉벽(위/아래/바깥쪽)이다.
    중심은 해부학적 사전값(젖꼭지 높이 0.725H, 좌우 +-0.095 m)에서 시작해 초과 높이 최대점으로 3회 갱신한다. [근사, 내 휴리스틱]
 3. 초과 높이 E = z - 흉벽. 좌우(x 부호)별로 E > 3 mm 인 영역이 한쪽 유방이다.
    부피 = sum(E * dA)  (흉벽 기준면 위쪽, 그 면까지 닫은 폐곡면의 부피와 같다), 돌출 = max(E).
이 방법이 맞는지는 tests/test_00_measurement_selfcheck.py 가 '부피를 아는 합성 곡면'으로 확인한다.
"""
import math

import numpy as np

STEP = 0.002  # 격자 간격 [m]
R_B, R_IN, R_OUT = 0.11, 0.12, 0.17  # 유방 적분 반지름 / 흉벽 환형 구간 안쪽·바깥쪽 반지름 [m] (modeler 값과의 교차검증으로 고름)


def heightfield(T, xs, ys):
    """삼각형 T(m,3,3) 의 가장 앞쪽 표면 높이장 Z[y,x] (표면이 없는 칸은 nan)."""
    Z = np.full((len(ys), len(xs)), -np.inf)
    dx = xs[1] - xs[0]; dy = ys[1] - ys[0]
    for tri in T:
        x, y = tri[:, 0], tri[:, 1]
        i0 = max(0, int(math.ceil((x.min() - xs[0]) / dx))); i1 = min(len(xs) - 1, int(math.floor((x.max() - xs[0]) / dx)))
        j0 = max(0, int(math.ceil((y.min() - ys[0]) / dy))); j1 = min(len(ys) - 1, int(math.floor((y.max() - ys[0]) / dy)))
        if i1 < i0 or j1 < j0:
            continue
        X, Y = np.meshgrid(xs[i0:i1 + 1], ys[j0:j1 + 1])
        den = (y[1] - y[2]) * (x[0] - x[2]) + (x[2] - x[1]) * (y[0] - y[2])
        if abs(den) < 1e-14:
            continue
        u = ((y[1] - y[2]) * (X - x[2]) + (x[2] - x[1]) * (Y - y[2])) / den
        v = ((y[2] - y[0]) * (X - x[2]) + (x[0] - x[2]) * (Y - y[2])) / den
        w = 1 - u - v
        z = u * tri[0, 2] + v * tri[1, 2] + w * tri[2, 2]
        inside = (u >= -1e-9) & (v >= -1e-9) & (w >= -1e-9)
        cur = Z[j0:j1 + 1, i0:i1 + 1]
        Z[j0:j1 + 1, i0:i1 + 1] = np.where(inside & (z > cur), z, cur)
    Z[np.isinf(Z)] = np.nan
    return Z


def _basis(X, Y, cx, cy):
    dx, dy = X - cx, Y - cy
    return np.stack([np.ones_like(dx), dx, dy, dx * dx, dy * dy, dx * dy], -1)


def fit_wall(X, Y, Z, cx, cy, sign):
    """중심 (cx,cy) 주위 환형 구간(유방 바깥 흉벽)에 이차 곡면을 맞춘다. 반환 계수 6개."""
    r2 = (X - cx) ** 2 + (Y - cy) ** 2
    use = np.isfinite(Z) & (r2 >= R_IN ** 2) & (r2 <= R_OUT ** 2) & (sign * X >= -0.01)
    coef, *_ = np.linalg.lstsq(_basis(X, Y, cx, cy)[use], Z[use], rcond=None)
    return coef


def wall_at(coef, X, Y, cx, cy):
    return _basis(X, Y, cx, cy) @ coef


def sample(Z, xs, ys, x, y):
    i = int(round((x - xs[0]) / (xs[1] - xs[0]))); j = int(round((y - ys[0]) / (ys[1] - ys[0])))
    if 0 <= i < len(xs) and 0 <= j < len(ys):
        return Z[j, i]
    return np.nan


def _crossing(prof_y, prof_e, level, start, step):
    """프로파일에서 start 인덱스부터 step(+1/-1) 방향으로 E 가 level 아래로 처음 내려가는 y (선형보간)."""
    i = start
    while 0 <= i + step < len(prof_e):
        a, b = prof_e[i], prof_e[i + step]
        if a >= level > b:
            return prof_y[i] + (prof_y[i + step] - prof_y[i]) * (a - level) / (a - b)
        i += step
    return np.nan


GRAD_MIN = 0.30  # 컵 경계: 정점 열에서 E 의 세로 기울기(|dE/dy|, 1 cm 이동평균)가 이 값 아래로 내려가는 곳 (약 17도)


def cup_bounds(prof_y, prof_e, ia):
    """정점 열 프로파일 E(y) 에서 컵의 아래/위 경계 y. [v4] IMF(아래 경계)를 형상에서 검출한다.
    정점에서 위/아래로 걸어가며 |dE/dy| 가 GRAD_MIN 아래로 처음 내려가는 y 를 경계로 한다.
    이 기울기는 흉벽 기준면이 수 mm 어긋나도 변하지 않는다: E>3 mm 임계값은 흉벽 기준이 낮게 잡히면
    컵 아래의 평평한 선반(판)까지 유방으로 세지만, 기울기 기준은 선반(기울기 ~0.1)과 컵 벽(기울기 ~1)을 구별한다.
    위/아래에 같은 규칙을 쓴다(한쪽만 바꾸면 apex 상대 높이가 한쪽으로 치우친다)."""
    h = int(round(0.005 / STEP))
    g = np.full(len(prof_e), np.nan)
    for i in range(h, len(prof_e) - h):
        g[i] = (prof_e[i + h] - prof_e[i - h]) / (2 * h * STEP)

    def walk(step):
        i, on_wall = ia, False   # 정점 부근은 기울기가 0 이므로 컵 벽에 한 번 들어선 뒤 다시 내려가는 곳을 찾는다
        while 0 < i < len(prof_e) - 1:
            if np.isfinite(g[i]):
                if abs(g[i]) >= GRAD_MIN:
                    on_wall = True
                elif on_wall:
                    return float(prof_y[i])
            i += step
        return float(prof_y[0] if step < 0 else prof_y[-1])
    return walk(-1), walk(+1)


def side_metrics(E, X, Y, Z, xs, ys, sign, thr=0.003):
    mask = (E > thr) & (sign * X > 0) & np.isfinite(E)
    if mask.sum() < 20:
        return None
    dA = STEP * STEP
    Em = np.where(mask, E, 0.0)
    vol = float(Em.sum() * dA)
    p = float(np.nanmax(np.where(mask, E, -np.inf)))
    jy, ix = np.unravel_index(np.nanargmax(np.where(mask, E, -np.inf)), E.shape)
    xa, ya = float(xs[ix]), float(ys[jy])
    rows = np.where(mask.any(axis=1))[0]
    y_top, y_bot = float(ys[rows.max()]), float(ys[rows.min()])
    cols = np.where(mask.any(axis=0))[0]
    v_up = float(Em[ys > ya].sum() * dA)
    # 정점(apex)을 지나는 수직 프로파일
    col = ix
    prof_y = ys[(ys >= y_bot - 0.02) & (ys <= y_top + 0.02)]
    prof_e = E[(ys >= y_bot - 0.02) & (ys <= y_top + 0.02), col]
    prof_e = np.nan_to_num(prof_e, nan=0.0)
    ia = int(np.argmin(np.abs(prof_y - ya)))
    imf_y, crown_y = cup_bounds(prof_y, prof_e, ia)
    imf_y, crown_y = max(imf_y, y_bot), min(crown_y, y_top)
    def dev(lo, hi):
        sel = (prof_y >= lo) & (prof_y <= hi)
        yy, ee = prof_y[sel], prof_e[sel]
        if len(yy) < 3:
            return np.nan
        chord = np.interp(yy, [yy[0], yy[-1]], [ee[0], ee[-1]])
        return float(np.mean(ee - chord) / p)
    dev_up, dev_low = dev(ya, crown_y), dev(imf_y, ya)
    # 아래/위 윤곽이 흉벽과 만나는 각도: E 가 0.15p -> 0.45p 로 오르는 구간의 기울기
    def angle(a, b):
        if not (np.isfinite(a) and np.isfinite(b)) or abs(a - b) < 1e-6:
            return np.nan
        return math.degrees(math.atan(0.30 * p / abs(a - b)))
    low = angle(_crossing(prof_y, prof_e, 0.15 * p, ia, -1), _crossing(prof_y, prof_e, 0.45 * p, ia, -1))
    up = angle(_crossing(prof_y, prof_e, 0.15 * p, ia, +1), _crossing(prof_y, prof_e, 0.45 * p, ia, +1))
    # 원뿔도: apex 주위 반지름 20 mm 원둘레 평균 E / p (원뿔 0.64, 반구형 0.87 부근)
    ring = []
    for a in np.linspace(0, 2 * math.pi, 16, endpoint=False):
        v = sample(E, xs, ys, xa + 0.02 * math.cos(a), ya + 0.02 * math.sin(a))
        if np.isfinite(v):
            ring.append(v)
    return {"volume_cm3": vol * 1e6, "projection_m": p, "apex": (xa, ya), "y_top": y_top, "y_bottom": y_bot,
            "imf_y": imf_y, "crown_y": crown_y,
            "height_m": crown_y - imf_y, "apex_rel_height": (ya - imf_y) / max(crown_y - imf_y, 1e-9),
            "upper_volume_fraction": v_up / vol, "upper_contour_dev": dev_up, "lower_contour_dev": dev_low,
            "angle_upper_deg": up, "angle_lower_deg": low,
            "roundness": float(np.mean(ring) / p) if ring else np.nan,
            "width_m": float((cols.max() - cols.min()) * STEP)}


def midline_curvature(Z, xs, ys, y_lo, y_hi, h=0.010):
    """x=0 에서 z(x) 의 2차 미분(굽힘)의 평균 [1/m]. V 홈일수록 크고 U/평평할수록 작다."""
    ks = []
    for y in np.arange(y_lo, y_hi, STEP):
        a, b, c = sample(Z, xs, ys, -h, y), sample(Z, xs, ys, 0.0, y), sample(Z, xs, ys, h, y)
        if np.isfinite([a, b, c]).all():
            ks.append(abs(a - 2 * b + c) / h ** 2)
    return float(np.mean(ks)) if ks else np.nan


def sternum_ridge(Z, xs, ys, y_lo, y_hi):
    """흉골 중앙(x=0) 높이가 좌우 15~45 mm 지점의 최저 높이보다 얼마나 솟았는가 [m] (행 평균, 양수만).
    유방 사이는 가운데가 가장 낮은 골이어야 하며, 가운데가 솟고 양옆이 패이면 이중 골(W자)이다."""
    out = []
    for y in np.arange(y_lo, y_hi, STEP):
        c = sample(Z, xs, ys, 0.0, y)
        side = [sample(Z, xs, ys, sg * x, y) for sg in (-1, 1) for x in np.arange(0.015, 0.0451, 0.005)]
        side = [v for v in side if np.isfinite(v)]
        if np.isfinite(c) and side:
            out.append(max(0.0, c - min(side)))
    return float(np.mean(out)) if out else np.nan


def analyse(T_surface, H):
    """몸통 앞면 삼각형 -> 가슴 지표 사전."""
    xs = np.arange(-0.24, 0.24 + 1e-9, STEP)
    ys = np.arange(0.725 * H - R_OUT - 0.01, 0.725 * H + R_OUT + 0.01, STEP)
    Z = heightfield(T_surface, xs, ys)
    X, Y = np.meshgrid(xs, ys)
    E = np.full_like(Z, np.nan)
    sides, planes = {}, {}
    for sgn, name in ((-1, "left"), (1, "right")):
        cx, cy = sgn * 0.095, 0.725 * H
        for _ in range(3):
            coef = fit_wall(X, Y, Z, cx, cy, sgn)
            Es = Z - wall_at(coef, X, Y, cx, cy)
            near = np.isfinite(Es) & ((X - cx) ** 2 + (Y - cy) ** 2 <= 0.09 ** 2) & (sgn * X > 0.02)
            if near.any():
                j, i = np.unravel_index(np.argmax(np.where(near, Es, -np.inf)), Es.shape)
                cx, cy = float(xs[i]), float(ys[j])
        disc = ((X - cx) ** 2 + (Y - cy) ** 2 <= R_B ** 2) & (sgn * X > 0)
        E = np.where(disc, Es, E)
        planes[name] = {"center": (cx, cy), "coef": coef.tolist()}
    out = {"plane_coef": planes}
    for sgn, name in ((-1, "left"), (1, "right")):
        out[name] = side_metrics(E, X, Y, Z, xs, ys, sgn)
    ya = [s["apex"][1] for s in (out["left"], out["right"]) if s]
    out["midline_curvature"] = midline_curvature(Z, xs, ys, np.mean(ya) - 0.015, np.mean(ya) + 0.015) if ya else np.nan
    # 좌우 분리: x=0 의 흉벽 대비 초과 높이 (두 쪽 흉벽 곡면의 평균을 x=0 까지 외삽)
    wl = planes["left"]; wr = planes["right"]
    Wmid = 0.5 * (wall_at(np.array(wl["coef"]), X, Y, *wl["center"]) + wall_at(np.array(wr["coef"]), X, Y, *wr["center"]))
    Emid = Z - Wmid
    sides_ok = out["left"] and out["right"]
    if sides_ok:
        p = 0.5 * (out["left"]["projection_m"] + out["right"]["projection_m"])
        xa = 0.5 * (abs(out["left"]["apex"][0]) + abs(out["right"]["apex"][0]))
        rows = np.where((ys >= min(out["left"]["y_bottom"], out["right"]["y_bottom"])) & (ys <= max(out["left"]["y_top"], out["right"]["y_top"])))[0]
        cols = np.where(np.abs(xs) <= xa)[0]
        bridged = [j for j in rows if np.isfinite(Emid[j, cols]).all() and Emid[j, cols].min() > 0.020]
        j0 = np.where(np.abs(ys - np.mean(ya)) <= 0.010)[0]; i0 = int(np.argmin(np.abs(xs)))
        out["cleavage_excess"] = float(np.nanmean(Emid[j0, i0]))
        out["cleavage_ratio"] = out["cleavage_excess"] / p
        out["bridge_height"] = float(len(bridged) * STEP)
        out["_Emid"] = Emid
    out["sternum_ridge"] = sternum_ridge(Z, xs, ys, np.mean(ya) - 0.015, np.mean(ya) + 0.015) if ya else np.nan
    out["_grid"] = (xs, ys, Z, E)
    return out
