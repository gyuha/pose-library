# 웹앱 테스트 계약 (task #2, S2)

`tests/test_20_app.py`와 `scripts/app_uat.js`가 `app/`에 요구하는 인터페이스입니다. app 역할은 이 문서 그대로 구현합니다. 바꿔야 하면 qa와 먼저 합의합니다.

테스트는 앱을 빌드·서빙하고(`cd app && npm ci && npm run build`, `npx vite preview --port 4173 --strictPort`), ego-browser로 `http://localhost:4173/`을 열어 아래를 확인합니다.

```
npm ci → npm run build → vite preview(4173) → ego-browser 스크립트(app_uat.js) → JSON 결과 → pytest 단언
```

## 1. 디버그 훅 `window.__poseApp`

페이지 로드 시 동기적으로 설치합니다(값은 `ready` 이후 유효).

| 멤버 | 반환 | 의미 |
|---|---|---|
| `ready` | `Promise<void>` | 두 GLB 로드, 포즈 파일·카탈로그 로드, 첫 포즈 적용까지 끝나면 resolve |
| `poseIds()` | `string[]` | 갤러리의 모든 포즈 id(태그 필터와 무관, `poses/pose_*.json` 파일 id와 같은 집합) |
| `selectPose(id)` | `void` 또는 `Promise<void>` | UI 클릭과 같은 효과. Promise면 포즈 적용 후 resolve. 모르는 id는 예외 |
| `setGender('female'\|'male')` | `void` 또는 `Promise<void>` | 남/여 토글과 같은 효과. 모델 교체와 현재 포즈 재적용 후 resolve |
| `setAngle(key)` | `void` 또는 `Promise<void>` | 앵글 버튼과 같은 효과 |
| `getState()` | `{poseId, gender, angle}` | 현재 선택. `angle`은 `front\|side\|three_quarter\|high\|low`(카메라가 프리셋에서 벗어나면 가장 가까운 프리셋) |
| `cameraAngles()` | `{yawDeg, pitchDeg}` | 궤도 대상점 기준 카메라 방향(모델 공간). 아래 정의 |
| `jointPositions()` | `{[bone]: [x,y,z]}` | 53개 뼈 전부의 **머리(head) 월드 위치**, 현재 성별 GLB의 **원래 모델 공간**(미터, Y-up, +Z 앞, +X 캐릭터 왼쪽), 현재 포즈 적용 후 |
| `promptText()` | `string` | 지금 화면에 보이는 포즈 프롬프트 문자열 |

`ready`가 resolve된 뒤에는 `getState()`/`cameraAngles()`가 항상 값을 돌려줘야 합니다.

### 카메라 각도 정의 (`cameraAngles`)
`d = camera.position − controls.target`(모델 공간 벡터)일 때:
- `yawDeg = atan2(−d.x, d.z)` (도, −180~180]. 캐릭터 정면 +Z에서 0, 캐릭터 **오른쪽**(−X)에서 +90)
- `pitchDeg = asin(d.y / |d|)` (도. 위에서 내려다보면 +)

기대 값은 `prompt/`의 `ANGLE_PRESETS[key].{yawDeg, pitchDeg}`이며 허용오차는 ±1°입니다. 앵글 버튼을 누르면 카메라 애니메이션/감쇠가 있어도 **10초 안에** 프리셋에 도달해야 합니다.

### `jointPositions()` 주의
- 앱이 모델을 화면용으로 스케일·이동·회전하더라도(씬 그룹 변환) 값은 그 변환을 되돌린 GLB 모델 공간이어야 합니다.
- 기준값은 `rig/tools/rigcore.py`의 `Skeleton.from_glb('rig/<gender>.glb').pose_globals(pose_for(...))[bone][:3,3]`이고 허용오차는 **1 mm**입니다(`rest × pose quaternion`, 루트 이동 = `translation × 골반 높이`).

## 2. DOM 셀렉터

| 셀렉터 | 요소 | 요구 |
|---|---|---|
| `[data-pose-id="<id>"]` | 포즈 썸네일(클릭 가능한 요소) | 포즈당 정확히 하나(필터 해제 상태 기본값). 클릭하면 그 포즈 선택 |
| `[data-gender="female"]`, `[data-gender="male"]` | 남/여 토글 버튼 | 클릭하면 성별 전환 |
| `[data-angle="front"]` `side` `three_quarter` `high` `low` | 앵글 프리셋 버튼 5개 | 클릭하면 `setAngle`과 같은 효과 |
| `#download-png` | 다운로드 버튼 | 클릭하면 브라우저 다운로드 이벤트로 PNG 한 장 |
| `#copy-prompt` | 복사 버튼 | 클릭 시 **클릭 핸들러 안에서** `navigator.clipboard.writeText(text)`를 호출 |
| `#prompt-text` | 프롬프트 표시 요소 | `<textarea>`면 `.value`, 아니면 `.textContent`가 `promptText()`와 **글자 그대로** 같아야 함(8줄, `\n` 구분, 앞뒤 공백·장식 문구 없음) |

## 3. 검사와 허용오차

| # | 검사 | 방법 | 기준 |
|---|---|---|---|
| 1 | 썸네일 클릭 | `[data-pose-id]` 전부를 DOM 클릭 | 클릭 후 `getState().poseId == id`. DOM id 집합 == `poses/pose_*.json` id 집합 == `poseIds()` |
| 2 | 관절 위치 | 포즈 × 성별 16조합 `jointPositions()` | rigcore 값과 각 뼈 ≤ 1 mm, 뼈 집합 53개 일치 |
| 3 | PNG 다운로드 | `#download-png` 클릭 → 다운로드 이벤트 → 파일 저장 | PNG 시그니처, **900×1200**, 파일명 `.png`, 빈 화면이 아님(배경색과 다른 픽셀 ≥ 1 %) |
| 4 | 프롬프트 복사 | UI 클릭으로 상태 4가지를 맞추고 `#copy-prompt` | 클립보드 인자 == `#prompt-text` == `promptText()` == `buildPosePrompt({pose,catalogEntry,gender,angle})` |
| 5 | 앵글 5개 | `[data-angle]` 클릭 | `getState().angle == key`, `cameraAngles()`가 프리셋 ±1°, `promptText()`가 해당 앵글의 프롬프트 |
| 6 | 레퍼런스 네트워크 0건 | 문서가 요청한 모든 리소스(Resource Timing) | `/poses/reference/`를 포함하는 URL 0건. 추가로 `app/dist/` 안에 경로에 `reference`가 들어간 파일 0개 |
| 7 | PNG 회귀 | pose_01·pose_04·pose_07 × female × front 다운로드 PNG를 `tests/baselines/<id>_female_front.png`와 비교 | 평균 절대 차이 ≤ 1.5/255, 채널 차이 > 40인 픽셀 비율 ≤ 0.75 %. 기준 파일이 없으면 만들고 "baseline created, needs review"로 **실패** |

## 4. 캡처 방식 (테스트가 하는 일)

- **PNG 다운로드**: ego-browser의 실제 다운로드 이벤트(`page.waitForEvent("download")` + `saveAs`)를 씁니다. 앱은 blob URL + `<a download>` 클릭 같은 표준 방식으로 내려받으면 됩니다(`#download-png`가 사용자 클릭으로 직접 트리거). 900×1200은 화면 렌더가 아니라 **오프스크린 렌더**여야 창 크기·DPR에 상관없이 같은 결과가 나옵니다.
- **클립보드**: 실제 클립보드는 권한·포커스에 불안정해서, 페이지 로드 후 `navigator.clipboard.writeText`를 가로채 인자만 기록합니다(원본은 호출하지 않으며 즉시 resolve). 따라서 앱은 **버튼 클릭 시점에** `navigator.clipboard.writeText(...)`를 호출해야 합니다(모듈 로드 때 참조를 캐시해 두면 가로채지 못합니다). 반환 Promise를 기다려 "복사 완료" 표시를 해도 됩니다.
- **네트워크**: 문서 안의 `performance.getEntriesByType('resource')`를 마지막에 읽습니다(fetch·이미지·스크립트·XHR 포함, 버퍼 크기 5000).
- ego-browser 스크립트는 셸 환경변수를 상속하지 않으므로 URL·출력 디렉터리 같은 입력은 `tests/test_20_app.py`가 스크립트 앞에 `const CONFIG = {...};`로 붙여 stdin으로 넘깁니다.

## 5. 앱이 지켜야 할 그 밖의 것
- `/poses/reference/` 로 가는 요청을 만들지 않습니다(`meta.sourceImage` 미사용).
- 썸네일은 앱 로드 시 브라우저에서 렌더합니다. 외부 이미지·사전 렌더 PNG를 쓰지 않습니다.
- `ready` 전에는 클릭 가능한 요소가 없어도 되지만, 스크립트는 `ready` 이후에만 동작합니다.
