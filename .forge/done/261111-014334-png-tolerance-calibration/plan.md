<!-- forge-slug: png-tolerance-calibration -->
<!-- followup-id: fu-7e05c32b843a -->
<!-- task: 5 -->
<!-- priority: low -->
<!-- tdd: off -->
# PNG 회귀 허용오차를 측정 데이터로 보정

## Goal / Non-goals
- Goal: test_20의 PNG 회귀 허용오차(평균 1.5/255, 0.75 %)가 렌더 노이즈보다 충분히 크고 실제 포즈 차이보다 충분히 작다는 것을 측정 테스트로 증명합니다. 필요하면 허용오차를 고칩니다.
- Non-goals: 앱과 포즈 변경, 기준 이미지 정책 변경, `.forge/loop-checks/` 수정.

## Source of truth
- Glossary terms: 포즈 썸네일 (.forge/CONTEXT.md)
- Related ADRs: .forge/adr/261105-214739-rig-and-pose-schema-owned-by-other-team.md
- Definition of Done:
  1. `bash .forge/loop-checks/c3_png_tolerance.sh` → exit 0
     - 작성 시점에는 exit 1입니다. test_21이 없습니다.
  2. `bash .forge/loop-checks/c1_static_e2e.sh` → exit 0 (회귀 가드)
  3. `bash .forge/loop-checks/c7_regression.sh` → exit 0 (회귀 가드)

## Work slices
- [ ] S1. qa가 `tests/test_21_png_tolerance.py`를 씁니다. 허용오차 상수는 `test_20_app`에서 import합니다. 허용오차를 바꿨다면 test_20의 상수를 고치고 근거를 주석으로 남깁니다. — completion criterion: DoD 1~3이 통과합니다.
  - 노이즈 하한: 같은 상태를 3번 이상 렌더해 차이를 잽니다. 성별 왕복 전환 뒤와 창 크기 변경 뒤의 렌더를 포함합니다.
  - 신호: 서로 다른 포즈끼리 female·front PNG 차이의 최솟값을 잽니다.
  - 단언: 노이즈 < 허용오차/3, 그리고 허용오차×3 < 최소 신호. 평균 지표와 픽셀 비율 지표 각각에 대해 확인합니다.
