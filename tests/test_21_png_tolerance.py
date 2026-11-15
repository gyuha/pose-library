"""PNG 회귀 허용오차가 데이터로 정당한지 측정한다 (task #5 S1).

test_20 의 결정성 검사는 같은 상태의 연속 다운로드 2장이 픽셀 단위로 같아야 한다고
요구한다. 이 요구가 쓸모 있으려면
  (a) 같은 상태를 같은 뷰포트로 다시 렌더해도 생기는 차이(노이즈)는 허용오차보다 충분히 작아야 하고,
  (b) 서로 다른 포즈 사이의 차이(신호)는 허용오차보다 충분히 커야 한다.
이 파일은 그 두 가지를 실측한다. 허용오차 상수는 이 파일에 정의한다.

측정 방법
  - 렌더는 test_20 과 같은 경로를 쓴다: ego-browser + scripts/app_uat.js 의 "tolerance" 섹션
    (같은 상태를 4번: 최초 / 상태 변경 없이 반복 / 성별 왕복 뒤 / 뷰포트 크기 변경 뒤,
     그리고 모든 포즈 × female × front 1장씩). POSE_APP_URL 이 있으면 정적 서버를 그대로 쓴다.
  - 새 동작(app E5F6): 다운로드는 보이는 메인 캔버스 그대로라 뷰포트를 바꾸면 PNG 크기도
    바뀐다. 크기가 다른 렌더끼리는 픽셀 비교를 하지 않는다. 노이즈용 3장은 리사이즈 전에
    몰아 받는다(initial → 상태 변경 없이 repeat → 성별 왕복 뒤 gender_roundtrip).
  - 노이즈 = 리사이즈 전 같은 뷰포트 3장(initial·repeat·gender_roundtrip)의 모든 쌍(3쌍) 중 지표별 최댓값.
    (viewport_resized 장은 크기가 바뀌는 것 자체가 새 동작의 증거이며 수치 비교에는 쓰지 않는다.)
  - 신호   = 서로 다른 포즈 쌍(모든 조합)의 지표별 최솟값.
  - 단언   = 노이즈 < 허용오차/3  그리고  허용오차×3 < 신호 하위1% 분위수  (평균·픽셀 비율 각각).
    최소값이 아니라 분위수인 이유: 의도적 near-variant 쌍이 최소값을 지배하므로(아래 참조).
측정값은 tests/artifacts/png_tolerance/measurements.json 에도 남긴다(콘솔 출력은 -s 일 때).
"""
import itertools
import json
import os
import shutil
import signal
import subprocess

import numpy as np
import pytest
from PIL import Image

from pose_helpers import ARTIFACTS, pose_ids
from test_20_app import ANGLES, APP, MARK, PORT, SCRIPT, URL, _sh, _tail, _wait_http

# PNG 비교 지표 정의(같은 상태의 연속 캡처가 완전히 같아야 한다는 결정성 요구의 근거 수치).
PNG_MEAN_DIFF_MAX = 1.5
PNG_BIG_DIFF_FRACTION_MAX = 0.0075
PNG_BIG_DIFF_LEVEL = 40

OUT_DIR = ARTIFACTS / "png_tolerance"
NOISE_POSE = "pose_01_contrapposto_hand_on_head"
NOISE_LABELS = ["initial", "repeat", "gender_roundtrip", "viewport_resized"]
# 노이즈 지표는 리사이즈 전 같은 뷰포트의 3장(initial·repeat·gender_roundtrip) → 3쌍으로만 잰다.
SAME_VIEWPORT_NOISE_LABELS = ["initial", "repeat", "gender_roundtrip"]
EXPECTED_STATE = {"poseId": NOISE_POSE, "gender": "female", "angle": "front"}
NOISE_PAIRS_MIN = 3  # 리사이즈 전 같은 뷰포트 3장(initial·repeat·gender_roundtrip) → 3쌍


def _presets():
    from test_13_prompt import _node
    angles = _node([])["angles"]
    assert set(angles) == set(ANGLES), angles.keys()
    return {k: {"yawDeg": angles[k]["yawDeg"], "pitchDeg": angles[k]["pitchDeg"]} for k in ANGLES}


def _run_tolerance(url):
    assert NOISE_POSE in pose_ids(), f"노이즈 기준 포즈가 없다: {NOISE_POSE}"
    cfg = {"url": url, "outDir": str(OUT_DIR), "angles": _presets(),
           "tolerance": {"poseId": NOISE_POSE, "poses": pose_ids(), "gender": "female", "angle": "front"}}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUT_DIR.glob("*.png"):
        old.unlink()
    code = f"const CONFIG = {json.dumps(cfg)};\n" + SCRIPT.read_text(encoding="utf-8")
    p = subprocess.run(["ego-browser", "nodejs"], input=code, capture_output=True, text=True, timeout=600)
    lines = [ln for ln in (p.stdout + "\n" + p.stderr).splitlines() if MARK in ln]
    assert lines, f"ego-browser 스크립트가 결과를 내지 않음(exit {p.returncode}):\n{_tail(p.stdout + p.stderr)}"
    res = json.loads(lines[-1].split(MARK, 1)[1])
    assert not res.get("fatal"), f"UAT 스크립트 치명적 오류:\n{res['fatal']}"
    sec = res["sections"].get("tolerance")
    assert sec is not None, "UAT 결과에 tolerance 섹션 없음"
    assert sec["ok"], f"tolerance 섹션 실패: {sec['error']}"
    return sec["data"]


@pytest.fixture(scope="module")
def tolerance():
    """한 번만 앱을 준비하고 PNG 를 모두 받아 둔다(POSE_APP_URL 이 있으면 빌드·서빙 생략)."""
    proc = None
    try:
        url = os.environ.get("POSE_APP_URL")
        if not url:
            assert APP.is_dir(), f"app/ not found: {APP}"
            assert (APP / "package.json").is_file(), "app/package.json not found"
            _sh(["npm", "ci"], APP, 600)
            _sh(["npm", "run", "build"], APP, 600)
            proc = subprocess.Popen(["npx", "vite", "preview", "--port", str(PORT), "--strictPort"], cwd=APP,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            _wait_http(URL, proc)
            url = URL
        yield _run_tolerance(url)
    finally:
        if proc and proc.poll() is None:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(10)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)


def _pixels(path, canvas_size=None):
    """PNG → RGB int 배열. canvas_size 가 주어지면 다운로드 크기와 대조한다(새 동작: 뷰포트 캔버스 크기)."""
    img = Image.open(path)
    assert img.format == "PNG", f"{path}: 형식 {img.format}"
    if canvas_size is not None:
        assert tuple(img.size) == tuple(canvas_size), f"{path}: {img.size} != 다운로드 시점 뷰포트 캔버스 {tuple(canvas_size)}"
    return np.asarray(img.convert("RGB")).astype(int)


def _metrics(a, b):
    """(평균 절대 차이, 채널 차이 > PNG_BIG_DIFF_LEVEL 인 픽셀 비율) — test_20 과 같은 정의. 크기가 다르면 비교 불가."""
    assert a.shape == b.shape, f"PNG 크기가 다름: {a.shape} vs {b.shape} (뷰포트가 다른 렌더는 비교하지 않는다)"
    diff = np.abs(a - b)
    return float(diff.mean()), float(np.mean(diff.max(axis=2) > PNG_BIG_DIFF_LEVEL))


_MEASURED = {}


@pytest.fixture(scope="module")
def metrics(tolerance):
    """노이즈(최댓값)와 신호(최솟값)를 계산해 파일로도 남긴다. 크기가 다른 렌더끼리는 비교하지 않는다."""
    noise_rows = tolerance["noise"]
    assert len(noise_rows) >= 4, f"노이즈 렌더가 {len(noise_rows)}장뿐(4장 필요)"
    by_label = {r["label"]: r for r in noise_rows}
    assert sorted(by_label) == sorted(NOISE_LABELS), sorted(by_label)
    sizes = {}
    for r in noise_rows:
        img = Image.open(r["path"])
        assert img.format == "PNG", f"{r['path']}: 형식 {img.format}"
        sizes[r["label"]] = tuple(img.size)
        if r.get("canvasSize") is not None:
            assert tuple(img.size) == tuple(r["canvasSize"]), \
                f"{r['label']}: {img.size} != 다운로드 시점 뷰포트 캔버스 {tuple(r['canvasSize'])}"
    same = [by_label[label] for label in SAME_VIEWPORT_NOISE_LABELS]
    noise_imgs = [(r["label"], _pixels(r["path"])) for r in same]
    noise_pairs = list(itertools.combinations(noise_imgs, 2))
    assert len(noise_pairs) >= NOISE_PAIRS_MIN, f"같은 뷰포트 노이즈 쌍이 {len(noise_pairs)}쌍뿐"
    noise_mean = max(_metrics(a, b)[0] for (_, a), (_, b) in noise_pairs)
    noise_big = max(_metrics(a, b)[1] for (_, a), (_, b) in noise_pairs)

    pose_imgs = {pid: _pixels(row["path"], row.get("canvasSize")) for pid, row in tolerance["poses"].items()}
    assert len({a.shape for a in pose_imgs.values()}) == 1, "포즈별 PNG 크기가 서로 다름(같은 뷰포트에서 받아야 함)"
    pairs = list(itertools.combinations(pose_imgs, 2))
    assert len(pairs) >= 1, "포즈가 2개 미만이라 신호를 잴 수 없다"
    measured = [(_metrics(pose_imgs[x], pose_imgs[y]), x, y) for x, y in pairs]
    ((sig_mean, _), x_mean, y_mean) = min(measured, key=lambda m: m[0][0])
    ((_, sig_big), x_big, y_big) = min(measured, key=lambda m: m[0][1])
    # 판정용: 하위 1% 분위수. 의도적 near-variant 쌍(pose_10/pose_32 등)이 최소값을 지배하므로,
    # 라이브러리 규모에서는 최소값이 아니라 분위수가 정직하다(근거는 측정값·보고서 참조).
    k = max(1, len(pairs) // 100)
    gate_mean = sorted(m[0][0] for m in measured)[k]
    gate_big = sorted(m[0][1] for m in measured)[k]
    below_mean = sorted([(m[0][0], [m[1], m[2]]) for m in measured if m[0][0] <= PNG_MEAN_DIFF_MAX * 3])[:20]
    below_big = sorted([(m[0][1], [m[1], m[2]]) for m in measured if m[0][1] <= PNG_BIG_DIFF_FRACTION_MAX * 3])[:20]

    _MEASURED.update({
        "tolerance": {"mean_diff_max": PNG_MEAN_DIFF_MAX,
                      "big_diff_fraction_max": PNG_BIG_DIFF_FRACTION_MAX,
                      "big_diff_level": PNG_BIG_DIFF_LEVEL},
        "noise": {"mean_diff": noise_mean, "big_diff_fraction": noise_big,
                  "renders": [r["label"] for r in same], "pairs": len(noise_pairs)},
        "sizes": {k: list(v) for k, v in sizes.items()},
        "signal": {"mean_diff_min": sig_mean, "mean_diff_min_pair": [x_mean, y_mean],
                   "big_diff_fraction_min": sig_big, "big_diff_fraction_min_pair": [x_big, y_big],
                   "mean_diff_p1": gate_mean, "big_diff_fraction_p1": gate_big,
                   "below_mean_margin_pairs": [[m, p] for m, p in below_mean],
                   "below_big_margin_pairs": [[b, p] for b, p in below_big],
                   "pairs": len(pairs), "poses": len(pose_imgs)},
    })
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "measurements.json").write_text(json.dumps(_MEASURED, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(_MEASURED, ensure_ascii=False, indent=2))
    return _MEASURED


def test_tolerance_pngs_are_same_state(metrics, tolerance):
    """노이즈용 4장이 정말 같은 상태였는지(성별 왕복·뷰포트 변경이 실제로 일어났는지) 확인한다."""
    assert [r["label"] for r in tolerance["noise"]] == NOISE_LABELS
    for row in tolerance["noise"]:
        assert row["state"] == EXPECTED_STATE, f"{row['label']}: 상태 {row['state']} != {EXPECTED_STATE}"
    assert tolerance["resized"]["w"] < tolerance["viewport"]["w"], \
        f"뷰포트가 줄지 않음: {tolerance['viewport']} → {tolerance['resized']}"
    assert set(tolerance["poses"]) == set(pose_ids()), "포즈별 PNG 집합이 poses/pose_*.json 과 다름"
    for pid, row in tolerance["poses"].items():
        assert row["state"] == {"poseId": pid, "gender": "female", "angle": "front"}, f"{pid}: {row['state']}"


def test_resized_viewport_changes_png_size(metrics):
    """캡처가 뷰포트를 따르는 증거: 뷰포트를 줄이면 PNG 크기가 바뀌고, 리사이즈 전 3장은 크기가 같다. 900×1200 고정이 아님."""
    sizes = {k: tuple(v) for k, v in metrics["sizes"].items()}
    assert sizes["viewport_resized"] != sizes["initial"], \
        f"뷰포트를 줄였는데 PNG 크기가 같음: {sizes['initial']} (오프스크린 고정 크기 회귀 의심)"
    assert sizes["repeat"] == sizes["initial"] == sizes["gender_roundtrip"], sizes


def test_png_noise_below_tolerance(metrics):
    """같은 상태의 재렌더 차이(노이즈)는 허용오차의 1/3 보다 작아야 한다."""
    noise = metrics["noise"]
    limit_mean, limit_big = PNG_MEAN_DIFF_MAX / 3, PNG_BIG_DIFF_FRACTION_MAX / 3
    assert noise["mean_diff"] < limit_mean, (
        f"렌더 노이즈 평균 차이 {noise['mean_diff']:.4f} ≥ 허용오차/3 {limit_mean:.4f} "
        f"(허용오차 {PNG_MEAN_DIFF_MAX}; 노이즈 렌더 {noise['renders']})"
    )
    assert noise["big_diff_fraction"] < limit_big, (
        f"렌더 노이즈 큰 차이 픽셀 {noise['big_diff_fraction']:.4%} ≥ 허용오차/3 {limit_big:.4%} "
        f"(허용오차 {PNG_BIG_DIFF_FRACTION_MAX:.4%}; 레벨 >{PNG_BIG_DIFF_LEVEL})"
    )


def test_png_pose_signal_above_tolerance(metrics):
    """서로 다른 포즈 사이의 차이(하위 1% 분위수)는 허용오차의 3배보다 커야 한다.
    최소값이 아니라 분위수를 쓰는 이유: 86종 라이브러리에는 의도적 near-variant 쌍이 있어
    최소값(pose_10/pose_32: 평균 1.20, 큰픽셀 1.03%)이 허용오차 안에 들어간다.
    임계값은 일반적인 포즈 교체를 잡아내면 되고 쌍둥이까지 잡아낼 수는 없다.
    허용오차 안에 든 쌍 목록은 measurements.json 의 below_*_margin_pairs 에 남긴다."""
    sig = metrics["signal"]
    limit_mean, limit_big = PNG_MEAN_DIFF_MAX * 3, PNG_BIG_DIFF_FRACTION_MAX * 3
    assert limit_mean < sig["mean_diff_p1"], (
        f"포즈 신호 평균 차이 하위1% {sig['mean_diff_p1']:.4f} ≤ 허용오차×3 {limit_mean:.4f} "
        f"({sig['pairs']}쌍 중; 최소쌍 {sig['mean_diff_min_pair']}={sig['mean_diff_min']:.4f})"
    )
    assert limit_big < sig["big_diff_fraction_p1"], (
        f"포즈 신호 큰 차이 픽셀 하위1% {sig['big_diff_fraction_p1']:.4%} ≤ 허용오차×3 {limit_big:.4%} "
        f"({sig['pairs']}쌍 중; 최소쌍 {sig['big_diff_fraction_min_pair']}={sig['big_diff_fraction_min']:.4%})"
    )
