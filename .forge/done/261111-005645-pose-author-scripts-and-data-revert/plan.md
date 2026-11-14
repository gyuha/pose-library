<!-- forge-slug: pose-author-scripts-and-data-revert -->
<!-- followup-id: fu-835ddfa85154 -->
<!-- task: 3 -->
<!-- priority: high -->
<!-- tdd: off -->
# 포즈 작성 스크립트 재현성 확보와 pose_05·pose_08 데이터 원복

## Goal / Non-goals
- Goal:
  - pose_02~08을 `scripts/pose_author/poses/pose_NN_<slug>.py --write`로 다시 만들 수 있게 합니다. pose_09~13은 이미 스크립트가 있습니다.
  - 테스트 카메라 때문에 바꿨던 데이터를 되돌립니다. pose_05의 루트 z 오프셋 −0.23 hipsHeight와 pose_08의 점프 높이 16 cm가 대상입니다.
- Non-goals:
  - 썸네일·PNG의 프레이밍(카메라 쪽 해결)은 task 4에서 합니다.
  - pose_02의 머리 회전은 바꾸지 않습니다. 실측 102.5°라 fu-2787을 종료했습니다.
  - pose_01과 `rig/`, `poses/schema.json`, `poses/README.md`, `poses/reference/`는 다른 팀 소유라 건드리지 않습니다.
  - `.forge/loop-checks/`는 수정하지 않습니다.

## Source of truth
- Glossary terms: 포즈 파일, 포즈 카탈로그, 정식 설명 (.forge/CONTEXT.md)
- Related ADRs: .forge/adr/261105-214739-rig-and-pose-schema-owned-by-other-team.md
- 소유권 예외(fg-loop 사용자 결정, 2026-11-11): 이 루프에 한해 poser가 `scripts/pose_author/poses/*.py`를 씁니다. `scripts/pose_author/lib.py`와 `tests/`는 qa 소유입니다.
- 형식과 기법 참고:
  - `.claude/skills/image-to-pose/SKILL.md` 2절(스크립트 형식)
  - `scripts/pose_author/examples/`(02~08의 원래 스크립트, pkl 방식)
  - `scripts/pose_author/poses/pose_09_hands_on_hips.py`(실행 예)
- Definition of Done:
  1. `bash .forge/loop-checks/c6_reproduce.sh` → exit 0
     - 작성 시점에는 exit 1입니다. pose_02~08 스크립트가 없습니다.
  2. `/tmp/pose-qa-venv/bin/python .forge/loop-checks/c5_pose_data.py` → exit 0
     - 작성 시점에는 exit 1입니다. 05 z=−0.2308, 08 최저점 female 0.155 m·male 0.165 m, 카탈로그에 "16cm"가 있습니다.
  3. `bash .forge/loop-checks/c7_regression.sh` → exit 0
     - 회귀 가드라서 작성 시점에 이미 통과합니다.

## Work slices
- [ ] S1. poser가 pose_02·03·04·06·07 스크립트를 `scripts/pose_author/poses/`에 씁니다. `--write`를 실행하면 현재 JSON과 정확히 같은 결과가 나와야 합니다. — completion criterion: c6에서 이 다섯 포즈가 일치합니다.
- [ ] S2. poser가 pose_05와 pose_08을 다시 만들고 스크립트를 씁니다. — completion criterion: c5와 c6이 exit 0입니다. (depends: S1)
  - pose_05는 루트 z 오프셋을 \|z\| ≤ 0.05 hipsHeight로 둡니다. 앉은 자세와 접지는 그대로 유지합니다.
  - pose_08은 두 발이 바닥에서 30 cm 이상 떠야 합니다(female·male 모두).
  - `catalog.ko.json`의 08 설명에서 "16cm"를 지우고 실제 값에 맞춥니다. 포즈 파일의 `meta.description`도 함께 맞춥니다.
- [ ] S3. orchestrator가 DoD 1~3을 다시 실행해 확인합니다. — completion criterion: 세 명령이 모두 exit 0입니다. (depends: S2)
