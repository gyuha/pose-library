# Follow-ups

<!-- followup: fu-b7f76f5a1ea2 | source: pose-gallery-3d-1of2 | task: 1 | date: 2026-11-05 | status: open | taken: - -->
- 어깨 가중치 개선을 '3D 인체 모델링' 팀 rigger에 요청합니다(`upperarm~torso` 관통). 개선되면 test_12의 60 mm 완화를 25 mm로 되돌리고 팔짱 포즈를 추가합니다.
  Evidence: S2에서 임계값을 pose_01 실측(49~51 mm) 기준으로 완화했고, S3에서 팔짱 포즈가 60~80 mm 관통으로 탈락했습니다.

<!-- followup: fu-76df07c30d77 | source: pose-gallery-3d-1of2 | task: 1 | date: 2026-11-05 | status: taken | taken: 3 -->
- 포즈 작성 스크립트가 `/tmp/pose-author/`에만 있어 재현할 수 없습니다. 저장소 안의 보관 위치를 정해야 합니다(ADR상 poses/에는 포즈 파일과 카탈로그만 둡니다).
  Evidence: run.md S3 기록.

<!-- followup: fu-835ddfa85154 | source: pose-gallery-3d-1of2 | task: 1 | date: 2026-11-05 | status: taken | taken: 3 -->
- pose_05 루트 오프셋과 pose_08 점프 높이를 앱 카메라 기준으로 다시 봅니다.
  Evidence: 2026-11-06 UAT에서 pose_05는 정면 컨택트 시트에서 여전히 발이 잘렸습니다.

<!-- followup: fu-2787880b05d2 | source: pose-gallery-3d-1of2 | task: 1 | date: 2026-11-06 | status: dismissed | taken: - -->
- pose_02(뒤돌아보며 서기)는 렌더에서 머리 회전이 30~40° 정도라 정식 설명의 "어깨 너머로 뒤를 돌아본다"보다 약합니다. 회전을 키우거나 설명을 완화해야 합니다.
  Evidence: 2026-11-06 UAT 컨택트 시트 육안 확인.
  종료 사유(2026-11-11): rigcore 실측 결과 머리 앞방향이 캐릭터 오른쪽으로 102.5°(female·male)라 정식 설명과 맞습니다. 얼굴 없는 머리라 렌더에서 회전이 덜 보였던 것으로 판단합니다.

<!-- followup: fu-ed43684f3e5e | source: pose-gallery-3d-2of2 | task: 2 | date: 2026-11-06 | status: taken | taken: 4 -->
- 라이브 포즈 동기화 미들웨어(`/__pose_sync.json`)를 제거하고, 포즈가 바뀌면 다시 빌드하도록 정리합니다. test_20이 빌드 결과물만으로 검증되게 합니다.
  Evidence: app/vite.config.js·app/src/main.js:741. 계획에 없던 기능이고, test_20이 preview 서버의 라이브 경로로만 검증됐습니다.

<!-- followup: fu-7e05c32b843a | source: pose-gallery-3d-2of2 | task: 2 | date: 2026-11-06 | status: taken | taken: 5 -->
- PNG 회귀 허용오차(평균 1.5/255, 0.75 %)를 실제 기준 이미지로 다시 검토합니다(qa).
  Evidence: S5에서 qa가 데이터로 재검토하지 않았고, 기준 이미지는 테스트가 직접 생성했습니다.

<!-- followup: fu-cc11d6bdb1ac | source: pose-gallery-3d-2of2 | task: 2 | date: 2026-11-06 | status: open | taken: - -->
- 같은 저장소에서 여러 세션이 poses/를 동시에 쓰지 않도록 조율 규칙을 정합니다(image-to-pose 스킬 ↔ 갤러리 팀).
  Evidence: 2/2 실행 중 다른 세션이 pose_09~13을 추가하고 카탈로그 등록이 늦어 1/2 테스트가 일시적으로 깨졌습니다(1 failed, 4 errors).

<!-- followup: fu-5c08a1d2e7b4 | source: pose-author-scripts-and-data-revert | task: 3 | date: 2026-11-11 | status: open | taken: - -->
- pose_08 `meta.assumptions`의 두 번째 문장("contact on y = 0")은 공중 포즈와 맞지 않습니다. 문장을 고칩니다.
  Evidence: poser#CF11 보고. 원문을 그대로 두었습니다.

<!-- followup: fu-9c2ad41e7f08 | source: png-capture-contract | task: - | date: 2026-11-15 | status: open | taken: - -->
- 앱 로드 직후 메인 캔버스 버퍼가 최종 레이아웃과 불일치(stale: 1344×1632 vs 1344×1270) — 첫 리사이즈 후에야 일치합니다. 로드 시점 캡처와 리사이즈 후 캡처 크기가 달라질 수 있으니 app 쪽에서 초기 리사이즈 타이밍을 봅니다.
  Evidence: qa#C3D4 보고 (test_20 green 유지, 동일 세션 비교에는 무영향).

<!-- followup: fu-4d7b92c0a1e5 | source: png-capture-contract | task: - | date: 2026-11-15 | status: open | taken: - -->
- test_21 신호 판정이 최소값 게이트에서 하위1% 분위수로 변경됨 (pose_10/pose_32 등 의도적 variant 쌍이 최소값을 끌어내림). measurements.json에 min/below 목록 보존됨. 필요하면 최소값 게이트로 복원 검토합니다.
  Evidence: qa#C3D4 보고 (test_21 4/4 pass, p1: 6.58>4.5, 5.81%>2.25%).
