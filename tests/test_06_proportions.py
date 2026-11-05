"""(f) 해부학적 비율. 모든 값은 키(H) 또는 서로의 비로 정규화한다.

기준값 출처와 신뢰도:
 - 머리 7.5~8 head: 과제 지시 + 미술 해부학 캐논. Drillis & Contini(1966)의 머리 높이 0.130H(=7.7 head) 와 일치. [Medium]
 - 어깨폭 0.259H, 엉덩이폭 0.191H, 상완 0.186H, 전완 0.146H, 손 0.108H: Winter, "Biomechanics and Motor Control of
   Human Movement" 4th ed. Fig 4.1 (Drillis & Contini 1966 기반, 성별 구분 없음). 기억에 의존한 수치라 정밀 인용 전 원문 확인 필요. [Medium]
 - 여성 어깨폭(삼각근 폭)/신장 ≈ 0.25, 엉덩이폭/신장 ≈ 0.20~0.22: ANSUR II(2012) 여성 통계를 기억으로 환산한 대략치. [Low]
 - 허리/엉덩이 둘레비 약 0.7: 과제 지시(Singh 1993 의 이상적 WHR 0.7). 일반 성인 여성 분포는 대략 0.67~0.85. [Medium]
 - 허리/가슴 둘레비 0.65~0.85: 일반적 모래시계형 체형(가슴≈엉덩이, 허리 약 70%) 기반 휴리스틱. [Low]
허용 범위는 '스타일화된 마네킹'임을 감안해 넉넉하게 잡았다. 그래도 벗어나면 의도한 것보다 과장된 것이다.
male 은 같은 지표의 대조군(측정 방법 검증용)으로만 출력한다.
"""
import pytest

from qa_metrics import models, proportions, torso_measures


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


def test_shoulders_at_least_as_wide_as_hips(pf, pm):
    r = pf[0]["shoulder_hip_ratio"]
    assert 1.0 <= r <= 1.4, (f"어깨폭/엉덩이폭 = {r:.2f} (shoulder {pf[0]['shoulder_width'] * 100:.1f} cm, hip {pf[0]['hip_width'] * 100:.1f} cm). "
                             f"기준 1.0~1.4. male 대조 {pm[0]['shoulder_hip_ratio']:.2f}")


def test_hip_width_vs_height(pf):
    r = pf[0]["hip_width"] / pf[0]["H"]
    assert 0.18 <= r <= 0.24, f"엉덩이폭/키 = {r:.3f}, 기준 0.18~0.24"


def test_waist_to_hip_girth(pf, pm):
    r = pf[1]["whr"]
    assert 0.65 <= r <= 0.80, (f"허리/엉덩이 둘레비 {r:.2f} (허리 {pf[1]['waist'][0] * 100:.0f} cm @{pf[1]['waist'][1]:.3f}H, "
                               f"엉덩이 {pf[1]['hip'][0] * 100:.0f} cm @{pf[1]['hip'][1]:.3f}H). 기준 0.65~0.80. male 대조 {pm[1]['whr']:.2f}")


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
