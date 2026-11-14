# run — PNG 회귀 허용오차를 측정 데이터로 보정
<!-- forge-slug: png-tolerance-calibration -->

실행: fg-loop 무인 실행. qa#59C8(opencode/deepseek-v4.1-flash, build)에 맡겼습니다.

## 슬라이스별 결과
- S1 qa가 tests/test_21_png_tolerance.py를 작성하고 측정했습니다 — ✅ 계획대로. 측정값이 기존 허용오차 양쪽 조건을 모두 만족해서 상수는 바꾸지 않았습니다.

## 계획과 달라진 점
- 노이즈는 평균 0.0000, 픽셀 비율 0 %였습니다. 같은 상태 4장(성별 왕복, 뷰포트 변경 포함)이 바이트까지 같았습니다.
- 신호 최솟값은 평균 9.2066, 픽셀 비율 8.41 %입니다(pose_02 ↔ pose_06).
- 기존 허용오차 1.5와 0.75 %가 노이즈와 신호 사이에 들어갑니다.

## DoD baseline → after
1. c3_png_tolerance: exit 1(test_21 없음) → exit 0(3 passed)
2. c1_static_e2e: exit 0 → exit 0(104 passed). 회귀 가드입니다.
3. c7_regression: exit 0 → exit 0(196 passed, test_20 cases=104). 회귀 가드입니다.
