"""각 포즈가 rig/male.glb, rig/female.glb 모두에 적용되는지 검사 (S2).

- 모르는 뼈 없음: 포즈의 뼈 이름 ⊂ 스켈레톤 규칙(53개) ⊂ 모델 skin joints.
- 루트 이동은 hipsHeight 비율: pelvis 전역 위치 == rest 위치 + translation × 대상 모델의 골반 높이.
- 스키닝 결과가 유한하고(NaN/inf 없음) 몸이 터무니없이 늘어나지 않는다.
- 바닥 접지(아래 규칙). 바닥은 y = 0.

바닥 허용오차 선택과 근거
  FLOOR_TOL = 10 mm (바닥 아래로 가라앉는 한도, 바닥 위로 뜨는 한도 둘 다).
  - 실측 기준: pose_01 의 최저 정점은 female -0.02 mm, male -3.65 mm (rig/README.md 도 male 3.7 mm 가라앉음을 기록).
    male 은 female 에 맞춘 포즈를 골반 높이 비율로 옮기므로 몇 mm 의 오차는 구조적이다.
  - 10 mm 는 연락 시트(800 px ≈ 1.9 m)에서 약 4 px 이고 신장의 0.6 %: 눈에 띄는 공중 부양/발 박힘이 아닌 정도.
  분류별 규칙 (분류는 poses/catalog.ko.json 의 태그, 카탈로그가 없으면 '알 수 없음'):
  - 서기: 가장 낮은 발바닥(foot_*/ball_* 지배 정점)이 [-tol, +tol] 안 — 최저 발바닥이 바닥에 닿는다.
          (한 발만 닿는 콘트라포스토/뒤꿈치 든 포즈 때문에 '두 발 모두'가 아니라 '가장 낮은 발'.)
  - 앉기: 몸 전체 최저 정점이 [-tol, +tol] 안. 앉을 곳(의자)은 없으므로 바닥에 앉든 발이 닿든 가장 낮은 곳이 바닥이어야 한다.
  - 동작: 점프 같은 공중 동작이 있을 수 있으므로 가라앉지만 않으면 된다(최저 정점 ≥ -tol). 단 신장의 절반(0.9 m) 넘게 뜨면 안 된다.
  - 분류 미상(카탈로그 없음): 앉기 규칙(몸 전체 최저 정점이 [-tol, +tol])을 적용한다. 서기 포즈도 이를 만족한다.
"""
import numpy as np
import pytest

from pose_helpers import MODELS, POSES_DIR, category_of, model, pose_ids, posed, rigcore
import json

FLOOR_TOL = 0.010   # m
MAX_AIRBORNE = 0.9  # m, 동작 포즈의 최대 허용 이격(상한 방어선)
STRETCH_MAX = 2.2   # 포즈 상태 전체 높이 / 신장 상한: 스키닝 폭주(정점이 날아감) 방어선

PARAMS = [pytest.param(m, p, id=f"{m}-{p}") for p in pose_ids() for m in MODELS]


def _raw(pose_id):
    return json.loads((POSES_DIR / f"{pose_id}.json").read_text())


@pytest.mark.parametrize("name,pose_id", PARAMS)
def test_no_unknown_bones(name, pose_id):
    skin_joints = [model(name).gltf["nodes"][j]["name"] for j in model(name).gltf["skins"][0]["joints"]]
    unknown = sorted(set(_raw(pose_id)["bones"]) - set(rigcore.BONES))
    assert not unknown, f"스켈레톤에 없는 뼈: {unknown}"
    assert not (set(_raw(pose_id)["bones"]) - set(skin_joints)), f"{name}.glb skin 에 없는 뼈"


@pytest.mark.parametrize("name,pose_id", PARAMS)
def test_root_translation_resolved_by_hips_height(name, pose_id):
    raw = _raw(pose_id)
    assert raw["root"]["unit"] == "hipsHeight"
    m = model(name)
    pose = rigcore.pose_for(m.skeleton, rigcore.load_pose(POSES_DIR / f"{pose_id}.json"))
    expect = np.array(raw["root"]["translation"]) * m.skeleton.hips_height
    assert np.allclose(pose["root_offset"], expect)
    pelvis = m.skeleton.pose_globals(pose)[rigcore.INDEX["pelvis"]][:3, 3]
    assert np.allclose(pelvis, m.skeleton.heads["pelvis"] + expect, atol=1e-9)


@pytest.mark.parametrize("name,pose_id", PARAMS)
def test_pose_applies_finite_and_sane(name, pose_id):
    V = posed(name, pose_id)
    assert V.shape == model(name).pos.shape and np.isfinite(V).all()
    extent = V.max(0) - V.min(0)
    rest_h = np.ptp(model(name).pos[:, 1])
    assert extent.max() < STRETCH_MAX * rest_h, f"포즈 상태 최대 범위 {extent.max():.2f} m (rest 신장 {rest_h:.2f} m)"


def _lowest_sole(name, V):
    sole = np.isin(model(name).dominant_bone(), ["foot_l", "foot_r", "ball_l", "ball_r"])
    return float(V[sole, 1].min())


@pytest.mark.parametrize("name,pose_id", PARAMS)
def test_floor_contact(name, pose_id):
    V = posed(name, pose_id)
    low, cat = float(V[:, 1].min()), category_of(pose_id)
    if cat == "서기":
        sole = _lowest_sole(name, V)
        assert -FLOOR_TOL <= sole <= FLOOR_TOL, f"최저 발바닥 y = {sole * 1e3:.1f} mm (허용 ±{FLOOR_TOL * 1e3:.0f} mm)"
        assert low >= -FLOOR_TOL, f"몸 최저 y = {low * 1e3:.1f} mm 가 바닥 아래"
    elif cat == "동작":
        assert low >= -FLOOR_TOL, f"몸 최저 y = {low * 1e3:.1f} mm 가 바닥 아래"
        assert low <= MAX_AIRBORNE, f"몸 최저 y = {low:.2f} m 공중"
    else:  # 앉기, 또는 카탈로그 없음/분류 미상
        assert -FLOOR_TOL <= low <= FLOOR_TOL, f"몸 최저 y = {low * 1e3:.1f} mm (허용 ±{FLOOR_TOL * 1e3:.0f} mm)"
