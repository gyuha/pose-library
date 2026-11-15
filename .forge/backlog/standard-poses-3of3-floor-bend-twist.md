<!-- forge-slug: standard-poses-3of3-floor-bend-twist -->
<!-- task: 8 -->
<!-- tdd: off -->
<!-- priority: high -->
<!-- part: 3/3 -->
# 표준 포즈 3/3: 바닥·숙임·틀기 P041–P079 (35종)

## Goal / Non-goals
- Goal: 횡좌·여성좌 8종(P041–P048) + 눕기 9종(P049–P052,P054,P056–P059) + 쪼그림 6종(P061–P066) + 앞숙임 6종(P067–P072) + 젖힘·틀기 6종(P073–P075,P077–P079)을 추가해 표준 73종을 완성하고 앱 갤러리·빌드를 확인한다.
- Non-goals: 2인·선정계는 범위 밖. 원본 이미지 저장·재배포 안 함. 스켈레톤 변경 안 함.

## Source of truth
- Glossary terms: 포즈 파일, 포즈 카탈로그, 정식 설명, 포즈 프롬프트, 포즈 썸네일, 앵글 프리셋 in .forge/CONTEXT.md
- Related ADRs: .forge/adr/261105-214739-rig-and-pose-schema-owned-by-other-team.md
- Definition of Done:
  - `ls poses/pose_*.json | wc -l → 73` 이상, catalog 73 항목 이상 (authoring 전 13 — Measured 2026-11-14)
  - `pytest -q` passed, 전수 limits·penetration 통과
  - `npm run build --prefix app` exit 0, 빌드 갤러리에서 73개 선택·프롬프트 복사 가능

## Work slices
- [ ] S1. 바닥·숙임·틀기 35종 JSON 저작 — completion criterion: 35개 파일 schema 검증 통과 (depends: 없음)
- [ ] S2. 카탈로그·프롬프트 35 항목 추가 — completion criterion: catalog 합계 73, prompt 생성 확인 (depends: S1)
- [ ] S3. 전수 검증·앱 빌드 — completion criterion: pytest passed, app build exit 0, 갤러리 73개 노출 확인 (depends: S2)
