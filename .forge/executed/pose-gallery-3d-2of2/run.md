# run — 포즈 갤러리 2/2: Vite three.js 웹앱(썸네일 클릭 → 3D 포즈 · PNG 다운로드 · 프롬프트 복사)
<!-- forge-slug: pose-gallery-3d-2of2 -->

실행 방식: 1/2와 같습니다. 슬라이스를 역할별 paseo 에이전트에 직렬로 위임했습니다.
- qa#2FAD: claude-sonnet-5-5, auto
- app#BB93: antigravity/gemini-4-argon-high, full-access

## 슬라이스별 결과
- S1 의존 파일 SHA-256 기록(06:39, 17개) — ⚠ 실행 중 다른 세션이 poses/와 prompt/index.test.js를 바꿔 DoD 3 판정 범위를 좁혔습니다.
- S2 qa: app_uat.js(ego-browser), test_20_app.py, app_contract.md 선작성 — ✅ 계획대로(목 앱으로 테스트 장치 검증)
- S3 app: Vite 골격, GLB 로드, 포즈 적용, 디버그 훅 — ✅ 관절 위치가 rigcore와 1 mm 이내로 일치(모든 포즈 × 2성별)
- S4 app: 그리드·필터·토글·앵글 5개·PNG·복사 — ⚠ 요청하지 않은 '라이브 포즈 동기화' 미들웨어(`/__pose_sync.json`)를 추가했습니다.
- S5 기준 이미지 — ⚠ qa가 따로 만들지 않았습니다. app 에이전트가 test_20을 처음 실행할 때 테스트가 직접 `tests/baselines/` 3장을 생성했습니다. 사용자 검토는 UAT에서 받습니다.

## 계획과 달라진 점
- **동시 세션의 변경**
  - 다른 세션(image-to-pose 스킬)이 실행 도중 `poses/pose_09·10·11·12·13`과 카탈로그 항목을 추가하고 `prompt/index.test.js`를 수정했습니다.
  - 한때 카탈로그가 등록되지 않은 상태라 1/2 테스트가 깨졌습니다(1 failed, 4 errors). 지금은 다시 모두 통과합니다(196 passed).
  - 사용자 결정(2026-11-06): 다른 세션이 마무리하고, DoD 3은 `rig/*.glb`, `rig/joint_limits.json`, `prompt/index.js`, `prompt/phrases.ko.js`만으로 판정합니다.
- **라이브 포즈 동기화 미들웨어** (`app/vite.config.js`, `app/src/main.js:741`)
  - vite dev/preview 서버가 요청 시점의 `poses/`를 읽어 빌드에 들어간 포즈 목록을 덮어씁니다.
  - 정적 배포에서는 fetch가 실패하고 빌드 시점 데이터로 돌아갑니다.
  - 문제: test_20은 preview 서버로 돌기 때문에, 이 경로 대신 '빌드 결과물만'으로 동작하는지는 검증하지 못했습니다.
  - 계획에 없던 기능이라 후속 정리 후보로 둡니다.
- **기준 이미지 허용오차**(평균 1.5/255, 0.75 %)는 실제 데이터로 다시 검토하지 않았습니다. qa가 S5에서 할 일이었습니다.
- **코드 리뷰(조건부)**
  - 인증, 데이터 변경, 외부 API 같은 위험 영역은 없습니다.
  - orchestrator가 vite.config.js와 main.js의 동기화 경로를 직접 읽어 위 내용을 확인했습니다.

## DoD baseline → after
1. `cd app && npm ci && npm run build`: app/ 없음 → exit 0(vite 6.2.1, three 0.174.0, 청크 크기 경고만 있음)
2. `pytest tests/test_20_app.py`: app/ 없음으로 35 failed → `39 passed`
3. SHA 불변(범위 축소): rig/*.glb, rig/joint_limits.json, prompt/index.js, prompt/phrases.ko.js가 S1과 같습니다. poses/*.json과 prompt/index.test.js는 다른 세션이 바꿔 판정에서 제외했습니다.
4. UAT: 사용자 통과(2026-11-06). 기준 이미지 3장도 승인했습니다.

## Follow-up candidates
- 라이브 포즈 동기화 미들웨어를 제거하고, 포즈가 바뀌면 다시 빌드하도록 정리합니다. test_20이 빌드 결과물만으로 검증되게 합니다.
- PNG 회귀 허용오차를 실제 기준 이미지로 다시 검토합니다(qa).
- 같은 저장소에서 여러 세션이 poses/를 동시에 쓰지 않도록 조율 규칙을 정합니다(image-to-pose 스킬 ↔ 갤러리 팀).
