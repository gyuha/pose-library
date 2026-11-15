"""갤러리 웹앱(app/) 자동 검증 (task #2 S2, TDD: app/ 은 이후 슬라이스에서 만든다).

앱을 빌드(`npm ci && npm run build`)하고 `vite preview --port 4173 --strictPort` 로 띄운 뒤,
ego-browser 스크립트(scripts/app_uat.js)를 한 번 실행해 JSON 결과를 받아 항목별로 단언한다.
앱이 지켜야 할 디버그 훅(`window.__poseApp`)·셀렉터·각도 정의는 tests/app_contract.md 에 정확히 적혀 있다(요약은 아래).

  window.__poseApp = { ready, poseIds(), selectPose(id), setGender(g), setAngle(key), getState(){poseId,gender,angle},
                       cameraAngles(){yawDeg,pitchDeg}, jointPositions(){bone:[x,y,z]}, promptText() }
  셀렉터: [data-pose-id="<id>"] [data-gender="<g>"] [data-angle="<key>"] #download-png #copy-prompt #prompt-text

캡처 방식
  - PNG: ego-browser 실제 다운로드 이벤트(waitForEvent("download")+saveAs) → tests/artifacts/app_uat/ 에 저장해 PIL 로 검사.
    크기는 UAT 스크립트가 함께 기록한 다운로드 시점의 뷰포트 캔버스 크기(canvasSize)와 대조한다(고정값 아님).
  - 클립보드: 페이지에서 navigator.clipboard.writeText 를 가로채 인자를 기록(권한·포커스에 따라 실제 클립보드는 불안정). 원본은 호출하지 않는다.
  - 네트워크: 문서의 Resource Timing 항목(fetch·img·script·xhr)에 '/poses/reference/' 가 없어야 한다 + app/dist 에 경로에 'reference' 가 든 파일 없음.
  - 입력 전달: ego-browser 스크립트는 셸 환경변수를 상속하지 않아서 stdin 앞에 `const CONFIG = {...};` 를 붙여 넘긴다.
개발용 스위치: 환경변수 POSE_APP_URL 이 있으면 빌드·서빙을 건너뛰고 그 주소로 스크립트를 돌린다(하네스 점검용).

허용오차
  - 관절 위치: 각 뼈 1 mm (rigcore 와 같은 FK 규칙이므로 float32 반올림 수준만 허용).
  - 카메라 각도: ±1° (스크립트 쪽에서 대기하며 확인).
  - PNG 비교 지표(근거 수치는 `tests/test_21_png_tolerance.py` 가 실측으로 검증): 평균 절대 차이 ≤ 1.5/255,
    채널 차이 > 40 인 픽셀 비율 ≤ 0.75 %. 같은 렌더러에서는 거의 0 이고, 팔다리 하나가 다른 위치로 가면 수 % 가 바뀐다.
  - PNG 결정성(회귀 대신, app E5F6): 같은 상태를 건드리지 않고 연속 다운로드한 2장은 픽셀 단위로 완전히 같아야 한다.
    근거: 다운로드는 화면 캔버스의 재렌더 캡처라 같은 상태에서는 같은 바이트가 나와야 하며,
    한 픽셀이라도 다르면 렌더 비결정성·캡처 타이밍 버그다.
  - 프레이밍: 모든 포즈 × 앵글 5개 × female PNG 에서 배경과 다른 픽셀의 bbox 가 네 변 모두 ≥ 1 % 여백을 두고,
    긴 변이 화면의 ≥ 40 % 여야 한다(카메라가 너무 멀어 통과하는 것 방지). 다운로드는 UAT 스크립트의 "framing"
    섹션이 한 브라우저 세션에서 몰아 받는다. 한 세션의 PNG 크기는 모두 같아야 한다(같은 뷰포트 캔버스).
PNG 크기는 고정값이 아니다: 앱은 보이는 메인 캔버스 그대로를 캡처하므로(app E5F6, 구 900×1200 오프스크린 폐지),
다운로드 크기는 그 시점의 뷰포트 캔버스 픽셀 크기(= UAT가 함께 기록한 canvasSize)와 같아야 한다.
"""
import json
import os
import shutil
import signal
import subprocess
import time
import urllib.request

import numpy as np
import pytest
from PIL import Image

from pose_helpers import ARTIFACTS, ROOT, load_catalog, pose_ids, rigcore
from test_13_prompt import _node, _pose

APP = ROOT / "app"
SCRIPT = ROOT / "scripts" / "app_uat.js"
OUT_DIR = ARTIFACTS / "app_uat"
PORT = 4173
URL = f"http://localhost:{PORT}/"
MARK = "__UAT_RESULT__"

JOINT_TOL_M = 1e-3
# 다운로드 PNG 크기에 고정값은 없다(app E5F6: 보이는 메인 캔버스 그대로 캡처, 구 900×1200 오프스크린 폐지).
# 크기는 UAT 스크립트가 다운로드 시점에 함께 기록한 메인 캔버스 픽셀 크기(canvasSize)와 같아야 한다.
BASELINE_POSES = ["pose_01_contrapposto_hand_on_head", "pose_04_sitting_knees_up", "pose_07_running"]
# 프레이밍: 인물(배경과 다른 픽셀)의 bbox 가 네 변 모두에서 1 % 이상 떨어져야 하고,
# 카메라가 너무 멀어 통과하지 못하도록 bbox 의 긴 변이 화면의 40 % 이상이어야 한다.
FRAMING_MARGIN_MIN = 0.01
FRAMING_FIGURE_MIN = 0.40
FRAMING_BG_DIFF = 16
ANGLES = ["front", "side", "three_quarter", "high", "low"]
PROMPT_CASES = [
    {"poseId": "pose_01_contrapposto_hand_on_head", "gender": "female", "angle": "front"},
    {"poseId": "pose_04_sitting_knees_up", "gender": "male", "angle": "three_quarter"},
    {"poseId": "pose_08_tuck_jump_arms_up", "gender": "male", "angle": "low"},
    {"poseId": "pose_06_walking", "gender": "female", "angle": "high"},
]


def _tail(text, n=25):
    return "\n".join(text.strip().splitlines()[-n:])


def _sh(cmd, cwd, timeout):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    assert p.returncode == 0, f"`{' '.join(cmd)}` 실패(exit {p.returncode}):\n{_tail(p.stdout + p.stderr)}"


def _wait_http(url, proc, timeout=40):
    end = time.time() + timeout
    while time.time() < end:
        if proc.poll() is not None:
            raise AssertionError(f"vite preview 가 종료됨(exit {proc.returncode}); 포트 {PORT} 가 이미 사용 중일 수 있다")
        try:
            urllib.request.urlopen(url, timeout=2).read(1)
            return
        except Exception:
            time.sleep(0.4)
    raise AssertionError(f"{url} 가 {timeout}s 안에 응답하지 않음")


def _expected_prompts(cases):
    catalog = load_catalog()
    return _node([{"pose": _pose(c["poseId"]), "catalogEntry": catalog[c["poseId"]], "gender": c["gender"], "angle": c["angle"]}
                  for c in cases])


def _run_uat(url):
    if not shutil.which("ego-browser"):
        raise AssertionError("ego-browser 가 PATH 에 없다")
    angles = _node([])["angles"]
    cfg = {"url": url, "outDir": str(OUT_DIR), "baselinePoses": BASELINE_POSES, "promptCases": PROMPT_CASES,
           "framing": {"poses": pose_ids(), "angles": ANGLES},
           "angles": {k: {"yawDeg": angles[k]["yawDeg"], "pitchDeg": angles[k]["pitchDeg"]} for k in ANGLES}}
    assert set(angles) == set(ANGLES), angles.keys()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUT_DIR.glob("*.png"):
        old.unlink()
    code = f"const CONFIG = {json.dumps(cfg)};\n" + SCRIPT.read_text(encoding="utf-8")
    p = subprocess.run(["ego-browser", "nodejs"], input=code, capture_output=True, text=True, timeout=600)
    # ego-browser 는 console.log 를 stdout 이나 stderr 로 내보낼 수 있고 앞에 공백이 붙을 수도 있어 둘 다 본다
    lines = [ln for ln in (p.stdout + "\n" + p.stderr).splitlines() if MARK in ln]
    assert lines, f"ego-browser 스크립트가 결과를 내지 않음(exit {p.returncode}):\n{_tail(p.stdout + p.stderr)}"
    res = json.loads(lines[-1].split(MARK, 1)[1])
    assert not res.get("fatal"), f"UAT 스크립트 치명적 오류:\n{res['fatal']}"
    return res


class Uat:
    """한 번 실행한 UAT 결과. 준비 단계 오류는 error 에 담아 모든 테스트가 같은 메시지로 FAIL 하게 한다."""

    def __init__(self):
        self.error, self.result = None, None

    def section(self, name):
        assert self.error is None, self.error
        sec = self.result["sections"].get(name)
        assert sec is not None, f"UAT 결과에 섹션 {name!r} 없음"
        assert sec["ok"], f"섹션 {name} 실패: {sec['error']}"
        return sec["data"]


@pytest.fixture(scope="module")
def uat():
    run, proc = Uat(), None
    try:
        url = os.environ.get("POSE_APP_URL")
        if not url:
            assert APP.is_dir(), f"app/ not found: {APP} (task #2 S3 에서 app 역할이 만든다)"
            assert (APP / "package.json").is_file(), "app/package.json not found"
            _sh(["npm", "ci"], APP, 600)
            _sh(["npm", "run", "build"], APP, 600)
            proc = subprocess.Popen(["npx", "vite", "preview", "--port", str(PORT), "--strictPort"], cwd=APP,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            _wait_http(URL, proc)
            url = URL
        run.result = _run_uat(url)
    except AssertionError as e:
        run.error = str(e)
    except subprocess.TimeoutExpired as e:
        run.error = f"시간 초과: {e}"
    yield run
    if proc and proc.poll() is None:
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            proc.wait(10)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)


# ---------------------------------------------------------------- tests
def test_app_present_and_hook_installed(uat):
    h = uat.section("hook")
    assert sorted(h["poseIds"]) == sorted(pose_ids()), h["poseIds"]
    assert set(h["state"]) >= {"poseId", "gender", "angle"} and h["state"]["gender"] in ("female", "male")
    assert {"yawDeg", "pitchDeg"} <= set(h["camera"])


def test_clicking_every_thumbnail_selects_that_pose(uat):
    d = uat.section("thumbnails")
    assert sorted(d["domIds"]) == sorted(pose_ids()), f"썸네일 id {d['domIds']} != 포즈 파일 {pose_ids()}"
    assert len(set(d["domIds"])) == len(d["domIds"]), "썸네일 id 중복"
    bad = [c for c in d["clicks"] if c["after"] != c["id"]]
    assert not bad, bad
    assert len({c["after"] for c in d["clicks"]}) == len(d["clicks"])


_TRUTH = {}


def _truth(gender, pose_id):
    key = (gender, pose_id)
    if key not in _TRUTH:
        if gender not in _TRUTH:
            _TRUTH[gender] = rigcore.Skeleton.from_glb(ROOT / "rig" / f"{gender}.glb")
        skel = _TRUTH[gender]
        pose = rigcore.load_pose(ROOT / "poses" / f"{pose_id}.json")
        G = skel.pose_globals(rigcore.pose_for(skel, pose))
        _TRUTH[key] = {b: G[i][:3, 3] for i, b in enumerate(rigcore.BONES)}
    return _TRUTH[key]


@pytest.mark.parametrize("gender", ["female", "male"])
@pytest.mark.parametrize("pose_id", pose_ids())
def test_joint_positions_match_rigcore(uat, gender, pose_id):
    d = uat.section("joints")
    row = d.get(f"{gender}/{pose_id}")
    assert row, f"{gender}/{pose_id} 결과 없음"
    assert row["state"]["poseId"] == pose_id and row["state"]["gender"] == gender, row["state"]
    got, want = row["joints"], _truth(gender, pose_id)
    assert set(got) == set(want), f"뼈 집합 불일치: 없음 {sorted(set(want) - set(got))[:5]}, 초과 {sorted(set(got) - set(want))[:5]}"
    err = {b: float(np.linalg.norm(np.array(got[b]) - want[b])) for b in want}
    worst = sorted(err.items(), key=lambda kv: -kv[1])[:4]
    assert max(err.values()) <= JOINT_TOL_M, "허용 1 mm 초과(최악 4개): " + ", ".join(f"{b} {e * 1e3:.2f} mm" for b, e in worst)


def _png(path):
    img = Image.open(path)
    assert img.format == "PNG", f"{path}: 형식 {img.format}"
    return img


def test_download_png_matches_viewport_canvas(uat):
    """다운로드는 보이는 메인 캔버스 그대로다: 유효 PNG·파일명 규칙·0이 아닌 크기·캔버스 크기 일치·빈 화면 아님."""
    d = uat.section("downloads")
    assert set(d) == {f"baseline/{p}" for p in BASELINE_POSES} | {"male_side", f"repeat/{BASELINE_POSES[0]}"}
    for key, v in d.items():
        st = v["state"]
        assert v["suggestedFilename"] == f"{st['poseId']}_{st['gender']}_{st['angle']}.png", \
            f"{key}: 파일명 {v['suggestedFilename']!r} (규칙 {{poseId}}_{{gender}}_{{angle}}.png)"
        assert v.get("canvasSize"), f"{key}: canvasSize 기록 없음(UAT 스크립트가 #main-canvas 크기를 함께 기록해야 함)"
        img = _png(v["path"])
        assert img.size[0] > 0 and img.size[1] > 0, f"{key}: 크기 0"
        assert tuple(img.size) == tuple(v["canvasSize"]), \
            f"{key}: 다운로드 {img.size} != 다운로드 시점 뷰포트 캔버스 {tuple(v['canvasSize'])} (900x1200 고정이 아님)"
        a = np.asarray(img.convert("RGB")).astype(int)
        bg = a[0, 0]
        changed = np.mean(np.abs(a - bg).max(axis=2) > 12)
        assert changed >= 0.01, f"{key}: 배경과 다른 픽셀 {changed:.2%} (빈 화면?)"
        assert np.abs(a[[0, 0, -1, -1], [0, -1, 0, -1]] - bg).max() <= 12, f"{key}: 모서리가 단색 배경이 아님"
        assert bg.mean() >= 200, f"{key}: 배경 {bg.tolist()} 가 밝은 단색이 아님"


def _figure_box(img):
    """배경(좌상단 색)과 다른 픽셀의 bbox (left, right, top, bottom). 픽셀 좌표는 0-based, 끝 포함."""
    a = np.asarray(img.convert("RGB")).astype(int)
    bg = a[0, 0]
    ys, xs = np.nonzero(np.abs(a - bg).max(axis=2) > FRAMING_BG_DIFF)
    assert xs.size, "배경과 다른 픽셀이 없음(빈 화면?)"
    return int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())


@pytest.mark.parametrize("angle", ANGLES)
@pytest.mark.parametrize("pose_id", pose_ids())
def test_png_framing(uat, pose_id, angle):
    """포즈 × 앵글 프리셋마다 인물이 PNG 네 변에서 1 % 이상 떨어져 있고, 너무 작지도 않다."""
    key = f"{pose_id}/{angle}"
    row = uat.section("framing").get(key)
    assert row, f"UAT 결과에 프레이밍 항목 {key} 없음"
    assert row["state"] == {"poseId": pose_id, "gender": "female", "angle": angle}, row["state"]
    img = _png(row["path"])
    assert tuple(img.size) == tuple(row["canvasSize"]), \
        f"{key}: 다운로드 {img.size} != 다운로드 시점 뷰포트 캔버스 {tuple(row['canvasSize'])} (900x1200 고정이 아님)"
    left, right, top, bottom = _figure_box(img)
    w, h = img.size
    margins = {"left": left / w, "right": (w - 1 - right) / w,
               "top": top / h, "bottom": (h - 1 - bottom) / h}
    too_close = {k: v for k, v in margins.items() if v < FRAMING_MARGIN_MIN}
    assert not too_close, (
        f"{key}: 인물이 이미지 변에 닿음 — bbox=({left},{top})-({right},{bottom}) / {w}x{h}, "
        + ", ".join(f"{k} 여백 {v:.2%}" for k, v in margins.items())
        + f" (네 변 모두 ≥ {FRAMING_MARGIN_MIN:.0%} 필요)"
    )
    width_frac, height_frac = (right - left + 1) / w, (bottom - top + 1) / h
    assert max(width_frac, height_frac) >= FRAMING_FIGURE_MIN, (
        f"{key}: 인물이 너무 작음 — bbox {width_frac:.1%} x {height_frac:.1%} / {w}x{h} "
        f"(긴 변 ≥ {FRAMING_FIGURE_MIN:.0%} 필요)"
    )


def test_framing_pngs_share_one_viewport_size(uat):
    """framing 섹션은 한 세션·한 뷰포트에서 몰아 받으므로 모든 PNG 크기가 같아야 한다."""
    rows = uat.section("framing")
    sizes = {tuple(Image.open(r["path"]).size) for r in rows.values()}
    assert len(sizes) == 1, f"한 세션 내 PNG 크기 불일치: {sorted(sizes)} (뷰포트가 바뀌었거나 캡처가 비결정적)"


def test_copy_prompt_equals_build_prompt(uat):
    rows = uat.section("copy")
    assert len(rows) == len(PROMPT_CASES)
    want = _expected_prompts(PROMPT_CASES)["results"]
    for row, exp in zip(rows, want):
        tag = row["want"]
        assert exp["ok"], exp
        s = row["state"]
        assert (s["poseId"], s["gender"], s["angle"]) == (tag["poseId"], tag["gender"], tag["angle"]), s
        assert row["copied"] == exp["text"], f"{tag}: 복사 텍스트가 buildPosePrompt 와 다름\n{row['copied']!r}\n{exp['text']!r}"
        assert row["shown"] == row["copied"], f"{tag}: #prompt-text != 복사 텍스트"
        assert row["hook"] == row["copied"], f"{tag}: promptText() != 복사 텍스트"


@pytest.mark.parametrize("key", ANGLES)
def test_angle_button_sets_camera_preset(uat, key):
    rows = uat.section("angles")
    r = rows[key]
    p = _node([])["angles"][key]
    assert r["state"]["angle"] == key, r["state"]
    dyaw = (r["camera"]["yawDeg"] - p["yawDeg"] + 540) % 360 - 180
    assert abs(dyaw) <= 1 and abs(r["camera"]["pitchDeg"] - p["pitchDeg"]) <= 1, \
        f"카메라 {r['camera']} != 프리셋 yaw {p['yawDeg']}, pitch {p['pitchDeg']}"
    first = pose_ids()[0]
    exp = _expected_prompts([{"poseId": r["state"]["poseId"], "gender": r["state"]["gender"], "angle": key}])["results"][0]
    assert exp["ok"] and r["promptText"] == exp["text"], f"{key}: 화면 프롬프트가 해당 앵글의 buildPosePrompt 와 다름"
    assert r["state"]["poseId"] == first


def test_no_reference_image_requests(uat):
    n = uat.section("network")
    assert n["total"] > 0, "리소스 요청 기록이 비어 있음(측정 실패)"
    assert not n["reference"], f"/poses/reference/ 요청 {n['reference']}"
    dist = APP / "dist"
    if dist.is_dir():
        leaked = [str(p.relative_to(dist)) for p in dist.rglob("*") if p.is_file() and "reference" in str(p.relative_to(dist)).lower()]
        assert not leaked, f"app/dist 에 레퍼런스 파일: {leaked}"


def test_repeat_download_is_pixel_identical(uat):
    """같은 상태를 건드리지 않고 연속으로 받은 2장은 픽셀 단위로 같아야 한다(재렌더 결정성, 기준 파일 비교 아님)."""
    d = uat.section("downloads")
    pose_id = BASELINE_POSES[0]
    a, b = d[f"baseline/{pose_id}"], d[f"repeat/{pose_id}"]
    assert a["state"] == b["state"] == {"poseId": pose_id, "gender": "female", "angle": "front"}, (a["state"], b["state"])
    pa = np.asarray(Image.open(a["path"]).convert("RGB")).astype(int)
    pb = np.asarray(Image.open(b["path"]).convert("RGB")).astype(int)
    assert pa.shape == pb.shape, f"크기 {pa.shape} vs {pb.shape}"
    diff = np.abs(pa - pb)
    assert diff.max() == 0, f"연속 캡처가 다름: 최대 채널 차이 {diff.max()}, 평균 {diff.mean():.4f}"
