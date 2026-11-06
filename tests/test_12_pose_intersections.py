"""포즈 메시 관통 검사 + 사람 확인용 컨택트 시트 (S2).

방법: rig/tools/check_penetration.py 의 Parts.measure(닫힌 쉘 안쪽 정점 수·깊이)를 import 해서 쓴다(결과는 tests/ 에만 쓴다).
부위 쌍은 그쪽 PAIRS 에서 'hidden'(어깨 필러: 설계상 가슴 안쪽)을 빼고, 다리-몸통·손-다리·왼팔-골반 쌍을 추가했다(pose_helpers.PAIRS).
지표: new_depth_mm = max(0, 포즈 최대 침투 깊이 − rest 최대 침투 깊이). rest 에 이미 있는 겹침(팔 쉘이 몸통과 겹침 등)은 뺀다.

임계값 (pose_01 실측을 기준치로 삼아 정함)
  pose_01 실측(new_depth_mm): 거의 모든 쌍 0. 예외만 기록한다.
    female: upperarm_l~torso 8.05, upperarm_r~torso 49.38   (hand_l~head 접촉 inside 3 정점, 깊이 0)
    male  : upperarm_l~torso 5.68, upperarm_r~torso 51.18
  - PAIR_MAX_NEW_DEPTH_MM = 25: 일반 쌍. 25 mm 는 손가락 두께(약 15~20 mm)보다 깊은 침투로 컨택트 시트에서 확연히 보인다.
    pose_01 은 이 값 아래에서 모든 일반 쌍이 0 이다.
  - SHOULDER_MAX_NEW_DEPTH_MM = 60: 'upperarm_*~torso' 쌍만 완화. 이 쌍의 upperarm 쉘에는 어깨 관절 구(Joints 재질)가 들어 있고,
    LBS 에서 팔을 들거나 돌리면 이 구가 가슴 쉘 안쪽으로 묻힌다(옷 속에 어깨가 들어가는 모양, 겉으로는 안 보임).
    pose_01 이 49.4/51.2 mm 라서 최악값 + 약 15 % 로 잡았다. **이 값은 pose_01 에서 보정한 회귀 방어선이지 해부학적 허용치가 아니다.**
    pose_01 자체의 오른어깨 49~51 mm 는 발견 사항으로 보고한다(리거/포저가 어깨 구 가중치나 포즈를 개선하면 낮춰야 함).
  접촉은 허용한다(contact 쌍: 깊이 0 에 inside 정점 몇 개). 접촉 의도 여부는 사람이 컨택트 시트로 본다.
"""
import pytest
from PIL import Image, ImageDraw

from pose_helpers import ARTIFACTS, MODELS, model, parts, pose_ids, pose_paths, posed, penetration, render_pose, rigcore

PAIR_MAX_NEW_DEPTH_MM = 25.0
SHOULDER_MAX_NEW_DEPTH_MM = 60.0
SHOULDER_PAIRS = {"upperarm_l~torso", "upperarm_r~torso"}

PARAMS = [pytest.param(m, p, id=f"{m}-{p}") for p in pose_ids() for m in MODELS]


@pytest.mark.parametrize("name,pose_id", PARAMS)
def test_no_deep_new_penetration(name, pose_id):
    rows = penetration(name, pose_id)
    bad = {}
    for k, r in rows.items():
        limit = SHOULDER_MAX_NEW_DEPTH_MM if k in SHOULDER_PAIRS else PAIR_MAX_NEW_DEPTH_MM
        if r["new_depth_mm"] > limit:
            bad[k] = f"새 침투 {r['new_depth_mm']} mm > {limit} mm (inside +{r['new_inside']})"
    assert not bad, bad


# ---------------------------------------------------------------- contact sheet (사람 확인용)
CELL = (300, 400)   # 렌더(600x800)를 절반으로 줄인 칸
VIEWS = ("front", "three_quarter")
PER_ROW = 2         # 한 줄에 포즈 2개(포즈당 정면+사선 = 4칸)
LABEL_H = 18


def _render_cell(name, pose_id, view):
    m = model(name)
    scale = m.skeleton.hips_height / render_pose.FEMALE_HIPS
    img = render_pose.render(posed(name, pose_id), m.tri, m.tri_mat, parts_ids(name), view, scale)
    return render_pose.floor_line(img, view, scale).resize(CELL, Image.LANCZOS)


_PART_IDS = {}


def parts_ids(name):
    if name not in _PART_IDS:
        _PART_IDS[name] = render_pose.part_ids(model(name))
    return _PART_IDS[name]


def make_contact_sheet(name):
    ids = pose_ids()
    rows = -(-len(ids) // PER_ROW)
    cw, ch = CELL
    sheet = Image.new("RGB", (PER_ROW * len(VIEWS) * cw, rows * (ch + LABEL_H)), "white")
    draw = ImageDraw.Draw(sheet)
    for i, pid in enumerate(ids):
        x0, y0 = (i % PER_ROW) * len(VIEWS) * cw, (i // PER_ROW) * (ch + LABEL_H)
        draw.text((x0 + 4, y0 + 3), f"{name} | {pid} | front, three_quarter", fill=(20, 20, 20))
        for j, view in enumerate(VIEWS):
            sheet.paste(_render_cell(name, pid, view), (x0 + j * cw, y0 + LABEL_H))
    return sheet


@pytest.mark.parametrize("name", MODELS)
def test_write_contact_sheet(name):
    """모든 포즈의 정면+사선 시트를 tests/artifacts/ 에 쓴다(rig/ 에는 쓰지 않는다). 사람이 눈으로 확인한다."""
    ARTIFACTS.mkdir(exist_ok=True)
    out = ARTIFACTS / f"pose_contact_sheet_{name}.png"
    make_contact_sheet(name).save(out)
    img = Image.open(out)
    assert img.width == PER_ROW * len(VIEWS) * CELL[0] and img.height >= CELL[1]
    assert len(pose_paths()) >= 1
