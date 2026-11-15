<!-- forge-slug: upper-sexy-3of4-fullsexy-standing-seated -->
<!-- task: 11 -->
<!-- tdd: off -->
<!-- priority: high -->
<!-- part: 3/4 -->
# 상반신·섹시 3/4: 전신 섹시 서기·앉기·무릎 P001–P045 (45종)

## Goal / Non-goals
- Goal: 전신 섹시계 중 서기 15종(P001–P015) + 앉기 15종(P016–P030) + 무릎 15종(P031–P045)을 신규 포즈 JSON+카탈로그로 추가한다. M자·기승위풍 등 한계 초과분은 근사로 저작하고 assumptions에 기록한다.
- Non-goals: 눕기·특수계는 4/4에서 한다. 원본 이미지 저장·재배포 안 함. 기존 파일 형식·스켈레톤 변경 안 함.

## Source of truth
- Glossary terms: 포즈 파일, 포즈 카탈로그, 정식 설명, 포즈 프롬프트 in .forge/CONTEXT.md
- Related ADRs: .forge/adr/261105-214739-rig-and-pose-schema-owned-by-other-team.md
- Definition of Done:
  - `ls poses/pose_*.json | wc -l` → 2/4 완료 후 대비 +45
  - catalog 항목 +45, schema 검증 통과
  - `pytest -q` passed, 신규 45종 limits·penetration 통과

## Work slices
- [ ] S1. P001–P045 포즈 JSON 45개 저작 (pose_167~pose_211) — completion criterion: 45개 파일 schema 검증 통과 (depends: 없음)
- [ ] S2. 카탈로그·프롬프트 45 항목 — completion criterion: catalog +45, prompt 생성 확인 (depends: S1)
- [ ] S3. 검증·회귀 — completion criterion: pytest passed, limits·penetration 전수 통과 (depends: S2)
