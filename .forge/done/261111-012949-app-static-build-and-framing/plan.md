<!-- forge-slug: app-static-build-and-framing -->
<!-- followup-id: fu-ed43684f3e5e -->
<!-- task: 4 -->
<!-- priority: medium -->
<!-- tdd: off -->
# 앱: 라이브 포즈 동기화 제거와 카메라 자동 프레이밍

## Goal / Non-goals
- Goal:
  - `/__pose_sync.json` 미들웨어와 그 fetch를 없애, 앱이 빌드 결과물(`app/dist`)만으로 동작하게 합니다.
  - 모든 포즈 × 앵글 프리셋 5개의 PNG·뷰에서 인물이 잘리지 않도록 카메라가 포즈 크기에 맞춰 거리와 대상점을 정하게 합니다(자동 프레이밍).
- Non-goals:
  - 포즈 데이터 변경(task 3), PNG 허용오차 재검토(task 5).
  - 디자인 변경과 새 기능.
  - `poses/`, `prompt/`, `rig/`, `.forge/loop-checks/` 수정.

## Source of truth
- Glossary terms: 포즈 썸네일, 앵글 프리셋 (.forge/CONTEXT.md)
- Related ADRs: .forge/adr/261105-214739-rig-and-pose-schema-owned-by-other-team.md
- 계약:
  - `tests/app_contract.md`가 기준입니다.
  - 앵글 프리셋의 yaw/pitch는 `ANGLE_PRESETS`와 ±1° 이내로 유지합니다. 자동 프레이밍은 거리와 대상점만 바꿉니다.
- Definition of Done:
  1. `bash .forge/loop-checks/c2_no_live_sync.sh` → exit 0
     - 작성 시점에는 exit 1입니다(files-with-live-sync=2).
  2. `bash .forge/loop-checks/c4_framing.sh` → exit 0
     - 작성 시점에는 exit 1입니다(framing-cases=0, 65개 이상 필요).
  3. `bash .forge/loop-checks/c1_static_e2e.sh` → exit 0
     - 회귀 가드입니다. 작성 시점에 이미 39 passed입니다. 지금은 fetch가 실패하면 빌드 데이터로 돌아가는 경로로 동작합니다.
  4. `bash .forge/loop-checks/c7_regression.sh` → exit 0
     - 회귀 가드입니다.

## Work slices
- [ ] S1. qa가 `tests/test_20_app.py`에 framing 케이스를 추가합니다. — completion criterion: `pytest --collect-only -k framing`이 포즈 수×5개 이상이고, 현재 앱에서 잘림이 있는 케이스는 실패합니다.
  - 모든 포즈 × 5앵글 × female에서 다운로드한 900×1200 PNG의 인물이 네 변 모두 1 % 이상 여백을 둬야 합니다.
  - 테스트 이름에 `framing`을 넣습니다.
  - `POSE_APP_URL` 경로에서도 동작해야 합니다.
- [ ] S2. app이 라이브 동기화(vite.config.js 플러그인, main.js의 `syncLivePosesIfAvailable`)를 제거하고 앵글 프리셋별 자동 프레이밍을 구현합니다. 적용 대상은 뷰, PNG, 썸네일입니다. — completion criterion: DoD 1~3이 통과합니다. (depends: S1)
- [ ] S3. qa가 프레이밍 변경으로 달라진 `tests/baselines/` 3장을 다시 만듭니다. orchestrator가 이미지를 열어 확인합니다. — completion criterion: DoD 4와 test_20 전체가 통과하고, orchestrator가 기준 이미지를 확인했다는 기록이 있습니다. (depends: S2)
