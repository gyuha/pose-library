"""(f) 해부학적 비율. 모든 값은 키(H) 또는 서로의 비로 정규화한다.

기준값 출처와 신뢰도:
 - 머리 7.5~8 head: 과제 지시 + 미술 해부학 캐논. Drillis & Contini(1966)의 머리 높이 0.130H(=7.7 head) 와 일치. [Medium]
 - 어깨폭 0.259H, 엉덩이폭 0.191H, 상완 0.186H, 전완 0.146H, 손 0.108H: Winter, "Biomechanics and Motor Control of
   Human Movement" 4th ed. Fig 4.1 (Drillis & Contini 1966 기반, 성별 구분 없음). 기억에 의존한 수치라 정밀 인용 전 원문 확인 필요. [Medium]
 - 여성 어깨폭(삼각근 폭)/신장 ≈ 0.25, 엉덩이폭/신장 ≈ 0.20~0.22: ANSUR II(2012) 여성 통계를 기억으로 환산한 대략치. [Low]
 - [기준 v2] 어깨/엉덩이 폭비 0.95~1.10 (여성): 성인 여성의 견봉 폭(biacromial)/엉덩이 폭(hip breadth)은 대략 0.95~1.05,
   삼각근 폭(bideltoid)/엉덩이 폭은 약 1.1~1.2 라는 ANSUR II 여성 통계의 기억치. 어깨 링 폭은 이 마네킹에서 견봉 폭과 삼각근 폭의
   중간(male 이 키의 0.244 = Winter 0.259 와 ANSUR 남성 견봉 0.22/삼각근 0.265 사이)이라 위 범위를 그대로 쓴다. [Low: 기억 의존, 원문 미확인]
   엉덩이 폭은 0.44~0.56H 높이 단면의 최대 x 폭(둔부~대전자)이며 높이 구간 선택에 민감하다(보고서의 민감도 표 참조).
 - [기준 v2] 허리/엉덩이 둘레비 0.68~0.78: 과제 지시(오케스트레이터). 일반 성인 여성 분포 0.67~0.85 의 안쪽 [Medium], 컨벡스헐 둘레는 줄자보다 크게 나오는 편향이 있다.
 - [기준 v2] 여남 차이 검사: 방향(여성은 키 대비 어깨가 좁고 엉덩이가 넓고 WHR 이 낮다)은 성적 이형성의 확립된 사실 [High],
   크기(어깨 0.94~0.96배, 엉덩이 1.05~1.10배)는 기억치 [Low]라 허용치는 느슨하게 잡은 내 휴리스틱이다.
 - 허리/엉덩이 둘레비 약 0.7: 과제 지시(Singh 1993 의 이상적 WHR 0.7). 일반 성인 여성 분포는 대략 0.67~0.85. [Medium]
 - 허리/가슴 둘레비 0.65~0.85: 일반적 모래시계형 체형(가슴≈엉덩이, 허리 약 70%) 기반 휴리스틱. [Low]
허용 범위는 '스타일화된 마네킹'임을 감안해 넉넉하게 잡았다. 그래도 벗어나면 의도한 것보다 과장된 것이다.
male 은 같은 지표의 대조군(측정 방법 검증용)으로만 출력한다.
"""
import pytest

from qa_metrics import hip_breadth, models, proportions, shoulder_breadth, torso_measures


@pytest.fixture(scope="module")
def pf():
    return proportions(models()[1]), torso_measures(models()[1])


@pytest.fixture(scope="module")
def pm():
    return proportions(models()[0]), torso_measures(models()[0])


def test_head_count(pf):
    assert 7.0 <= pf[0]["heads_tall"] <= 8.0, f"{pf[0]['heads_tall']:.2f} head"


def test_shoulder_width_vs_height(pf, pm):
    p = pf[0]; r = p["shoulder_width"] / p["H"]
    assert 0.22 <= r <= 0.27, (f"어깨 링 바깥폭/키 = {r:.3f} (female {p['shoulder_width'] * 100:.1f} cm / {p['H']:.3f} m). "
                               f"기준 0.22~0.27 (Winter 0.259, 여성 ANSUR≈0.25). male 대조 {pm[0]['shoulder_width'] / pm[0]['H']:.3f}")


def test_shoulder_to_hip_breadth_is_female(pf, pm):
    """[v2] 어깨 링 폭 / 엉덩이 폭 = 0.95~1.10. male 은 이 지표에서 약 1.4 라서 구별된다."""
    f = shoulder_breadth(models()[1]) / hip_breadth(models()[1])[0]
    mm = shoulder_breadth(models()[0]) / hip_breadth(models()[0])[0]
    hb = hip_breadth(models()[1])
    assert 0.95 <= f <= 1.10, (f"어깨/엉덩이 폭비 {f:.2f} (어깨 {shoulder_breadth(models()[1]) * 100:.1f} cm, 엉덩이 {hb[0] * 100:.1f} cm @{hb[1]:.3f}H). "
                               f"기준 0.95~1.10, male 대조 {mm:.2f}")


def test_hip_width_vs_height(pf):
    r = pf[0]["hip_width"] / pf[0]["H"]
    assert 0.18 <= r <= 0.24, f"엉덩이폭/키 = {r:.3f}, 기준 0.18~0.24"


def test_waist_to_hip_girth(pf, pm):
    r = pf[1]["whr"]
    assert 0.68 <= r <= 0.78, (f"허리/엉덩이 둘레비 {r:.2f} (허리 {pf[1]['waist'][0] * 100:.0f} cm @{pf[1]['waist'][1]:.3f}H, "
                               f"엉덩이 {pf[1]['hip'][0] * 100:.0f} cm @{pf[1]['hip'][1]:.3f}H). 기준 0.68~0.78. male 대조 {pm[1]['whr']:.2f}")


@pytest.mark.skip(reason="폐기(오케스트레이터 결정): 가슴이 없던 때의 휴리스틱이라 가슴 추가 후 가슴둘레에 유방이 포함되어 의미가 없다. test_08_bust.py 의 가슴-밑가슴 둘레 차이 검사가 대체한다.")
def test_waist_to_bust_girth(pf, pm):
    r = pf[1]["waist_bust"]
    assert 0.65 <= r <= 0.85, f"허리/가슴 둘레비 {r:.2f}, 기준 0.65~0.85. male 대조 {pm[1]['waist_bust']:.2f}"


def test_waist_girth_vs_height(pf, pm):
    """허리 둘레/키. 여성은 남성 비율의 약 90~100% (ANSUR 기억치 기반 [Low])."""
    f = pf[1]["waist"][0] / pf[0]["H"]; m = pm[1]["waist"][0] / pm[0]["H"]
    assert 0.85 * m <= f <= 1.05 * m, f"female {f:.3f} vs male {m:.3f} (비 {f / m:.2f}); 허용 0.85~1.05"


@pytest.mark.parametrize("key,ref", [("upper_arm_len", 0.186), ("forearm_len", 0.146), ("hand_len", 0.108)])
def test_arm_segments_vs_winter(pf, key, ref):
    r = pf[0][key] / pf[0]["H"]
    assert abs(r / ref - 1) <= 0.25, f"{key}/H={r:.3f} vs Winter {ref} (허용 ±25%)"


@pytest.mark.parametrize("key,ref", [("thigh_len", 0.245), ("shin_len", 0.246)])
def test_leg_segments_vs_winter(pf, key, ref):
    r = pf[0][key] / pf[0]["H"]
    assert abs(r / ref - 1) <= 0.25, f"{key}/H={r:.3f} vs Winter {ref} (허용 ±25%). 관절 링 중심 기준 근사"


@pytest.mark.parametrize("key", ["upper_arm_len", "forearm_len", "hand_len", "thigh_len", "shin_len", "knee_height",
                                 "hip_joint_height", "chin_height", "foot_length"])
def test_vertical_and_limb_ratios_not_changed_by_morph(pf, pm, key):
    """모프가 키 대비 사지/수직 비율을 male 에서 ±8% 이상 바꾸지 않았는가 (바뀌었다면 모프가 도입한 비율 변화)."""
    f = pf[0][key] / pf[0]["H"]; m = pm[0][key] / pm[0]["H"]
    assert abs(f / m - 1) <= 0.08, f"{key}: female {f:.3f} / male {m:.3f} = {f / m:.2f}"


# --------------------------------------------------------------------------- [v2] 여성 특징이 male 과 구분되는가
def _norm(model):
    H = proportions(model)["H"]
    return {"shoulder": shoulder_breadth(model) / H, "hip": hip_breadth(model)[0] / H,
            "waist": torso_measures(model)["waist"][0] / H, "whr": torso_measures(model)["whr"]}


def test_dimorphism_shoulder_narrower_than_male():
    f, m = _norm(models()[1]), _norm(models()[0])
    r = f["shoulder"] / m["shoulder"]
    assert 0.80 <= r <= 0.97, f"키 정규화 어깨폭 female/male = {r:.2f} (female {f['shoulder']:.3f}H, male {m['shoulder']:.3f}H), 허용 0.80~0.97"


def test_dimorphism_hips_wider_than_male():
    f, m = _norm(models()[1]), _norm(models()[0])
    r = f["hip"] / m["hip"]
    assert 1.08 <= r <= 1.45, f"키 정규화 엉덩이폭 female/male = {r:.2f} (female {f['hip']:.3f}H, male {m['hip']:.3f}H), 허용 1.08~1.45"


def test_dimorphism_waist_hip_ratio_lower_than_male():
    f, m = _norm(models()[1]), _norm(models()[0])
    assert m["whr"] - f["whr"] >= 0.08, f"WHR 차 (male - female) = {m['whr'] - f['whr']:.2f} (male {m['whr']:.2f}, female {f['whr']:.2f}), 기준 0.08 이상"


def test_dimorphism_shoulder_hip_ratio_gap():
    fm, mm = models()[1], models()[0]
    f = shoulder_breadth(fm) / hip_breadth(fm)[0]; m = shoulder_breadth(mm) / hip_breadth(mm)[0]
    assert m - f >= 0.20, f"어깨/엉덩이 폭비 차 (male - female) = {m - f:.2f} (male {m:.2f}, female {f:.2f}), 기준 0.20 이상"
