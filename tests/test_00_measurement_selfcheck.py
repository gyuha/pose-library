"""측정 코드 자체 검증. 이 파일이 통과해야 test_08_bust.py 의 수치를 믿을 수 있다.
 - 합성 곡면: 부피를 해석적으로 아는 물방울형/원뿔형 유방 (tests/synthetic.py)
 - male: 유방이 없으므로 '가슴 없음'으로 측정되어야 한다 (측정 잡음 상한을 정한다)
 - 구별력: 원뿔은 roundness 가 낮고, V 홈은 곡률이 높다.
"""
import numpy as np
import pytest

import bust_eval as be
import bust_metrics as bm
import synthetic as sy

H = 1.757


@pytest.fixture(scope="module")
def drop():
    return bm.analyse(sy.surface_triangles(), H)


def test_synthetic_volume_recovered(drop):
    true = sy.true_volume_cm3()
    for side in ("left", "right"):
        assert abs(drop[side]["volume_cm3"] / true - 1) <= 0.08, f"{side}: {drop[side]['volume_cm3']:.0f} vs 해석값 {true:.0f} cm3"


def test_synthetic_projection_recovered(drop):
    assert abs(drop["left"]["projection_m"] - 0.07) <= 0.003


def test_synthetic_apex_location(drop):
    assert abs(drop["right"]["apex"][0] - 0.095) <= 0.004 and abs(drop["right"]["apex"][1] - 1.265) <= 0.004
    assert abs(drop["left"]["apex"][0] + 0.095) <= 0.004


def test_synthetic_curved_wall_is_not_counted_as_breast():
    """벽이 곡면이어도(무유방) 유방으로 오인하지 않는다."""
    r = bm.analyse(sy.surface_triangles(p=0.0), H)
    assert r["left"] is None or r["left"]["volume_cm3"] < 30


def test_synthetic_teardrop_has_expected_shape():
    r = bm.analyse(sy.surface_triangles(up=0.075, low=0.05), H)["right"]
    assert r["apex_rel_height"] < 0.5, "위쪽이 더 긴 물방울은 최대 돌출점이 중앙보다 아래여야 함"
    assert 0.5 < r["upper_volume_fraction"] < 0.7, f"위쪽이 큰 물방울의 upper 비율 {r['upper_volume_fraction']:.2f}"


def test_cone_is_distinguished_from_dome(drop):
    cone = bm.analyse(sy.surface_triangles(cone=True), H)["right"]
    assert drop["right"]["roundness"] >= 0.75 > cone["roundness"], f"둥근 {drop['right']['roundness']:.2f}, 원뿔 {cone['roundness']:.2f}"


def test_wall_is_recovered_with_non_quadratic_perturbation():
    """흉벽이 이차식이 아니어도(x^4 항 추가) 부피 오차가 15% 이내."""
    T = sy.surface_triangles()
    T = T.copy(); T[..., 2] -= 6.0 * T[..., 0] ** 4
    r = bm.analyse(T, H)["right"]
    assert abs(r["volume_cm3"] / sy.true_volume_cm3() - 1) <= 0.15, f"{r['volume_cm3']:.0f} vs {sy.true_volume_cm3():.0f}"


def test_v_groove_has_higher_curvature_than_u_groove():
    """중앙 골이 V 인 표면과 평평한 흉골 표면을 곡률로 구별한다."""
    flat = bm.analyse(sy.surface_triangles(cx=0.095, rx=0.058), H)["midline_curvature"]
    v = sy.surface_triangles(cx=0.095, rx=0.058)
    v = v.copy(); v[..., 2] -= 0.025 * np.clip(1 - np.abs(v[..., 0]) / 0.012, 0, None)  # x=0 에 뾰족한 V 홈
    kv = bm.analyse(v, H)["midline_curvature"]
    assert kv > 3 * max(flat, 5.0), f"flat {flat:.1f}, V {kv:.1f}"


def test_male_chest_is_measured_as_no_bust():
    """male 대조군: 유방 부피 < 60 cm3, 돌출 < 20 mm (측정 잡음 상한). female 기준(350 cm3 / 60 mm)보다 충분히 작다."""
    a = be.evaluate("male")["analysis"]
    for side in ("left", "right"):
        d = a[side]
        assert d is None or (d["volume_cm3"] < 60 and d["projection_m"] < 0.020), f"male {side}: {d['volume_cm3']:.0f} cm3, {d['projection_m'] * 1000:.0f} mm"


def test_male_and_female_are_separated_by_bust_volume():
    f = be.evaluate("female")["analysis"]
    m = be.evaluate("male")["analysis"]
    vm = max((m[s]["volume_cm3"] if m[s] else 0.0) for s in ("left", "right"))
    vf = max((f[s]["volume_cm3"] if f[s] else 0.0) for s in ("left", "right"))
    # 이 검사는 '측정이 두 모델을 구분하는가'만 본다. female 이 기준을 만족하는지는 test_08 이 본다.
    assert vf > vm, f"female {vf:.0f} <= male {vm:.0f} cm3: 측정이 구분하지 못함"


def test_male_sternum_ridge_is_small_and_w_profile_is_detected():
    male = be.evaluate("male")["analysis"]["sternum_ridge"]
    assert male * 1000 < 4.0, f"male 흉골 솟음 {male * 1000:.1f} mm (측정 잡음 상한)"
    T = sy.surface_triangles().copy()
    T[..., 2] += 0.012 * np.clip(1 - np.abs(T[..., 0]) / 0.015, 0, None) * (np.abs(T[..., 0]) < 0.015)  # x=0 에 12 mm 능선
    ridge = bm.analyse(T, H)["sternum_ridge"] * 1000
    assert ridge > 8.0, f"합성 중앙 능선 12 mm 가 {ridge:.1f} mm 로 측정됨"


def test_separation_detects_merged_breasts():
    """[v2.1] 분리된 합성 유방은 골 초과 높이 ~0, 하나로 붙은 합성 유방(cx=0.03)은 크게 측정된다. male 은 15 mm 미만."""
    sep = bm.analyse(sy.surface_triangles(), H)
    merged = bm.analyse(sy.surface_triangles(cx=0.03, rx=0.075), H)
    assert sep["cleavage_excess"] * 1000 < 3 and sep["bridge_height"] == 0
    assert merged["cleavage_excess"] * 1000 > 30 and merged["bridge_height"] > 0.05, (merged["cleavage_excess"], merged["bridge_height"])
    assert be.evaluate("male")["analysis"].get("cleavage_excess", 0.0) * 1000 < 15


def test_sharp_edge_counter_detects_notch():
    T = sy.surface_triangles()
    c = T.mean(1)
    zone = T[(c[:, 1] > 1.10) & (c[:, 1] < 1.20) & (np.abs(c[:, 0]) < 0.13)]
    base = be.sharp_edges(zone)
    N = zone.copy()
    box = (np.abs(N[..., 0] - 0.07) < 0.012) & (np.abs(N[..., 1] - 1.15) < 0.012)
    N[..., 2] -= 0.008 * box  # 사각형 노치(8 mm)
    notch = be.sharp_edges(N)
    assert base[0] <= 2 and notch[0] >= 8, f"매끈 {base}, 노치 {notch}"
    m, _ = be.lower_rim_sharp_edges("male"), None
    assert m[0] <= 10, f"male 하단 날카로운 모서리 {m}"
