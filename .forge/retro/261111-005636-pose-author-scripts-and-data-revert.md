<!-- auto-retro: fg-loop -->
# 2026-11-11 — 포즈 작성 스크립트 재현성 확보와 pose_05·pose_08 데이터 원복

## 계획과 실제
- 계획대로 된 것: pose_02~08 재현 스크립트, pose_05 root z 원복, pose_08 점프 높이 ≥ 30 cm. c5·c6·c7 모두 통과했습니다.
- 달라진 점
  - 옛 pkl 방식 스크립트는 실행할 수 없어서 최종 각도를 그대로 담은 스크립트로 대신했습니다.
  - 카탈로그 설명을 바꾸자 `prompt/snapshots.ko.json`이 맞지 않아 c7이 실패했습니다. 계획에 없던 prompter 작업이 필요했습니다.

## 배운 점
- 다음에 다르게 할 것
  - 정식 설명(카탈로그)을 바꾸는 계획에는 prompt 스냅숏 재생성 슬라이스를 처음부터 넣습니다.
  - 포즈 작성 스크립트는 처음부터 `--write`로 재현 가능한 형식으로 저장소에 둡니다. /tmp에 둔 pkl 방식 스크립트는 다시 실행할 수 없게 되었습니다.

## 문서 갱신
- 검토 전입니다(자동 회고).

## Follow-up candidates

<!-- followup: fu-5c08a1d2e7b4 | source: pose-author-scripts-and-data-revert | task: 3 | date: 2026-11-11 | status: open | taken: - -->
- pose_08 `meta.assumptions`의 두 번째 문장("contact on y = 0")은 공중 포즈와 맞지 않습니다. 문장을 고칩니다.
  Evidence: poser#CF11 보고. 원문을 그대로 두었습니다.
