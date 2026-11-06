"""[v4] 가슴 측정 재정의(IMF 검출, 변 길이 정규화 스파이크)가 진짜 결함을 여전히 잡는지 합성 반례로 확인한다.
수정한 기준마다 (a) 오탐이던 입력은 통과하고 (b) 같은 종류의 진짜 결함은 실패해야 한다.
"""
import numpy as np

import bust_eval as be
import bust_metrics as bm
import synthetic as sy
from qa_metrics import strict_intersections

H = 1.757
TRUE_IMF = 1.265 - 0.055   # synthetic.bump 기본값: apex cy - low


def _with_shelf(T):
    """판 선반 재현: 컵 아래 y 1.14~1.20 에 흉벽 대비 +10 mm 의 평평한 선반과 1.14 아래쪽 20 mm 계단(배 셸 위를 덮는 판 모서리)."""
    T = T.copy()
    y = T[..., 1]
    x = np.abs(T[..., 0])
    shelf = (y >= 1.14) & (y <= 1.20) & (x < 0.15)
    T[..., 2] += 0.010 * shelf
    T[..., 2] -= 0.020 * ((y < 1.14) & (y > 1.10) & (x < 0.15))
    return T


# ---- IMF / 컵 경계 ------------------------------------------------------------------------------------------
def test_imf_matches_true_cup_base_on_clean_surface():
    r = bm.analyse(sy.surface_triangles(), H)["right"]
    assert abs(r["imf_y"] - TRUE_IMF) <= 0.012, f"검출 IMF {r['imf_y']:.3f} vs 참값 {TRUE_IMF:.3f}"


def test_imf_ignores_plate_shelf_that_fooled_threshold_method():
    """선반이 있어도 IMF 는 컵 시작점에 남고(수정 후), E>3 mm 하단(y_bottom, 수정 전 방식)은 선반 아래로 끌려 내려간다 = 오탐 재현."""
    r = bm.analyse(_with_shelf(sy.surface_triangles()), H)["right"]
    assert abs(r["imf_y"] - TRUE_IMF) <= 0.015, f"선반이 있는 면에서 IMF {r['imf_y']:.3f} vs 참값 {TRUE_IMF:.3f}"
    assert TRUE_IMF - r["y_bottom"] >= 0.03, f"선반 재현이 약함: y_bottom {r['y_bottom']:.3f} 이 참값 {TRUE_IMF:.3f} 보다 3 cm 이상 낮아야 한다"


def test_cup_bounds_do_not_hide_a_cone_or_oversize():
    """진짜 결함은 경계 보정과 무관하게 나온다: 원뿔은 roundness 가 낮고, 과대 유방은 돌출/부피가 기준을 넘는다."""
    cone = bm.analyse(sy.surface_triangles(cone=True), H)["right"]
    big = bm.analyse(sy.surface_triangles(p=0.10, rx=0.075, up=0.095, low=0.075), H)["right"]
    assert cone["roundness"] < 0.75
    assert big["projection_m"] > 0.080 and big["volume_cm3"] > 500, (big["projection_m"], big["volume_cm3"])


def test_asymmetric_synthetic_breasts_are_detected():
    """좌우 한쪽만 키운 합성 유방: 좌우 부피 차 > 3% 가 측정된다 (test_left_right_symmetry 의 판정량)."""
    T = sy.surface_triangles()
    ok = bm.analyse(T, H)
    c = T.mean(1)
    big = bm.analyse(sy.surface_triangles(), H)
    L = sy.surface_triangles(p=0.07); R = sy.surface_triangles(p=0.085)
    mix = np.where((c[:, 0] > 0)[:, None, None], R, L)   # 오른쪽(x>0)만 돌출 85 mm
    r = bm.analyse(mix, H)
    dv = lambda a: abs(a["left"]["volume_cm3"] / a["right"]["volume_cm3"] - 1)
    assert dv(ok) < 0.03 and dv(r) > 0.10, (dv(ok), dv(r))


# ---- 스파이크 -----------------------------------------------------------------------------------------------
def _grid(step, nx, ny, bump=None):
    xs = np.arange(nx) * step; ys = np.arange(ny) * step
    X, Y = np.meshgrid(xs, ys)
    Z = 0.05 * np.exp(-((X - xs.mean()) ** 2 + (Y - ys.mean()) ** 2) / (2 * (4 * step) ** 2))   # 완만한 혹(정상 곡면)
    if bump:
        Z[bump[0], bump[1]] += bump[2]
    P = np.stack([X, Y, Z], -1)
    a, b, c, d = P[:-1, :-1], P[:-1, 1:], P[1:, 1:], P[1:, :-1]
    return np.concatenate([np.stack([a, b, c], 2).reshape(-1, 3, 3), np.stack([a, c, d], 2).reshape(-1, 3, 3)])


def _score(T):
    """삼각형 수프 -> spike_stats 입력(풀 정점 P, 삼각형 인덱스 idx, 용접 맵 inv=항등)."""
    key = np.round(T.reshape(-1, 3) / 1e-6).astype(np.int64)
    _, first, idx = np.unique(key, axis=0, return_index=True, return_inverse=True)
    P = T.reshape(-1, 3)[first]; idx = idx.ravel().reshape(-1, 3)
    fn = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-15)
    (sc, d, r, _xyz), _w = be.spike_stats(np.arange(len(P)), idx, P, fn)
    return sc, d, r


def test_spike_detected_on_dense_and_on_lowpoly_meshes():
    dense_ok, dense_bad = _grid(0.003, 40, 40), _grid(0.003, 40, 40, bump=(20, 20, 0.012))   # 12 mm 단일 정점 돌기, 변 3 mm
    low_ok, low_bad = _grid(0.040, 12, 12), _grid(0.040, 12, 12, bump=(6, 6, 0.030))           # 30 mm 단일 정점 돌기, 변 40 mm
    assert _score(dense_ok)[0] < 1 and _score(dense_bad)[0] > 1, (_score(dense_ok), _score(dense_bad))
    assert _score(low_ok)[0] < 1 and _score(low_bad)[0] > 1, (_score(low_ok), _score(low_bad))


def test_lowpoly_corner_is_not_a_spike_but_old_criterion_would_flag_it():
    """오탐 재현: 변 40 mm 면에서 완만한 정상 곡면의 편차 d 는 8 mm 를 넘어도(예전 기준 실패) 비율 r 이 작아 스파이크가 아니다."""
    sc, d, r = _score(_grid(0.040, 12, 12, bump=(6, 6, 0.012)))   # 12 mm 정점 돌출: d 약 9 mm 이상, r 은 0.5 미만
    assert d > 0.008 and r < 0.5 and sc < 1, (sc, d, r)


# ---- 수정하지 않은 기준(관통/퇴화)이 여전히 반례를 잡는지 (회귀 방지) -----------------------------------------
def test_intersection_detector_still_flags_crossing_triangles():
    A = np.array([[[0, 0, 0], [1, 0, 0], [0, 1, 0]]], float)
    B = np.array([[[0.2, 0.2, -0.5], [0.2, 0.2, 0.5], [0.8, 0.2, 0.0]]], float)   # A 를 관통
    assert strict_intersections(np.concatenate([A, B])) == {(0, 1)}
    assert strict_intersections(np.concatenate([A, B + [0, 0, 2]])) == set()


def test_degenerate_triangle_formula_flags_zero_area():
    T = np.array([[[0, 0, 0], [1, 0, 0], [2, 0, 0]], [[0, 0, 0], [1, 0, 0], [0, 1, 0]]], float)
    area = np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1) / 2
    assert list(area > 1e-9) == [False, True]
