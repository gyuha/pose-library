"""포즈 파일·카탈로그 형식 검사 (S2, TDD: 포즈 7개와 카탈로그는 이후 슬라이스에서 생긴다).

- 모든 poses/pose_*.json 이 poses/schema.json 에 맞고, meta.id == 파일명, 쿼터니언 단위 길이,
  three.js Euler XYZ 분해 값이 rig/joint_limits.json 범위 안(허용오차 0.05°, check_limits.py 와 같은 의미)이다.
- 포즈는 8개 이상이다.
- poses/catalog.ko.json 이 poses/catalog.schema.json 에 맞고, 카탈로그 id 집합 == 포즈 파일 id 집합이다.
  카탈로그 형태: {"formatVersion": 1, "poses": [{id, name(한국어), tags(비어있지 않은 한국어 문자열 ≥1),
  description(한국어 정식 설명 1~2문장)}]}. 태그에는 분류 태그(서기/앉기/동작)가 정확히 하나, 개수는 3·2·3.
"""
import collections
import json
import re

import jsonschema
import numpy as np
import pytest

from pose_helpers import CATEGORY_TAGS, POSES_DIR, RIG_DIR, load_catalog, pose_paths, rigcore
import check_limits  # rig/tools (read-only import; main() 이 rig/ 에 쓰므로 호출하지 않는다)

HANGUL = re.compile(r"[가-힣]")
LIMIT_TOL_DEG = 0.05   # check_limits.TOL 과 같은 의미
MIN_POSES = 8
EXPECTED_CATEGORY_COUNTS = {"서기": 3, "앉기": 2, "동작": 3}

POSE_PARAMS = [pytest.param(p, id=p.stem) for p in pose_paths()]
SCHEMA = json.loads((POSES_DIR / "schema.json").read_text())
LIMITS = json.loads((RIG_DIR / "joint_limits.json").read_text())


def test_pose_count_at_least_8():
    assert len(pose_paths()) >= MIN_POSES, f"포즈 파일 {len(pose_paths())}개 < {MIN_POSES}"


@pytest.mark.parametrize("path", POSE_PARAMS)
def test_pose_matches_schema(path):
    d = json.loads(path.read_text())
    errs = [f"{e.message} at {list(e.absolute_path)}" for e in jsonschema.Draft202012Validator(SCHEMA).iter_errors(d)]
    assert not errs, errs[:5]


@pytest.mark.parametrize("path", POSE_PARAMS)
def test_meta_id_equals_file_stem(path):
    assert json.loads(path.read_text())["meta"]["id"] == path.stem


@pytest.mark.parametrize("path", POSE_PARAMS)
def test_quaternions_unit_length(path):
    bad = {}
    for b, v in json.loads(path.read_text())["bones"].items():
        n = float(np.linalg.norm(v["quaternion"]))
        if abs(n - 1) > 1e-4:
            bad[b] = n
    assert not bad, bad


@pytest.mark.parametrize("path", POSE_PARAMS)
def test_euler_within_joint_limits(path):
    """check_limits.check_pose: 단위 길이, euler/쿼터니언 일치(0.05°), XYZ Euler 한계(±0.05°), 모르는 뼈 없음."""
    _, errors = check_limits.check_pose(path, LIMITS)
    assert not errors, errors[:5]


def test_limits_tolerance_matches_check_limits():
    assert check_limits.TOL == LIMIT_TOL_DEG


# ---------------------------------------------------------------- catalog
CATALOG_PATH = POSES_DIR / "catalog.ko.json"
CATALOG_SCHEMA_PATH = POSES_DIR / "catalog.schema.json"


def _catalog():
    assert CATALOG_PATH.exists(), "poses/catalog.ko.json 이 없다 (S3 poser 작업)"
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def test_catalog_matches_schema():
    assert CATALOG_SCHEMA_PATH.exists(), "poses/catalog.schema.json 이 없다 (S3 poser 작업)"
    schema = json.loads(CATALOG_SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    errs = [f"{e.message} at {list(e.absolute_path)}" for e in jsonschema.Draft202012Validator(schema).iter_errors(_catalog())]
    assert not errs, errs[:5]


def test_catalog_shape():
    """스키마가 느슨해도 기대 형태를 직접 확인한다."""
    c = _catalog()
    assert c.get("formatVersion") == 1
    assert isinstance(c.get("poses"), list) and c["poses"]
    for e in c["poses"]:
        assert {"id", "name", "tags", "description"} <= set(e), e.get("id")
        assert isinstance(e["id"], str) and re.fullmatch(r"[a-z0-9_]+", e["id"])
        assert isinstance(e["name"], str) and HANGUL.search(e["name"]), f"{e['id']}: name 은 한국어"
        assert isinstance(e["tags"], list) and len(e["tags"]) >= 1, f"{e['id']}: tags 비어 있음"
        for t in e["tags"]:
            assert isinstance(t, str) and t.strip() and HANGUL.search(t), f"{e['id']}: tag {t!r} 는 한국어"
        assert len(set(e["tags"])) == len(e["tags"]), f"{e['id']}: tags 중복"
        d = e["description"]
        assert isinstance(d, str) and d.strip() and HANGUL.search(d), f"{e['id']}: description 은 한국어"
        n_sent = len(re.findall(r"[.!?。](?:\s|$)", d.strip())) or 1
        assert 1 <= n_sent <= 2, f"{e['id']}: description {n_sent}문장 (1~2문장이어야 함)"


def test_catalog_ids_unique_and_equal_pose_file_ids():
    c = _catalog()
    ids = [e["id"] for e in c["poses"]]
    assert len(ids) == len(set(ids)), "카탈로그 id 중복"
    files = {p.stem for p in pose_paths()}
    assert set(ids) == files, f"카탈로그에만: {sorted(set(ids) - files)}, 포즈 파일에만: {sorted(files - set(ids))}"


def test_catalog_exactly_one_category_tag_each():
    for e in _catalog()["poses"]:
        cats = [t for t in e["tags"] if t in CATEGORY_TAGS]
        assert len(cats) == 1, f"{e['id']}: 분류 태그 {cats} (정확히 하나여야 함: {CATEGORY_TAGS})"


def test_catalog_category_counts():
    _catalog()
    counts = collections.Counter(t for e in _catalog()["poses"] for t in e["tags"] if t in CATEGORY_TAGS)
    # 1/2 계획의 구성(서기 3 · 앉기 2 · 동작 3)은 최소값이다. image-to-pose 스킬로 포즈가 늘어날 수 있다.
    assert all(counts[k] >= v for k, v in EXPECTED_CATEGORY_COUNTS.items()), dict(counts)
