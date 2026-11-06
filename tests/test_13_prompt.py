"""prompt/ 엔진 ↔ 포즈 파일 ↔ 카탈로그 교차 계약 검사 (S5). prompt/ 자체 단위 테스트는 중복하지 않는다.

node 로 scripts/run_prompt_cases.mjs 를 한 번 호출해(배치) 포즈 수 × 2성별 × 5앵글 조합을 모두 검사한다(포즈 8개면 80조합).
"""
import json
import subprocess

import pytest

from pose_helpers import MODELS, POSES_DIR, ROOT, load_catalog, pose_ids

LABELS = ["인물", "앵글", "자세", "몸통", "팔", "다리", "체중", "시선"]
ANGLES = ["front", "side", "three_quarter", "high", "low"]
GENDER_PHRASE = {"female": "여성 인물", "male": "남성 인물"}
BRIDGE = ROOT / "scripts" / "run_prompt_cases.mjs"


def _node(cases):
    p = subprocess.run(["node", str(BRIDGE)], input=json.dumps(cases), capture_output=True, text=True, timeout=60)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)


def _pose(pid):
    return json.loads((POSES_DIR / f"{pid}.json").read_text())


@pytest.fixture(scope="module")
def env():
    catalog = load_catalog()
    assert catalog, "poses/catalog.ko.json 이 필요하다"
    ids = pose_ids()
    assert len(ids) >= 8, f"포즈 {len(ids)}개 (8개 이상이어야 함)"
    combos = [(pid, g, a) for pid in ids for g in MODELS for a in ANGLES]
    cases = [{"pose": _pose(pid), "catalogEntry": catalog[pid], "gender": g, "angle": a} for pid, g, a in combos]
    out = _node(cases + cases)  # 두 번 호출한 결과 비교(결정성)
    n = len(cases)
    return {"catalog": catalog, "combos": combos, "angles": out["angles"],
            "first": out["results"][:n], "second": out["results"][n:]}


def test_all_combinations_count(env):
    assert len(env["combos"]) == len(pose_ids()) * len(MODELS) * len(ANGLES)


def test_angle_presets_keys(env):
    assert set(env["angles"]) == set(ANGLES)
    for k, v in env["angles"].items():
        assert v["phrase"].strip() and v["label"].strip(), k


def test_all_combinations_contract(env):
    problems = []
    for (pid, g, a), r in zip(env["combos"], env["first"]):
        tag = f"{pid}/{g}/{a}"
        if not r["ok"]:
            problems.append(f"{tag}: 예외 {r['error']}")
            continue
        lines = r["text"].split("\n")
        if len(lines) != 8:
            problems.append(f"{tag}: {len(lines)}줄")
            continue
        for i, (label, line) in enumerate(zip(LABELS, lines)):
            prefix = f"{label}: "
            if not line.startswith(prefix):
                problems.append(f"{tag}: {i + 1}번째 줄 레이블 {line[:12]!r} (기대 {label}:)")
            elif not line[len(prefix):].strip():
                problems.append(f"{tag}: {label} 내용이 비어 있음")
        body = {lbl: ln[len(lbl) + 2:] for lbl, ln in zip(LABELS, lines)}
        if body["자세"] != env["catalog"][pid]["description"]:
            problems.append(f"{tag}: 자세 != 카탈로그 정식 설명")
        if GENDER_PHRASE[g] not in body["인물"]:
            problems.append(f"{tag}: 인물에 {GENDER_PHRASE[g]!r} 없음 ({body['인물']!r})")
        if body["앵글"] != env["angles"][a]["phrase"]:
            problems.append(f"{tag}: 앵글 != ANGLE_PRESETS.phrase")
    assert not problems, f"{len(problems)}건\n" + "\n".join(problems[:15])


def test_deterministic(env):
    assert env["first"] == env["second"]


def test_invalid_inputs_raise():
    cat = load_catalog()
    pid = pose_ids()[0]
    pose, entry = _pose(pid), cat[pid]
    other = next(e for i, e in cat.items() if i != pid)
    out = _node([
        {"pose": pose, "catalogEntry": entry, "gender": "other", "angle": "front"},
        {"pose": pose, "catalogEntry": entry, "gender": "female", "angle": "diagonal"},
        {"pose": pose, "catalogEntry": other, "gender": "female", "angle": "front"},
        {"pose": pose, "catalogEntry": entry, "gender": "female", "angle": "front"},  # 대조군: 정상
    ])["results"]
    assert [r["ok"] for r in out] == [False, False, False, True], out
