"""포즈 테스트(test_10~12) 공용 헬퍼. rig/ 는 읽기 전용으로 import 만 한다(rig/ 에는 아무것도 쓰지 않는다).

rig/tools/rigcore.py, rig/tools/check_penetration.py 는 import 시 부작용이 없다(함수·상수 정의뿐, 쓰기는 main() 안).
"""
import functools
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
POSES_DIR = ROOT / "poses"
RIG_DIR = ROOT / "rig"
ARTIFACTS = Path(__file__).resolve().parent / "artifacts"
MODELS = ("female", "male")

sys.path.insert(0, str(RIG_DIR / "tools"))
import check_penetration as cp  # noqa: E402  (read-only import)
import rigcore  # noqa: E402
import render_pose  # noqa: E402

CATEGORY_TAGS = ("서기", "앉기", "동작")


def pose_paths():
    return sorted(POSES_DIR.glob("pose_*.json"))


def pose_ids():
    return [p.stem for p in pose_paths()]


def load_catalog():
    """catalog.ko.json 의 {id: entry}. 파일이 없으면 None (S3 에서 poser 가 만든다)."""
    p = POSES_DIR / "catalog.ko.json"
    if not p.exists():
        return None
    return {e["id"]: e for e in json.loads(p.read_text(encoding="utf-8")).get("poses", [])}


def category_of(pose_id):
    cat = load_catalog()
    if not cat or pose_id not in cat:
        return None
    found = [t for t in cat[pose_id].get("tags", []) if t in CATEGORY_TAGS]
    return found[0] if len(found) == 1 else None


@functools.lru_cache(maxsize=None)
def model(name):
    return rigcore.RigModel(RIG_DIR / f"{name}.glb")


@functools.lru_cache(maxsize=None)
def posed(name, pose_id):
    """(정점 위치 배열) — 스키닝 결과. 루트 이동은 모델 골반 높이로 환산(rigcore.pose_for)."""
    m = model(name)
    pose = rigcore.load_pose(POSES_DIR / f"{pose_id}.json")
    return m.skeleton.skin(rigcore.pose_for(m.skeleton, pose), m.pos, m.joints, m.weights)


@functools.lru_cache(maxsize=None)
def parts(name):
    return cp.Parts(model(name))


# check_penetration.PAIRS 에서 'hidden'(어깨 필러: 설계상 가슴 안쪽에 있음)은 뺀다.
# 앉기·동작 포즈를 위해 다리-몸통, 손-다리, 왼팔-골반 쌍을 추가한다.
EXTRA_PAIRS = [
    ("leg_l", "torso", "avoid"), ("leg_r", "torso", "avoid"),
    ("hand_l", "leg_l", "avoid"), ("hand_l", "leg_r", "avoid"), ("hand_r", "leg_l", "avoid"),
    ("upperarm_l", "pelvis", "avoid"), ("lowerarm_l", "pelvis", "avoid"), ("hand_l", "pelvis", "avoid"),
]
PAIRS = [p for p in cp.PAIRS if p[2] != "hidden"] + EXTRA_PAIRS


@functools.lru_cache(maxsize=None)
def rest_measure(name, a, b):
    m = model(name)
    return parts(name).measure(m.pos, a, b)


def penetration(name, pose_id):
    """{ 'A~B': {pose, rest, new_depth_mm, new_inside} } — rest 대비 새로 생긴 관통만 본다."""
    V = posed(name, pose_id)
    out = {}
    for a, b, kind in PAIRS:
        r_pose = parts(name).measure(V, a, b)
        r_rest = rest_measure(name, a, b)
        out[f"{a}~{b}"] = {
            "kind": kind, "pose": r_pose, "rest": r_rest,
            "new_depth_mm": round(max(0.0, r_pose["max_depth_mm"] - r_rest["max_depth_mm"]), 2),
            "new_inside": r_pose["inside_vertices"] - r_rest["inside_vertices"],
        }
    return out
