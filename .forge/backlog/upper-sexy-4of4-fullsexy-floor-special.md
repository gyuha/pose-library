<!-- forge-slug: upper-sexy-4of4-fullsexy-floor-special -->
<!-- task: 12 -->
<!-- tdd: off -->
<!-- priority: high -->
<!-- part: 4/4 -->
# 상반신·섹시 4/4: 전신 섹시 눕기·특수 P046–P080 (35종) + 갤러리 마감

## Goal / Non-goals
- Goal: 전신 섹시계 중 눕기 20종(P046–P065) + 특수 15종(P066–P080: 브리지·스플릿·망구리가에시 등)을 한계 내 근사로 저작하고, 합계 246종으로 앱 갤러리·빌드를 확인한다.
- Non-goals: 2인 포즈는 범위 밖. 원본 이미지 저장·재배포 안 함. 스켈레톤 변경 안 함.

## Source of truth
- Glossary terms: 포즈 파일, 포즈 카탈로그, 정식 설명, 포즈 프롬프트, 포즈 썸네일, 앵글 프리셋 in .forge/CONTEXT.md
- Related ADRs: .forge/adr/261105-214739-rig-and-pose-schema-owned-by-other-team.md
- Definition of Done:
  - `ls poses/pose_*.json | wc -l → 246` 이상, catalog 246 항목 이상 (authoring 전 86 — Measured 2026-11-15)
  - `pytest -q` passed, 전수 limits·penetration 통과
  - `npm run build --prefix app` exit 0, 빌드 갤러리에서 246개 선택·프롬프트 복사 가능

## Work slices
- [ ] S1. 눕기 20종 + 특수 15종 JSON 저작 (pose_212~pose_246) — completion criterion: 35개 파일 schema 검증 통과 (depends: 없음)
- [ ] S2. 카탈로그·프롬프트 35 항목 — completion criterion: catalog 합계 246, prompt 생성 확인 (depends: S1)
- [ ] S3. 전수 검증·앱 빌드 — completion criterion: pytest passed, app build exit 0, 갤러리 246개 노출 확인 (depends: S2)
