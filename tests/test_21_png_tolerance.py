"""PNG 회귀 허용오차가 데이터로 정당한지 측정한다 (task #5 S1).

test_20 의 `test_canvas_png_matches_baseline` 은 다운로드 PNG 를 기준 이미지와 비교해
  - 평균 절대 차이 ≤ PNG_MEAN_DIFF_MAX (1.5/255)
  - 채널 차이 > PNG_BIG_DIFF_LEVEL(40) 인 픽셀 비율 ≤ PNG_BIG_DIFF_FRACTION_MAX (0.75 %)
로 회귀를 잡는다. 이 값이 쓸모 있으려면
  (a) 같은 상태를 다시 렌더해도 생기는 차이(노이즈)보다 충분히 커야 하고,
  (b) 서로 다른 포즈 사이의 차이(신호)보다 충분히 작아야 한다.
이 파일은 그 두 가지를 실측한다. 허용오차는 test_20_app 에서 그대로 import 하므로,
값을 바꾸면 이 테스트가 같은 기준으로 다시 판단한다.

측정 방법
  - 렌더는 test_20 과 같은 경로를 쓴다: ego-browser + scripts/app_uat.js 의 "tolerance" 섹션
    (같은 상태를 4번: 최초 / 성별 왕복 뒤 / 뷰포트 크기 변경 뒤 / 크기 복원 뒤 반복,
     그리고 모든 포즈 × female × front 1장씩). POSE_APP_URL 이 있으면 정적 서버를 그대로 쓴다.
  - 노이즈 = 같은 상태 4장의 모든 쌍(6쌍) 중 지표별 최댓값.
  - 신호   = 서로 다른 포즈 쌍(모든 조합)의 지표별 최솟값.
  - 단언   = 노이즈 < 허용오차/3  그리고  허용오차×3 < 신호  (평균·픽셀 비율 각각).
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
from test_20_app import PNG_MEAN_DIFF_MAX, PNG_BIG_DIFF_FRACTION_MAX
from test_20_app import ANGLES, PNG_BIG_DIFF_LEVEL, PNG_SIZE
from test_20_app import APP, MARK, PORT, SCRIPT, URL, _sh, _tail, _wait_http

OUT_DIR = ARTIFACTS / "png_tolerance"
NOISE_POSE = "pose_01_contrapposto_hand_on_head"
NOISE_LABELS = ["initial", "gender_roundtrip", "viewport_resized", "repeat"]
EXPECTED_STATE = {"poseId": NOISE_POSE, "gender": "female", "angle": "front"}
NOISE_PAIRS_MIN = 3  # 최소 4장 → 6쌍


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


def _pixels(path):
    img = Image.open(path)
    assert img.format == "PNG", f"{path}: 형식 {img.format}"
    assert img.size == PNG_SIZE, f"{path}: {img.size} != {PNG_SIZE}"
    return np.asarray(img.convert("RGB")).astype(int)


def _metrics(a, b):
    """(평균 절대 차이, 채널 차이 > PNG_BIG_DIFF_LEVEL 인 픽셀 비율) — test_20 과 같은 정의."""
    diff = np.abs(a - b)
    return float(diff.mean()), float(np.mean(diff.max(axis=2) > PNG_BIG_DIFF_LEVEL))


_MEASURED = {}


@pytest.fixture(scope="module")
def metrics(tolerance):
    """노이즈(최댓값)와 신호(최솟값)를 계산해 파일로도 남긴다."""
    noise_rows = tolerance["noise"]
    assert len(noise_rows) >= NOISE_PAIRS_MIN + 1, f"노이즈 렌더가 {len(noise_rows)}장뿐(4장 이상 필요)"
    noise_imgs = [(r["label"], _pixels(r["path"])) for r in noise_rows]
    noise_pairs = list(itertools.combinations(noise_imgs, 2))
    noise_mean = max(_metrics(a, b)[0] for (_, a), (_, b) in noise_pairs)
    noise_big = max(_metrics(a, b)[1] for (_, a), (_, b) in noise_pairs)

    pose_imgs = {pid: _pixels(row["path"]) for pid, row in tolerance["poses"].items()}
    pairs = list(itertools.combinations(pose_imgs, 2))
    assert len(pairs) >= 1, "포즈가 2개 미만이라 신호를 잴 수 없다"
    measured = [(_metrics(pose_imgs[x], pose_imgs[y]), x, y) for x, y in pairs]
    ((sig_mean, _), x_mean, y_mean) = min(measured, key=lambda m: m[0][0])
    ((_, sig_big), x_big, y_big) = min(measured, key=lambda m: m[0][1])

    _MEASURED.update({
        "tolerance": {"mean_diff_max": PNG_MEAN_DIFF_MAX,
                      "big_diff_fraction_max": PNG_BIG_DIFF_FRACTION_MAX,
                      "big_diff_level": PNG_BIG_DIFF_LEVEL},
        "noise": {"mean_diff": noise_mean, "big_diff_fraction": noise_big,
                  "renders": [r["label"] for r in noise_rows], "pairs": len(noise_pairs)},
        "signal": {"mean_diff_min": sig_mean, "mean_diff_min_pair": [x_mean, y_mean],
                   "big_diff_fraction_min": sig_big, "big_diff_fraction_min_pair": [x_big, y_big],
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
    """서로 다른 포즈 사이의 최소 차이(신호)는 허용오차의 3배보다 커야 한다."""
    sig = metrics["signal"]
    limit_mean, limit_big = PNG_MEAN_DIFF_MAX * 3, PNG_BIG_DIFF_FRACTION_MAX * 3
    assert limit_mean < sig["mean_diff_min"], (
        f"포즈 신호 평균 차이 최솟값 {sig['mean_diff_min']:.4f} ≤ 허용오차×3 {limit_mean:.4f} "
        f"(쌍 {sig['mean_diff_min_pair']}, {sig['pairs']}쌍 중)"
    )
    assert limit_big < sig["big_diff_fraction_min"], (
        f"포즈 신호 큰 차이 픽셀 최솟값 {sig['big_diff_fraction_min']:.4%} ≤ 허용오차×3 {limit_big:.4%} "
        f"(쌍 {sig['big_diff_fraction_min_pair']}, {sig['pairs']}쌍 중)"
    )
