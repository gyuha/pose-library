<!-- forge-slug: standard-poses-1of3-seated -->
<!-- task: 6 -->
<!-- tdd: off -->
<!-- priority: high -->
<!-- part: 1/3 -->
# 표준 포즈 1/3: 앉기계 P001–P014 (14종)

## Goal / Non-goals
- Goal: 전신 표준계 중 앉기계 14종(P001–P014)을 원본 한 장씩 참고로 신규 포즈 JSON+카탈로그로 추가한다.
- Non-goals: 서기·무릎꿇기·바닥계는 2/3·3/3에서 한다. 원본 이미지 저장·재배포 안 함. 기존 13개 파일 형식·스켈레톤 변경 안 함.

## Source of truth
- Glossary terms: 포즈 파일, 포즈 카탈로그, 정식 설명, 포즈 프롬프트 in .forge/CONTEXT.md
- Related ADRs: .forge/adr/261105-214739-rig-and-pose-schema-owned-by-other-team.md
- Definition of Done:
  - `ls poses/pose_*.json | wc -l` → 14 이상 증가 (authoring 전 13 — Measured 2026-11-14)
  - `python3 -c "import json; print(len(json.load(open('poses/catalog.ko.json'))['poses']))"` → 기존 대비 +14 (authoring 전 13)
  - P001–P014 각 항목에 한국어 이름·태그·정식 설명 포함, `poses/schema.json` 검증 통과
  - `pytest -q` passed, 신규 14종 `check_limits`·`check_penetration` 통과

## Work slices
- [ ] S1. P001–P014 포즈 JSON 14개 저작 — completion criterion: 14개 파일이 schema 검증 통과, bones 미기재는 rest로 처리 (depends: 없음)
- [ ] S2. 카탈로그·프롬프트 14 항목 추가 — completion criterion: catalog.ko.json +14, prompt 모듈에서 정식 설명+구조화 상세 생성 확인 (depends: S1)
- [ ] S3. 검증·회귀 — completion criterion: pytest -q passed, limits·penetration 전수 통과 (depends: S2)
