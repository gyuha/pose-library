<!-- forge-slug: pose-gallery-3d-1of2 -->
<!-- task: 1 -->
<!-- part: 1/2 -->
<!-- tdd: on -->
<!-- priority: high -->
# 포즈 갤러리 1/2: 포즈 8개, 포즈 카탈로그, 한국어 포즈 프롬프트 엔진

## Goal / Non-goals
- Goal: 갤러리에 쓸 포즈 파일 8개(기존 pose_01 포함)를 준비합니다. 한국어 포즈 카탈로그와, 포즈 파일·카탈로그·성별·앵글 프리셋을 받아 줄 단위 한국어 포즈 프롬프트를 만드는 순수 JS 모듈(`prompt/`)도 함께 만들고, 모두 명령어로 검증합니다.
- Non-goals:
  - 텍스트→포즈 파서, 관절 수동 조정, 영문 프롬프트(나중에 추가합니다. 그때 쉽게 붙일 수 있도록 문구 테이블만 언어별 파일로 분리합니다).
  - 웹앱(2/2에서 합니다).
  - `rig/`, `poses/schema.json`, `poses/pose_01_*.json`, `poses/reference/` 수정. 모두 '3D 인체 모델링' 팀 소유입니다.
  - 레퍼런스 사이트의 이미지나 데이터를 가져오거나 크롤링하는 일.
  - 기존 `tests/test_0*` 실패(예: test_08 bust) 수정.

## Source of truth
- Glossary terms: 포즈 파일, 포즈 카탈로그, 정식 설명, 포즈 프롬프트, 앵글 프리셋, 레퍼런스 사이트 (.forge/CONTEXT.md)
- Related ADRs: .forge/adr/261105-214739-rig-and-pose-schema-owned-by-other-team.md
- 합의 사항:
  - 프롬프트는 한국어만 만듭니다. 형태는 레이블을 붙인 8줄이고 순서는 `인물:` `앵글:` `자세:` `몸통:` `팔:` `다리:` `체중:` `시선:`입니다.
    - `인물:`에는 성별 문구(여성 인물 / 남성 인물)와 '전신'이 들어갑니다.
    - `자세:`는 카탈로그의 정식 설명입니다.
    - `몸통:`부터 `시선:`까지는 관절 회전에서 규칙으로 도출합니다. 축 의미는 `rig/joint_limits.json`의 `note`를 따릅니다(좌우는 캐릭터 기준).
  - 앵글 프리셋 5개:
    - 정면: yaw 0°
    - 옆: yaw 90°, 캐릭터 오른쪽
    - 사선: yaw 45°
    - 위: pitch +45°, 내려다봄
    - 아래: pitch −30°, 올려다봄
  - 포즈 구성: 기존 pose_01 + 신규 7개 = 서기 3 · 앉기 2 · 동작 3. 모두 `targetModels: ["female","male"]`입니다.
  - 역할 배분(orchestrator가 위임합니다):
    - poser: 포즈 파일과 카탈로그
    - prompter: `prompt/`
    - qa: `tests/`, `scripts/`
- 선행 조건: 사용자가 '3D 인체 모델링' 팀 rigger의 작업 완료를 확인한 뒤에만 시작합니다.
- Definition of Done:
  1. `GLTF_VALIDATOR_NODE_PATH=/private/tmp/pose-model-validator/node_modules PYTHONDONTWRITEBYTECODE=1 /tmp/pose-qa-venv/bin/python -m pytest tests/test_10_pose_files.py tests/test_11_pose_apply.py tests/test_12_pose_intersections.py tests/test_13_prompt.py -q -p no:cacheprovider` → exit 0
     - 작성 시점 상태: 파일이 없어 실패합니다(정상적인 사전 실패).
  2. `ls poses/pose_*.json | wc -l` → 8
     - 작성 시점 값: 1(pose_01만 있음).
  3. `cd prompt && node --test` → exit 0(node v24.13.0)
     - 작성 시점 상태: `prompt/`가 없어 실패합니다.
  4. `shasum -a 256 rig/male.glb rig/female.glb rig/joint_limits.json poses/schema.json poses/pose_01_contrapposto_hand_on_head.json`이 S1에서 기록한 값과 같습니다.
     - 회귀 가드라서 작성 시점에 통과해도 정상입니다. 다른 팀 파일을 건드리지 않았음을 보장합니다.
  5. UAT(사람 확인):
     - 사용자가 `tests/artifacts/pose_contact_sheet_female.png`와 `tests/artifacts/pose_contact_sheet_male.png`(8포즈 정면/사선)를 봅니다.
     - female·정면 기준 프롬프트 8개를 읽고, 정식 설명·도출 상세·실제 포즈 사이에 모순이 없는지 확인합니다.

## Work slices
- [ ] S1. orchestrator가 선행 조건을 확인합니다. 사용자에게 rigger 완료 여부를 묻고, DoD 4의 다섯 파일 SHA-256을 run 노트에 기록합니다. — completion criterion: run 노트에 사용자 확인 문구와 SHA-256 5개가 있습니다.
- [ ] S2. qa가 테스트를 먼저 씁니다. `rig/tools/rigcore.py`는 import만 하고 쓰지 않으며, `rig/` 아래에 파일을 만드는 도구(`check_limits.py` 등)는 실행하지 않습니다. `tests/requirements.txt`에 `jsonschema`를 추가합니다. — completion criterion: 다음 테스트 파일이 존재하고, 현재 상태에서는 포즈 개수·카탈로그·프롬프트 부재 때문에만 실패하며 pose_01 자체 검사는 통과합니다. (depends: S1)
  - `test_10_pose_files.py`
    - 모든 `poses/pose_*.json`이 `poses/schema.json`에 맞습니다.
    - id가 파일명과 같습니다.
    - 쿼터니언이 단위 길이입니다.
    - Euler XYZ 값이 `rig/joint_limits.json` 범위 안에 있습니다.
    - 포즈가 8개 이상입니다.
    - `poses/catalog.ko.json`이 `poses/catalog.schema.json`에 맞고, 카탈로그 id 집합이 포즈 파일 id 집합과 같습니다.
  - `test_11_pose_apply.py`
    - 각 포즈가 `rig/male.glb`와 `rig/female.glb` 모두에 적용됩니다.
    - 모르는 뼈가 없습니다.
    - 최저 발바닥 높이가 허용 오차 안에 있습니다. 허용 오차는 qa가 정하고 근거를 적습니다.
  - `test_12_pose_intersections.py`
    - 포즈 메시의 관통 검사를 합니다. 임계값과 pose_01 기준치는 qa가 정합니다.
    - 결과로 `tests/artifacts/pose_contact_sheet_{female,male}.png`를 씁니다.
- [ ] S3. poser가 `poses/catalog.schema.json`과 `poses/catalog.ko.json`을 씁니다. 항목마다 id, 한국어 이름, 태그, 정식 설명 1~2문장이 들어가고, 카탈로그는 pose_01을 포함해 8개 항목입니다. 신규 포즈 파일 7개(서기 2 · 앉기 2 · 동작 3)를 기존 스키마에 맞춰 씁니다. — completion criterion: `test_10`·`test_11`·`test_12`가 통과하고 DoD 2가 8입니다. (depends: S2)
- [ ] S4. prompter가 `prompt/`에 의존성 없는 ES 모듈을 만듭니다. — completion criterion: `cd prompt && node --test`가 exit 0이고, 8포즈 × 2성별 × 5앵글 = 80개 조합이 모두 8줄 레이블 형식으로 나옵니다. (depends: S3)
  - 공개 API: `buildPosePrompt({ pose, catalogEntry, gender, angle }) → string`, `ANGLE_PRESETS`
  - 문구 테이블은 `prompt/phrases.ko.js`에 둡니다.
  - 모르는 gender나 angle을 받으면 예외를 던집니다.
  - 같은 입력이면 항상 같은 출력을 냅니다.
  - 테스트를 먼저 씁니다: pose_01 기대 출력, 포즈별 스냅숏, 줄 순서, 예외.
- [ ] S5. qa가 `tests/test_13_prompt.py`를 씁니다. pytest에서 node로 `buildPosePrompt`를 호출하고, 80개 조합 각각을 검사합니다. — completion criterion: DoD 1의 네 테스트 파일이 모두 통과합니다. (depends: S4)
  - 8줄이고 레이블 순서가 맞습니다.
  - `자세:` 줄이 카탈로그 정식 설명과 같습니다.
  - `인물:`의 성별 문구와 `앵글:` 문구가 입력과 맞습니다.
  - 빈 줄이 없습니다.
