# Follow-ups

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
