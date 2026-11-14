<!-- forge-slug: pose-gallery-3d-2of2 -->
<!-- task: 2 -->
<!-- part: 2/2 -->
<!-- tdd: on -->
# 포즈 갤러리 2/2: Vite three.js 웹앱(썸네일 클릭 → 3D 포즈 · PNG 다운로드 · 프롬프트 복사)

## Goal / Non-goals
- Goal: `app/`에 Vite + three.js 웹앱을 만듭니다. 사용자가 포즈 썸네일을 누르면 3D 마네킹이 그 포즈를 취하고, 현재 뷰를 PNG로 내려받거나 한국어 포즈 프롬프트를 클립보드에 복사할 수 있어야 합니다. 검증은 ego-browser로 자동화합니다.
- Non-goals:
  - 텍스트→포즈, 관절 수동 조정, 영문 프롬프트, 5앵글 일괄 다운로드.
  - 포즈의 `meta.sourceImage`(레퍼런스 이미지)를 표시하거나 앱 번들·배포물에 포함하는 일.
  - `rig/`, `poses/`, `prompt/`, `model/` 수정. 앱에는 모두 읽기 전용 의존성입니다.
  - 레퍼런스 사이트의 이미지나 데이터 사용.
  - 배포 설정.

## Source of truth
- Glossary terms: 포즈 썸네일, 포즈 파일, 포즈 카탈로그, 포즈 프롬프트, 앵글 프리셋, 레퍼런스 사이트 (.forge/CONTEXT.md)
- Related ADRs: .forge/adr/261105-214739-rig-and-pose-schema-owned-by-other-team.md
- 합의 사항:
  - 레이아웃
    - 좌: 썸네일 그리드, 태그 필터 드롭다운 하나, 남/여 전역 토글(기본 female)
    - 우: 항상 보이는 3D 패널. OrbitControls, 앵글 프리셋 버튼 5개, [PNG 다운로드], 8줄 프롬프트 표시, [프롬프트 복사]
  - 포즈 썸네일은 앱 로드 시 브라우저에서 정면 앵글로 렌더하며, 현재 성별을 따릅니다. 미리 만든 PNG 파일은 없습니다.
  - PNG 다운로드: 현재 카메라 그대로 3:4, 900×1200, 밝은 단색 배경으로 한 장을 저장합니다.
  - 프롬프트: `prompt/`의 `buildPosePrompt({pose, catalogEntry, gender, angle})` 출력을 그대로 표시하고 복사합니다. 카메라가 프리셋에서 벗어나면 가장 가까운 프리셋을 앵글로 씁니다.
  - 스택: Vite(`app/package.json`), three.js 고정 버전. `app/`이 Vite 루트이고, `rig/`·`poses/`·`prompt/`는 `server.fs.allow`와 `import.meta.glob`으로 읽습니다.
  - 포즈 적용 규칙은 rest 기준 로컬 쿼터니언과 hipsHeight 비율 루트 이동이며, `rig/tools/rigcore.py`의 FK와 같은 결과를 내야 합니다.
  - 검증 도구는 ego-browser입니다(`ego-browser nodejs`로 스크립트 구동). 화면 전체 스크린샷은 창 크기나 DPR에 따라 흔들리므로, 회귀 비교는 캔버스 PNG 출력을 허용 오차를 두고 비교합니다.
  - 역할 배분(orchestrator가 위임합니다): app은 `app/`, qa는 `tests/`와 `scripts/`.
- 선행 조건: 1/2가 봉인되어 있어야 합니다(soft order).
- Definition of Done:
  1. `cd app && npm ci && npm run build` → exit 0
     - 작성 시점 상태: `app/`이 없어 실패합니다.
  2. `PYTHONDONTWRITEBYTECODE=1 /tmp/pose-qa-venv/bin/python -m pytest tests/test_20_app.py -q -p no:cacheprovider` → exit 0
     - 작성 시점 상태: 파일이 없어 실패합니다.
  3. `shasum -a 256 rig/*.glb rig/joint_limits.json poses/*.json prompt/*.js`가 S1에서 기록한 값과 같습니다.
     - 회귀 가드라서 작성 시점에 통과해도 정상입니다.
  4. UAT(사람 확인): 사용자가 ego-browser로 앱을 열어 다음을 직접 확인합니다.
     - 썸네일 클릭 → 포즈 적용
     - 남/여 전환
     - 앵글 프리셋 5개
     - PNG 저장
     - 복사한 프롬프트를 붙여 넣은 결과

## Work slices
- [ ] S1. orchestrator가 1/2 봉인 여부를 확인하고 DoD 3 대상 파일의 SHA-256을 run 노트에 기록합니다. — completion criterion: run 노트에 SHA-256 목록이 있습니다.
- [ ] S2. qa가 테스트를 먼저 씁니다. `scripts/app_uat.js`(ego-browser nodejs용)와 `tests/test_20_app.py`(vite build·preview를 띄우고 스크립트를 호출)입니다. — completion criterion: 두 파일이 존재하고, 앱이 없는 현재 상태에서 test_20이 앱 부재 때문에 실패합니다. (depends: S1)
  - 검사 항목:
    - 모든 썸네일을 클릭하면 선택된 포즈 id가 바뀝니다.
    - 포즈마다 three.js의 관절 월드 위치가 rigcore `pose_globals` 결과와 1 mm 이내로 일치합니다. male과 female 모두 검사합니다.
    - PNG 다운로드 이벤트가 900×1200 PNG를 내놓습니다.
    - 클립보드 텍스트가 현재 상태(포즈·성별·앵글)의 `buildPosePrompt` 출력과 같습니다.
    - 앵글 프리셋 5개에서 카메라가 맞게 바뀝니다.
    - `/poses/reference/` 경로로 가는 네트워크 요청이 0건입니다.
    - 캔버스 PNG가 `tests/baselines/`와 허용 오차 안에서 일치합니다. 기준 이미지는 첫 생성 후 사용자 검토를 받습니다.
  - 관절 위치 비교를 위해 앱에 읽기 전용 디버그 훅(예: `window.__poseApp`)이 필요하면 그 인터페이스를 테스트에 명시합니다.
- [ ] S3. app이 Vite 골격을 만듭니다. `rig/{male,female}.glb`를 불러오고, 포즈 파일을 rigcore와 같은 규칙으로 적용하며, S2가 명시한 디버그 훅을 넣습니다. — completion criterion: DoD 1이 통과하고 test_20의 관절 위치 일치 항목이 통과합니다. (depends: S2)
- [ ] S4. app이 화면 기능을 만듭니다. — completion criterion: DoD 2가 통과합니다. (depends: S3)
  - 썸네일 그리드: 브라우저 즉석 렌더, 현재 성별을 따름
  - 태그 필터
  - 남/여 전역 토글
  - 앵글 프리셋 5개
  - 900×1200 PNG 다운로드
  - 8줄 프롬프트 표시와 `navigator.clipboard.writeText` 복사(복사 완료 표시 포함)
  - `meta.sourceImage`는 쓰지 않습니다.
- [ ] S5. qa가 캔버스 기준 이미지(`tests/baselines/`)를 처음 생성하고, 사용자가 검토·승인합니다. — completion criterion: 사용자가 승인한 기준 이미지로 DoD 2가 다시 통과합니다. (depends: S4)
