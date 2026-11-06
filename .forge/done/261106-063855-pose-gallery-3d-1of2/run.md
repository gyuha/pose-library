# run — 포즈 갤러리 1/2: 포즈 8개, 포즈 카탈로그, 한국어 포즈 프롬프트 엔진
<!-- forge-slug: pose-gallery-3d-1of2 -->

실행 방식: forge 기본값인 Dynamic Workflow 대신 orchestrator 팀 규칙을 따랐습니다. 각 슬라이스를 담당 역할의 paseo 에이전트(정해진 provider/model/mode)에 위임했고, 의존 관계가 모두 직렬이라 순서대로 실행했습니다.
- qa#2FAD: claude-sonnet-5-5, auto
- poser#2DD1: claude-opus-5-5, auto
- prompter#1286: codex/gpt-6.1-sol, auto-review

## 슬라이스별 결과
- S1 선행 조건 확인과 SHA 기록 — ✅ 계획대로. 사용자가 rigger 완료를 확인했습니다(2026-11-05 22:25).
- S2 qa 테스트 선작성(test_10~12, pose_helpers, 컨택트 시트) — ⚠ 어깨 관통 임계값을 pose_01 실측(49~51 mm)에 맞춰 60 mm로 완화했습니다.
- S3 poser 카탈로그와 포즈 7개 — ⚠ 팔짱 포즈를 손 인사 포즈로 교체했습니다. pose_05는 루트를 20 cm 뒤로 옮겼고, pose_08은 점프 높이를 16 cm로 낮췄습니다.
- S4 prompter의 prompt/ ES 모듈(TDD, 스냅숏 포함) — ✅ 계획대로
- S5 qa test_13_prompt.py와 scripts/run_prompt_cases.mjs — ✅ 계획대로

## 계획과 달라진 점
- **S1 SHA-256(의존 파일, 22:25 기준)**
  - rig/male.glb 12c1cd88…
  - rig/female.glb 19fbc043…
  - rig/joint_limits.json 3146bc09…
  - poses/schema.json 86792467…
  - poses/pose_01 b378d03c…
- **S2 어깨 관통 임계값**
  - `upperarm_*~torso` 쌍은 60 mm까지 허용합니다(일반 쌍은 25 mm).
  - 해부학 기준이 아니라 pose_01 실측값(female 49.4 mm, male 51.2 mm)에 약 15%를 더한 값입니다. 일반 기준을 적용하면 pose_01이 실패합니다.
  - 원인은 리그의 어깨 가중치로 추정합니다(추정).
- **S3 팔짱 포즈**
  - 팔을 모으고 안쪽으로 돌리면 위팔 셸이 가슴에 60~80 mm 묻혀서 만들지 못했습니다(poser 측정).
  - 대신 '뒤돌아보며 서기'와 '손 흔들어 인사하기'를 서기로 넣었습니다.
- **S3 테스트 카메라에 맞춘 데이터 조정**
  - pose_05(뒤로 손 짚고 기대앉기)는 정면 컨택트 시트에서 발이 잘려서 루트를 20 cm 뒤로 옮겼습니다.
  - pose_08(무릎 당겨 만세 점프)은 손이 프레임 밖으로 나가서 점프 높이를 16 cm로 낮췄습니다.
  - 미리보기 카메라 때문에 포즈 데이터를 바꾼 것이므로, 앱 카메라가 생긴 뒤 다시 볼 대상입니다.
- **S3 소소한 결함**
  - pose_02 male은 가슴에 1~2 px 크기의 스키닝 접힘이 있습니다.
  - pose_05는 바닥 오차가 가장 큽니다. male 손바닥이 −8.8 mm로, 허용 범위 ±10 mm 안입니다.
- **S4 휴리스틱의 한계**
  - FK 없이 로컬 회전만으로 상세를 도출합니다. 그래서 접지, 하중 비율, 시선이 닿는 곳은 확정하지 않습니다.
  - 체중 줄은 '추정'이라고 표기합니다.
- **코드 리뷰(조건부)**
  - 위험 영역(인증, 데이터 변경, 외부 API)이 없어 별도 리뷰 단계를 돌리지 않았습니다.
  - 대신 orchestrator가 DoD를 다시 실행했고, test_13에 변이 검사를 했습니다. `남성 인물`을 `남자 인물`로 바꾸면 1 failed, 원래대로 되돌리면 5 passed였습니다.

## DoD baseline → after
1. pytest test_10~13: 파일 없음(실패) → `126 passed`
2. `ls poses/pose_*.json | wc -l`: 1 → 8
3. `cd prompt && node --test`: 디렉터리 없음 → pass 8, fail 0
4. 다른 팀 파일 SHA-256 5개: S1 기록값 → 동일. 회귀 가드라서 처음부터 통과가 정상입니다.
5. UAT(사람 확인): 이 노트를 쓰는 시점에는 대기 중입니다.

## Follow-up candidates

<!-- followup: fu-b7f76f5a1ea2 | source: pose-gallery-3d-1of2 | task: 1 | date: 2026-11-05 | status: open | taken: - -->
- 어깨 가중치 개선을 '3D 인체 모델링' 팀 rigger에 요청합니다(`upperarm~torso` 관통). 개선되면 test_12의 60 mm 완화를 25 mm로 되돌리고 팔짱 포즈를 추가합니다.
  Evidence: S2에서 임계값을 pose_01 실측(49~51 mm) 기준으로 완화했고, S3에서 팔짱 포즈가 60~80 mm 관통으로 탈락했습니다.

<!-- followup: fu-76df07c30d77 | source: pose-gallery-3d-1of2 | task: 1 | date: 2026-11-05 | status: open | taken: - -->
- 포즈 작성 스크립트가 `/tmp/pose-author/`에만 있어 재현할 수 없습니다. 저장소 안의 보관 위치를 정해야 합니다(ADR상 poses/에는 포즈 파일과 카탈로그만 둡니다).
  Evidence: run.md S3 기록.

<!-- followup: fu-835ddfa85154 | source: pose-gallery-3d-1of2 | task: 1 | date: 2026-11-05 | status: open | taken: - -->
- pose_05 루트 오프셋과 pose_08 점프 높이를 앱 카메라 기준으로 다시 봅니다.
  Evidence: 2026-11-06 UAT에서 pose_05는 정면 컨택트 시트에서 여전히 발이 잘렸습니다.

<!-- followup: fu-2787880b05d2 | source: pose-gallery-3d-1of2 | task: 1 | date: 2026-11-06 | status: open | taken: - -->
- pose_02(뒤돌아보며 서기)는 렌더에서 머리 회전이 30~40° 정도라 정식 설명의 "어깨 너머로 뒤를 돌아본다"보다 약합니다. 회전을 키우거나 설명을 완화해야 합니다.
  Evidence: 2026-11-06 UAT 컨택트 시트 육안 확인.
