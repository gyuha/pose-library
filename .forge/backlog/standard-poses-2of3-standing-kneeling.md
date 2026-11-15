<!-- forge-slug: standard-poses-2of3-standing-kneeling -->
<!-- task: 7 -->
<!-- tdd: off -->
<!-- priority: high -->
<!-- part: 2/3 -->
# 표준 포즈 2/3: 서기·무릎꿇기 P015–P040 (24종)

## Goal / Non-goals
- Goal: 표준계 서기 14종(P015–P022,P024–P027,P029–P030) + 무릎꿇기 10종(P031–P040)을 신규 포즈 JSON+카탈로그로 추가한다.
- Non-goals: 앉기계·바닥계는 1/3·3/3에서 한다. 원본 이미지 저장·재배포 안 함. 스켈레톤 변경 안 함.

## Source of truth
- Glossary terms: 포즈 파일, 포즈 카탈로그, 정식 설명, 포즈 프롬프트 in .forge/CONTEXT.md
- Related ADRs: .forge/adr/261105-214739-rig-and-pose-schema-owned-by-other-team.md
- Definition of Done:
  - `ls poses/pose_*.json | wc -l` → 1/3 완료 후 대비 +24
  - catalog 항목 +24, 각 한국어 이름·태그·정식 설명 포함, schema 검증 통과
  - `pytest -q` passed, 신규 24종 limits·penetration 통과

## Work slices
- [ ] S1. 서기 14종 + 무릎꿇기 10종 JSON 저작 — completion criterion: 24개 파일 schema 검증 통과 (depends: 없음)
- [ ] S2. 카탈로그·프롬프트 24 항목 추가 — completion criterion: catalog +24, prompt 생성 확인 (depends: S1)
- [ ] S3. 검증·회귀 — completion criterion: pytest -q passed, limits·penetration 전수 통과 (depends: S2)
