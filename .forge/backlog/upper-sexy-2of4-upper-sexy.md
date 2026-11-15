<!-- forge-slug: upper-sexy-2of4-upper-sexy -->
<!-- task: 10 -->
<!-- tdd: off -->
<!-- priority: high -->
<!-- part: 2/4 -->
# 상반신·섹시 2/4: 상반신 섹시계 P041–P080 (40종)

## Goal / Non-goals
- Goal: 상반신 카테고리 중 가슴모으기계 10종(P041–P050) + 노골계 30종(P051–P080)을 신규 포즈 JSON+카탈로그로 추가한다. 접촉·노출 서술은 과장 없이 축소 서술하고 assumptions에 기록한다.
- Non-goals: 섹시계(전신)는 3·4/4에서 한다. 원본 이미지 저장·재배포 안 함. 기존 파일 형식·스켈레톤 변경 안 함.

## Source of truth
- Glossary terms: 포즈 파일, 포즈 카탈로그, 정식 설명, 포즈 프롬프트 in .forge/CONTEXT.md
- Related ADRs: .forge/adr/261105-214739-rig-and-pose-schema-owned-by-other-team.md
- Definition of Done:
  - `ls poses/pose_*.json | wc -l` → 1/4 완료 후 대비 +40
  - catalog 항목 +40, schema 검증 통과
  - `pytest -q` passed, 신규 40종 limits·penetration 통과

## Work slices
- [ ] S1. P041–P080 포즈 JSON 40개 저작 (pose_127~pose_166) — completion criterion: 40개 파일 schema 검증 통과 (depends: 없음)
- [ ] S2. 카탈로그·프롬프트 40 항목 — completion criterion: catalog +40, prompt 생성 확인 (depends: S1)
- [ ] S3. 검증·회귀 — completion criterion: pytest passed, limits·penetration 전수 통과 (depends: S2)
