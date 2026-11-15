// 갤러리 웹앱 UAT 드라이버 — `ego-browser nodejs < scripts/app_uat.js` 로 실행한다.
// 계약(디버그 훅·셀렉터)은 tests/app_contract.md 에 있다.
//
// ego-browser 스크립트는 셸 환경변수를 상속하지 않으므로, tests/test_20_app.py 가 이 파일 앞에
//   const CONFIG = {...};
// 한 줄을 붙여서 stdin 으로 넘긴다. CONFIG:
//   url              앱 주소 (예: http://localhost:4173/)
//   outDir           다운로드한 PNG 를 저장할 절대 경로 디렉터리
//   angles           {front:{yawDeg,pitchDeg}, ...}  (prompt/ 의 ANGLE_PRESETS 에서 가져온 값)
//   baselinePoses    [poseId, ...]  female·front 로 PNG 를 받을 포즈
//   promptCases      [{poseId, gender, angle}, ...]  UI 클릭으로 맞춘 뒤 복사 버튼을 누를 상태
//   framing          {poses:[poseId, ...], angles:[key, ...]}  female 로 포즈×앵글 PNG 를 받을 조합(프레이밍 검사)
//   tolerance        {poseId, poses:[poseId, ...], gender, angle}  허용오차 측정용 PNG(같은 상태 반복 + 포즈별 1장)
// 결과: 마지막에 `__UAT_RESULT__<json>` 한 줄을 출력한다. 섹션 하나가 실패해도 나머지는 계속 실행한다.
if (typeof CONFIG === "undefined") throw new Error("CONFIG 가 없다: tests/test_20_app.py 가 앞에 붙여 준다");

const fs = await import("node:fs/promises");
const result = { sections: {}, fatal: null };
const task = await taskSpace("pose-app-uat");
const page = task.page("p1");
const T = 30_000;

async function section(name, fn) {
  try {
    result.sections[name] = { ok: true, data: await fn() };
  } catch (e) {
    result.sections[name] = { ok: false, error: String((e && e.message) || e) };
  }
}
const evalApp = (fn, arg) => page.evaluate(fn, arg === undefined ? null : arg);
const state = () => evalApp(() => window.__poseApp.getState());

// 앵글 프리셋 도달: 상태의 angle 이 맞고 카메라 yaw/pitch 가 ±1° 이내(OrbitControls 감쇠·애니메이션 대기)
async function waitAngle(key) {
  await page.waitForFunction(
    ({ key, p }) => {
      const a = window.__poseApp;
      const c = a.cameraAngles();
      const dy = ((c.yawDeg - p.yawDeg + 540) % 360) - 180;
      return a.getState().angle === key && Math.abs(dy) <= 1 && Math.abs(c.pitchDeg - p.pitchDeg) <= 1;
    },
    { key, p: CONFIG.angles[key] },
    { timeout: 10_000 },
  );
}
async function waitPose(id) {
  await page.waitForFunction((id) => window.__poseApp.getState().poseId === id, id, { timeout: 10_000 });
}
async function waitGender(g) {
  await page.waitForFunction((g) => window.__poseApp.getState().gender === g, g, { timeout: 10_000 });
}
// 다운로드 이벤트를 먼저 걸고 #download-png 를 눌러 outDir 에 저장한다.
// 새 동작(app E5F6): 보이는 메인 캔버스 그대로 캡처라 크기가 고정값이 아니므로,
// 다운로드 시점의 #main-canvas drawing buffer 크기(canvas.width×canvas.height)도 함께 기록한다.
async function download(file) {
  const dl = page.waitForEvent("download", { timeout: T });
  await page.click("#download-png");
  const d = await dl;
  const path = `${CONFIG.outDir}/${file}`;
  await d.saveAs(path);
  const canvasSize = await evalApp(() => {
    const c = document.getElementById("main-canvas");
    return c ? [c.width, c.height] : null;
  });
  return { path, suggestedFilename: d.suggestedFilename(), canvasSize };
}

try {
  await fs.mkdir(CONFIG.outDir, { recursive: true });
  await page.goto(CONFIG.url, { timeout: T });
  await page.waitForFunction(() => !!window.__poseApp, undefined, { timeout: T });
  await evalApp(() => window.__poseApp.ready);
  await evalApp(() => performance.setResourceTimingBufferSize(5000));
  // 클립보드 가로채기: 실제 클립보드는 권한·포커스에 따라 불안정하므로 writeText 호출 인자만 기록한다(원본은 호출하지 않는다).
  await evalApp(() => {
    window.__copied = [];
    const writeText = async (t) => { window.__copied.push(String(t)); };
    if (navigator.clipboard) navigator.clipboard.writeText = writeText;
    else Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
  });

  await section("hook", () => evalApp(() => ({
    poseIds: window.__poseApp.poseIds(),
    state: window.__poseApp.getState(),
    camera: window.__poseApp.cameraAngles(),
  })));

  // 1. 모든 썸네일을 DOM 클릭 → 선택 포즈 id 가 바뀐다
  await section("thumbnails", async () => {
    await evalApp(() => window.__poseApp.setGender("female"));
    const domIds = await evalApp(() => [...document.querySelectorAll("[data-pose-id]")].map((e) => e.getAttribute("data-pose-id")));
    const clicks = [];
    for (const id of domIds) {
      const before = (await state()).poseId;
      await page.click(`[data-pose-id="${id}"]`);
      await waitPose(id);
      clicks.push({ id, before, after: (await state()).poseId });
    }
    return { domIds, clicks };
  });

  // 2. 포즈 × 성별 관절 월드 위치(GLB 모델 공간, 미터)
  await section("joints", async () => {
    const ids = await evalApp(() => window.__poseApp.poseIds());
    const out = {};
    for (const g of ["female", "male"]) {
      for (const id of ids) {
        out[`${g}/${id}`] = await evalApp(async ({ g, id }) => {
          await window.__poseApp.setGender(g);
          await window.__poseApp.selectPose(id);
          return { state: window.__poseApp.getState(), joints: window.__poseApp.jointPositions() };
        }, { g, id });
      }
    }
    return out;
  });

  // 5. 앵글 프리셋 버튼 5개 → 카메라가 프리셋 yaw/pitch 로, 프롬프트 텍스트도 함께 기록
  await section("angles", async () => {
    await evalApp(async () => {
      await window.__poseApp.setGender("female");
      await window.__poseApp.selectPose(window.__poseApp.poseIds()[0]);
    });
    const rows = {};
    for (const key of Object.keys(CONFIG.angles)) {
      await page.click(`[data-angle="${key}"]`);
      await waitAngle(key);
      rows[key] = await evalApp(() => ({
        state: window.__poseApp.getState(),
        camera: window.__poseApp.cameraAngles(),
        promptText: window.__poseApp.promptText(),
      }));
    }
    return rows;
  });

  // 4. 프롬프트 복사: UI 클릭으로 상태를 맞추고 #copy-prompt
  if (Array.isArray(CONFIG.promptCases)) await section("copy", async () => {
    const rows = [];
    for (const c of CONFIG.promptCases) {
      await page.click(`[data-gender="${c.gender}"]`);
      await waitGender(c.gender);
      await page.click(`[data-pose-id="${c.poseId}"]`);
      await waitPose(c.poseId);
      await page.click(`[data-angle="${c.angle}"]`);
      await waitAngle(c.angle);
      const n = await evalApp(() => window.__copied.length);
      await page.click("#copy-prompt");
      await page.waitForFunction((n) => window.__copied.length > n, n, { timeout: 10_000 });
      rows.push({
        want: c,
        ...(await evalApp(() => {
          const el = document.querySelector("#prompt-text");
          return {
            copied: window.__copied[window.__copied.length - 1],
            copyCount: window.__copied.length,
            shown: el ? (el.value ?? el.textContent) : null,
            hook: window.__poseApp.promptText(),
            state: window.__poseApp.getState(),
          };
        })),
      });
    }
    return rows;
  });

  // 3·7. PNG 다운로드: female·front 기준 이미지 + 다른 상태(male·side) 한 장 +
  // 첫 포즈 연속 재다운로드(상태를 건드리지 않은 2연속 캡처, 픽셀 완전 일치 확인용).
  // 새 동작(app E5F6): 보이는 메인 캔버스 그대로 캡처(900×1200 오프스크린 아님).
  if (Array.isArray(CONFIG.baselinePoses)) await section("downloads", async () => {
    const files = {};
    await evalApp(() => window.__poseApp.setGender("female"));
    await waitGender("female");
    for (const [i, id] of CONFIG.baselinePoses.entries()) {
      await evalApp((id) => window.__poseApp.selectPose(id), id);
      await waitPose(id);
      await page.click('[data-angle="front"]');
      await waitAngle("front");
      files[`baseline/${id}`] = { ...(await download(`${id}_female_front.png`)), state: await state() };
      if (i === 0) {
        // 상태 변경 없이 바로 한 번 더: 결정적 재렌더면 픽셀이 완전히 같아야 한다.
        files[`repeat/${id}`] = { ...(await download(`${id}_female_front_repeat.png`)), state: await state() };
      }
    }
    await evalApp(() => window.__poseApp.setGender("male"));
    await waitGender("male");
    await page.click('[data-angle="side"]');
    await waitAngle("side");
    files["male_side"] = { ...(await download("male_side.png")), state: await state() };
    return files;
  });

  // 8. 프레이밍용 PNG: 모든 포즈 × 앵글 5개 × female. 한 브라우저 세션에서 몰아 받는다(테스트가 bbox 여백을 잰다).
  //      상태 변경은 디버그 훅으로 하고(클릭 수 절약), 카메라가 프리셋에 도달한 것만 확인한 뒤 다운로드한다.
  //      한 세션·한 뷰포트에서 받으므로 모든 PNG 크기가 같아야 한다(테스트가 단언).
  await section("framing", async () => {
    const cfg = CONFIG.framing || { poses: [], angles: [] };
    const files = {};
    await evalApp(() => window.__poseApp.setGender("female"));
    await waitGender("female");
    for (const id of cfg.poses) {
      for (const key of cfg.angles) {
        await evalApp(({ id, key }) => {
          window.__poseApp.selectPose(id);
          window.__poseApp.setAngle(key);
        }, { id, key });
        await waitAngle(key);
        files[`${id}/${key}`] = { ...(await download(`framing_${id}_${key}.png`)), state: await state() };
      }
    }
    return files;
  });

  // 허용오차 보정(test_21): 같은 상태를 반복 렌더한 차이(노이즈)와 서로 다른 포즈의 차이(신호)를 재기 위한 PNG.
  //    노이즈 3장 = 최초 / 상태 변경 없이 반복 / 성별 왕복(female→male→female) 뒤 — 리사이즈 전에 몰아 받는다.
  //    뷰포트 변경 1장(viewport_resized)은 크기가 바뀌는 것 자체가 새 동작의 증거다.
  //    새 동작(app E5F6): 캡처가 뷰포트 캔버스를 따르므로 viewport_resized 장은 크기가 달라지는 것이 정상이다.
  //    노이즈 지표는 리사이즈 전 같은 뷰포트의 3장으로만 잰다.
  if (CONFIG.tolerance) await section("tolerance", async () => {
    const cfg = CONFIG.tolerance;
    const gender = cfg.gender || "female";
    const angle = cfg.angle || "front";
    const setState = (id) => evalApp(({ id, gender, angle }) => {
      window.__poseApp.setGender(gender);
      window.__poseApp.selectPose(id);
      window.__poseApp.setAngle(angle);
    }, { id, gender, angle });
    const settle = async (id) => {
      await waitGender(gender);
      await waitPose(id);
      await waitAngle(angle);
    };
    const capture = async (file) => ({ ...(await download(file)), state: await state() });

    const noise = [];
    const shot = async (label, file) => noise.push({ label, ...(await capture(file)) });
    const canvasSize = () => evalApp(() => {
      const c = document.getElementById("main-canvas");
      return c ? [c.width, c.height] : null;
    });
    // 캔버스 크기가 바뀔 때까지 대기(뷰포트 변경의 증거), 타임아웃이면 그대로 실패한다.
    const waitCanvasChange = (base) => page.waitForFunction((b) => {
      const c = document.getElementById("main-canvas");
      return c && (c.width !== b[0] || c.height !== b[1]);
    }, base, { timeout: 15_000 });
    // 캔버스 크기가 연속 2회(500 ms 간격) 같을 때까지 대기. 복원 후 초기값과
    // 같을 필요는 없다(로드 직후 버퍼가 최종 레이아웃과 다를 수 있어도 안정되면 된다).
    const waitCanvasStable = async () => {
      const t0 = Date.now();
      let prev = await canvasSize();
      for (;;) {
        await page.waitForTimeout(500);
        const cur = await canvasSize();
        if (cur && prev && cur[0] === prev[0] && cur[1] === prev[1]) return cur;
        prev = cur;
        if (Date.now() - t0 > 15000) throw new Error("canvas size not stable: " + JSON.stringify(cur));
      }
    };

    await setState(cfg.poseId);
    await settle(cfg.poseId);
    await shot("initial", "tol_noise_a.png");

    // 상태 변경 없이 바로 반복 렌더: 같은 뷰포트·같은 버퍼라 픽셀이 완전히 같아야 한다.
    await shot("repeat", "tol_noise_b.png");

    // 성별 왕복 뒤 같은 상태 (모델 교체·썸네일 재렌더가 PNG 에 영향을 주면 안 된다)
    await evalApp((g) => window.__poseApp.setGender(g === "female" ? "male" : "female"), gender);
    await setState(cfg.poseId);
    await settle(cfg.poseId);
    await shot("gender_roundtrip", "tol_noise_c.png");

    // 뷰포트 크기 변경 뒤 같은 상태 (캡처가 뷰포트를 따르므로 PNG 크기가 바뀌는 것이 정상이다)
    const viewport = await evalApp(() => ({ w: window.innerWidth, h: window.innerHeight }));
    const baseCanvas = await canvasSize();
    await page.cdp("Emulation.setDeviceMetricsOverride", {
      width: Math.max(640, Math.round(viewport.w * 0.7)),
      height: Math.max(480, Math.round(viewport.h * 0.7)),
      deviceScaleFactor: 1,
      mobile: false,
    });
    await waitCanvasChange(baseCanvas);
    await waitCanvasStable();
    const resized = await evalApp(() => ({ w: window.innerWidth, h: window.innerHeight }));
    await setState(cfg.poseId);
    await settle(cfg.poseId);
    await shot("viewport_resized", "tol_noise_d.png");
    await page.cdp("Emulation.clearDeviceMetricsOverride");
    await waitCanvasStable();

    // 신호: 모든 포즈를 같은 성별·앵글로 한 장씩
    const poses = {};
    for (const id of cfg.poses) {
      await setState(id);
      await settle(id);
      poses[id] = await capture(`tol_pose_${id}.png`);
    }
    return { noise, poses, viewport, resized };
  });

  // 6. 네트워크: 이 문서가 지금까지 요청한 모든 리소스(fetch·img·xhr·script 포함, Resource Timing)
  await section("network", () => evalApp(() => {
    const names = performance.getEntriesByType("resource").map((e) => e.name);
    return { total: names.length, reference: names.filter((n) => n.includes("/poses/reference/")), names };
  }));
} catch (e) {
  result.fatal = String((e && e.stack) || e);
} finally {
  try { await task.finish({ keep: [] }); } catch (e) { result.finishError = String(e); }
}
console.log("__UAT_RESULT__" + JSON.stringify(result));
