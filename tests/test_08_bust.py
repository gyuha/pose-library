"""[기준 v2] 가슴 검사. 기준값은 키 1.757 m 여성 마네킹의 C컵 반 물방울형 (오케스트레이터 지정).
측정 방법: tests/bust_metrics.py 의 docstring. 방법 자체의 정확도는 test_00_measurement_selfcheck.py
 (합성 곡면 오차 약 1~2%, male 대조 잡음 약 25 cm3 / 11 mm)로 확인한다.

기준 출처/신뢰도
 - 가슴둘레-밑가슴둘레 14~16 cm (KS C컵 15 cm): 오케스트레이터 지정. [Medium] 측정은 컨벡스헐 둘레 + 이차 곡면 흉벽이라 내 방법의 편향이 있다.
 - 한쪽 부피 350~500 cm3, 돌출 60~80 mm: 오케스트레이터 지정. 부피는 흉벽 '이차 곡면 외삽' 기준 근사. [Medium]
 - 상/하 극 부피비 40:60~50:50, 최대 돌출점이 유방 높이 중앙보다 아래: 오케스트레이터 지정(반 물방울형 정의). [Medium]
 - 위쪽 윤곽 오목/직선(현 대비 볼록 편차 <= +10% p), 아래쪽 볼록(>= +10% p이고 위쪽보다 5%p 이상 큼),
   IMF(아래 윤곽이 흉벽과 만나는 각도 >= 40° 이고 위쪽보다 8° 이상 가파름): 정성 요건을 수치화한 내 휴리스틱. [Low]
 - 이면각 최대 60°, 정점 스파이크 8 mm, 원뿔도(r=20 mm 원 평균 E / 돌출) >= 0.75, 중앙 곡률 <= 40 /m(곡률반경 25 mm 이상): 내 휴리스틱. [Low]
 - 중앙 골: 흉골 중앙이 좌우 골보다 6 mm 넘게 솟지 않음(이중 골 방지): 내 휴리스틱. [Low]
 - [v2.1] 좌우 분리: apex 높이에서 x=0 의 흉벽 대비 초과 높이 <= min(15 mm, 최대 돌출의 30%). 흉골 위는 흉벽에 가깝다는 해부학 근거의 휴리스틱. [Low]
 - [v2.1] 가로 띠 금지: 흉벽 대비 20 mm 넘게 솟은 영역이 x=-apex~+apex 전 구간을 한 행도 덮지 않음(uniboob). [Low]
 - [v2.1] 하단 계단/노치: 가슴 쉘 최하단+8 cm 앞면의 이면각>30° 모서리가 20개 이하이고 총길이 <= male*1.5+0.1 m. male 은 4개/0.28 m. 노치는 짧고 날카로운 모서리를 만든다는 가정의 휴리스틱. [Low]
 - [v4] IMF/컵 경계: E>3 mm 임계값 대신 정점 열의 E 기울기(|dE/dy| < 0.3, 1 cm 이동평균)로 컵의 아래/위 경계를 검출한다
   (bust_metrics.cup_bounds). 배 셸을 덮는 판의 선반(약 5 cm, 흉벽 이차 적합 대비 약 10 mm)이 유방으로 잡혀 측정 하단이 컵 시작점보다
   4 cm 낮아지던 문제의 수정. apex 상대 높이, 위/아래 윤곽 볼록도, 밑가슴둘레 위치가 이 경계를 쓴다. 근거: tests/reports/bust_reassessment.md.
 - [v4] 정점 스파이크: 변 길이로 정규화(spike_stats). 로우폴리 각진 표현 요구에 맞춘 재정의.
 - 좌우 대칭: 부피 차 3%, 정점/돌출 차 2 mm: 내 휴리스틱.
"""
import pytest

import bust_eval as be
from qa_metrics import abdomen_poke, chest_partner_sets

F = be.evaluate("female")
A = F["analysis"]
SIDES = [s for s in ("left", "right") if A[s]]


def _need_bust():
    if not SIDES:
        pytest.fail("female 에서 유방이 검출되지 않음 (흉벽 대비 3 mm 이상 돌출한 영역 없음)")


def _each(key):
    return {s: A[s][key] for s in SIDES}


def test_bust_exists_on_both_sides():
    assert len(SIDES) == 2, f"유방 검출 {SIDES}"


def test_cup_girth_difference_14_to_16_cm():
    _need_bust()
    d = (F["bust_girth"] - F["underbust_girth"]) * 100
    assert 14 <= d <= 16, (f"가슴둘레 {F['bust_girth'] * 100:.1f} cm (y={F['bust_girth_y']:.3f}) - 밑가슴둘레 {F['underbust_girth'] * 100:.1f} cm "
                           f"(y={F['underbust_girth_y']:.3f}) = {d:.1f} cm, 기준 14~16 cm")


def test_breast_volume_350_to_500_cm3():
    _need_bust()
    v = _each("volume_cm3")
    assert all(350 <= x <= 500 for x in v.values()), f"한쪽 부피 {({k: round(x) for k, x in v.items()})} cm3, 기준 350~500"


def test_projection_60_to_80_mm():
    _need_bust()
    p = _each("projection_m")
    assert all(0.060 <= x <= 0.080 for x in p.values()), f"흉벽 대비 최대 돌출 {({k: round(x * 1000, 1) for k, x in p.items()})} mm, 기준 60~80"


def test_upper_pole_volume_fraction_40_to_50_percent():
    _need_bust()
    u = _each("upper_volume_fraction")
    assert all(0.40 <= x <= 0.50 for x in u.values()), f"upper pole 부피 비율 {({k: round(x, 3) for k, x in u.items()})}, 기준 0.40~0.50 (40:60~50:50)"


def test_apex_is_below_breast_mid_height():
    _need_bust()
    r = _each("apex_rel_height")
    h = _each("height_m")
    assert all(x < 0.5 for x in r.values()), (f"최대 돌출점의 상대 높이(밑=0, 위=1) {({k: round(x, 3) for k, x in r.items()})}, 기준 < 0.5. "
                                            f"유방 높이 {({k: round(x * 100, 1) for k, x in h.items()})} cm")


def test_upper_contour_is_straight_or_concave():
    _need_bust()
    d = _each("upper_contour_dev")
    assert all(x <= 0.10 for x in d.values()), f"위쪽 윤곽 볼록도(돌출 대비 현 편차) {({k: round(x, 3) for k, x in d.items()})}, 기준 <= 0.10"


def test_lower_contour_is_convex_and_fuller_than_upper():
    _need_bust()
    lo, up = _each("lower_contour_dev"), _each("upper_contour_dev")
    assert all(lo[s] >= 0.10 and lo[s] - up[s] >= 0.05 for s in SIDES), \
        f"아래 윤곽 볼록도 {({k: round(x, 3) for k, x in lo.items()})} (기준 >= 0.10), 위쪽과의 차 {({s: round(lo[s] - up[s], 3) for s in SIDES})} (기준 >= 0.05)"


def test_inframammary_fold_exists():
    _need_bust()
    lo, up = _each("angle_lower_deg"), _each("angle_upper_deg")
    assert all(lo[s] >= 40 and lo[s] - up[s] >= 8 for s in SIDES), \
        f"아래 윤곽이 흉벽과 만나는 각도 {({k: round(x, 1) for k, x in lo.items()})}° (기준 >= 40°), 위쪽 {({k: round(x, 1) for k, x in up.items()})}° (아래가 8° 이상 가팔라야 함)"


def test_no_sharp_creases_in_bust_region():
    S = F["smoothness"]
    assert S["max_dihedral"] <= 60, f"가슴 부위 인접 면 최대 이면각 {S['max_dihedral']:.1f}° (95% {S['p95_dihedral']:.1f}°, 위치 {S['worst_edge_xyz']}), 기준 <= 60°"


def test_no_single_vertex_cone_spike():
    """[v4] 로우폴리용 재정의. 편차 d(이웃 평균 대비 법선 방향)가 8 mm 넘고 동시에 비율 r=d/이웃 평균 거리가 0.5 넘는 정점이 없어야 한다.
    예전 기준(d <= 8 mm 단독)은 변 길이 40 mm 인 각진 면에서 정상 모서리 정점(판 모서리 17.8 mm)도 실패시켰다. 이유와 반례: bust_eval.spike_stats,
    tests/test_09_bust_measurement_validity.py (단일 정점 돌기는 여전히 잡힘)."""
    _need_bust()
    S = F["smoothness"]
    r = _each("roundness")
    assert S["spike_score"] <= 1.0, (f"스파이크 점수 {S['spike_score']:.2f} (> 1 이면 스파이크): 편차 {S['max_spike'] * 1000:.1f} mm, 비율 {S['max_spike_ratio']:.2f} "
                                  f"(기준 d > 8 mm 이고 r > 0.5) 위치 {S['spike_xyz']}")
    assert all(x >= 0.75 for x in r.values()), f"원뿔도(r=20 mm 원 평균 E/돌출) {({k: round(x, 2) for k, x in r.items()})}, 기준 >= 0.75 (원뿔 약 0.65, 반구 약 0.87)"


def test_cleavage_is_u_not_v():
    _need_bust()
    k = A["midline_curvature"]
    assert k <= 40, f"좌우 유방 사이 중앙 곡률 {k:.0f} /m (곡률반경 {1000 / max(k, 1e-9):.0f} mm), 기준 <= 40 /m (반경 25 mm 이상). V 홈이면 큼"


def test_breasts_are_separated_at_midline():
    """[v2.1] apex 높이에서 x=0 의 흉벽 대비 초과 높이가 15 mm 이하이고 최대 돌출의 30% 이하."""
    _need_bust()
    e = A["cleavage_excess"] * 1000; p = (A["left"]["projection_m"] + A["right"]["projection_m"]) * 500
    assert e <= min(15.0, 0.30 * p), f"x=0 의 흉벽 대비 초과 높이 {e:.1f} mm = 돌출 {p:.1f} mm 의 {e / p * 100:.0f}% (기준 <= {min(15.0, 0.30 * p):.1f} mm). 골이 메워짐"


def test_no_horizontal_band_joining_breasts():
    """[v2.1] 흉벽 대비 20 mm 넘게 솟은 영역이 좌우 apex 사이 x 전 구간을 덮는 행이 없어야 한다 (uniboob)."""
    _need_bust()
    h = A["bridge_height"] * 1000
    assert h <= 4.0, f"좌우 유방을 잇는 가로 띠 높이 {h:.0f} mm (기준 <= 4 mm). 09_bust_profiles.png 오른쪽 히트맵 참조"


def test_no_steps_or_notches_at_lower_chest_edge():
    """[v2.1] 가슴 쉘 하단의 날카로운(>30°) 모서리 개수/총길이가 male 대비 크게 늘지 않아야 한다."""
    n, L = be.lower_rim_sharp_edges("female"); nm, Lm = be.lower_rim_sharp_edges("male")
    assert n <= 20 and L <= 1.5 * Lm + 0.10, f"하단 날카로운 모서리 {n}개 / {L:.2f} m (male {nm}개 / {Lm:.2f} m, 기준 <= 20개, <= {1.5 * Lm + 0.10:.2f} m). 08_bust_closeups.png 하단 사각형 노치"


def test_cleavage_has_no_midline_ridge():
    """유방 사이는 가운데가 가장 낮은 골이어야 한다: x=0 이 좌우 15~45 mm 보다 6 mm 넘게 솟으면 이중 골(W자)이다. 기준 6 mm는 male 값(약 2 mm)보다 크게 잡은 내 휴리스틱."""
    _need_bust()
    r = A["sternum_ridge"] * 1000
    assert r <= 6.0, f"흉골 중앙이 좌우 골보다 {r:.1f} mm 솟음 (이중 골/W자 프로파일, 기준 <= 6 mm). 09_bust_profiles.png 가운데 그래프 참조"


def test_no_new_intersections_with_neighbours():
    """가슴과 상완/허리 밴드 사이에 male 에 없던 교차 삼각형이 0, 배 쉘이 가슴 앞면 밖으로 튀어나오지 않음."""
    sets = chest_partner_sets()
    msg = []
    for cls, (m, f) in sets.items():
        new = f - m
        if new:
            msg.append(f"{cls}: 새로 교차하는 면 {len(new)}개 (male {len(m)} -> female {len(f)})")
    poke, male_poke, vi = abdomen_poke()
    if poke > 0.002:
        msg.append(f"배 쉘 정점 v{vi} 가 가슴 앞면보다 {poke * 1000:.1f} mm 앞으로 튀어나옴 (male {male_poke * 1000:.1f} mm, 기준 <= 2 mm)")
    assert not msg, "; ".join(msg)


def test_left_right_symmetry():
    _need_bust()
    l, r = A["left"], A["right"]
    dv = abs(l["volume_cm3"] / r["volume_cm3"] - 1)
    dp = abs(l["projection_m"] - r["projection_m"]) * 1000
    da = max(abs(abs(l["apex"][0]) - abs(r["apex"][0])), abs(l["apex"][1] - r["apex"][1])) * 1000
    f_max, f_p99 = be.front_asymmetry("female")
    m_max, _ = be.front_asymmetry("male")
    tol = max(2.0, m_max * 1000 + 1.0)  # male 원본 자체의 좌우 높이 차(원본 모델 오차)에 1 mm 여유
    assert dv <= 0.03 and dp <= 2 and da <= 2 and f_max * 1000 <= tol, \
        (f"부피 차 {dv * 100:.1f}% (<=3), 돌출 차 {dp:.1f} mm (<=2), 정점 위치 차 {da:.1f} mm (<=2), "
         f"앞면 높이 좌우 차 최대 {f_max * 1000:.1f} mm (99% {f_p99 * 1000:.1f}, male {m_max * 1000:.1f}, 허용 {tol:.1f})")
