---
author: gyuha
decided: 2026-11-05 21:47
---
# 리깅 모델과 포즈 스키마는 '3D 인체 모델링' 팀의 산출물을 그대로 의존성으로 쓴다

같은 저장소에서 '3D 인체 모델링' 팀의 rigger가 `rig/male.glb`·`rig/female.glb`(표준 뼈 이름 스켈레톤 `pose-library-humanoid-v1`)와 `poses/schema.json`을 만들고 있었다. 포즈 갤러리 앱 팀(orchestrator 팀)의 poser도 `poses/`를 소유하도록 정의되어 있어 기준 문서가 둘로 갈라질 위험이 있었다. 그래서 앱은 `model/*.glb` 대신 `rig/*.glb`를 불러온다. 우리 poser가 `poses/`에 추가하는 것은 기존 스키마를 따르는 포즈 파일과, 한국어 이름·태그·정식 설명을 담은 사이드카 포즈 카탈로그(`poses/catalog.ko.json`과 그 스키마)뿐이다. 그 팀의 스키마, 포즈 파일, `rig/`는 수정하지 않는다. 스키마 변경이 필요하면 그 팀에 요청한다.

## Considered Options

- 우리 팀이 `poses/`를 인수하고 스키마를 고친다: 상대 팀 작업을 멈춰야 하고 팀 파일 정리가 필요해 기각했다.
- `model/*.glb`(DEF- 이름 55관절) 기준의 별도 스키마를 만든다: 같은 폴더에 기준 문서가 둘 생겨 기각했다.
