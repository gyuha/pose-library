<!-- forge-slug: upper-sexy-1of4-upper-cute -->
<!-- task: 9 -->
<!-- tdd: off -->
<!-- priority: high -->
<!-- part: 1/4 -->
# 상반신·섹시 1/4: 상반신 귀여움계 P001–P040 (40종)

## Goal / Non-goals
- Goal: 상반신 카테고리 중 귀여움계 25종(P001–P025: 하트·피스·고양이손 등 손 제스처 위주)과 가슴모으기계 15종(P026–P040)을 신규 포즈 JSON+카탈로그로 추가한다.
- Non-goals: P041 이후·섹시계는 2·3·4/4에서 한다. 원본 이미지 저장·재배포 안 함. 기존 86개 파일 형식·스켈레톤 변경 안 함.

## Source of truth
- Glossary terms: 포즈 파일, 포즈 카탈로그, 정식 설명, 포즈 프롬프트 in .forge/CONTEXT.md
- Related ADRs: .forge/adr/261105-214739-rig-and-pose-schema-owned-by-other-team.md
- Definition of Done:
  - `ls poses/pose_*.json | wc -l` → 86 대비 +40 (authoring 전 86 — Measured 2026-11-15)
  - catalog 항목 +40, 각 한국어 이름·태그·정식 설명 포함, schema 검증 통과
  - `pytest -q` (test_10~13) passed, 신규 40종 limits·penetration 통과

## Work slices
- [ ] S1. P001–P040 포즈 JSON 40개 저작 (pose_87~pose_126) — completion criterion: 40개 파일 schema 검증 통과 (depends: 없음)
- [ ] S2. 카탈로그·프롬프트 40 항목 — completion criterion: catalog +40, prompt 생성 확인 (depends: S1)
- [ ] S3. 검증·회귀 — completion criterion: pytest passed, limits·penetration 전수 통과 (depends: S2)
