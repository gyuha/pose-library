# 포즈 라이브러리

캐릭터 포즈를 3D 마네킹으로 보여 주고, 이미지와 자연어 프롬프트로 내보내는 앱.
라이브 데모: https://gyuha.com/pose-library/

원본 포즈 갤러리(ai-pose-gallery.pages.dev)를 한 장씩 참고해 직접 만든 관절 회전값 246개를 수록. 저장소에는 외부 이미지를 넣지 않습니다.

## 구성

| 폴더 | 내용 |
|---|---|
| `poses/` | 포즈 JSON 246개 + 한국어 카탈로그(`catalog.ko.json`). 형식은 `poses/README.md` |
| `rig/` | 55조인트 스켈레톤(`pose-library-humanoid-v1`) GLB(male/female)와 검사 도구. 상세는 `rig/README.md` |
| `prompt/` | 포즈 JSON → 8줄 한국어 프롬프트 ES 모듈. 사용법은 `prompt/README.md` |
| `app/` | three.js 웹앱 (갤러리 선택 · 3D 미리보기 · PNG 다운로드 · 프롬프트 복사) |
| `tests/` | pytest 스위트 + 앱 E2E. 계약은 `tests/app_contract.md` |
| `scripts/` | 포즈 작성 헬퍼 |

## 실행

`task` (go-task) 기준입니다. 처음이면 venv·의존성부터 준비됩니다.

```sh
task web      # 빌드 후 http://0.0.0.0:4173/pose-library/ 서빙
task dev      # 개발 서버 (HMR)
task verify   # 전체 게이트: 포즈 73개+ · pytest · 빌드 · dist 일치
task test     # pytest test_10~13 + prompt 테스트
task test:e2e # preview 기동 → E2E → 서버 정리의 원샷 실행
task clean    # dist·캐시 정리
```

개별 명령은 `Taskfile.yml`을 보세요.

## 포즈 데이터 한눈에

- 한 파일 = 정지 포즈 하나, male/female GLB에 그대로 적용 (회전은 rest 로컬 프레임 기준, 이동은 골반 높이 비율)
- `bones`에 없는 뼈는 rest, 좌우는 캐릭터 자신의 기준
- 카탈로그 항목의 정식 설명이 프롬프트 첫머리, 관절 상세·성별·앵글 문구가 뒤따름
- 관절 한계 초과 포즈는 한계 내 근사로 저작하고 `meta.assumptions`에 기록

## 테스트

- `test_00~09`: GLB·스켈레톤·가중치 (모델 기반)
- `test_10~13`: 포즈 파일·적용·관통·프롬프트 계약
- `test_20`: 앱 E2E (캔버스 캡처 다운로드·태그 검색·프롬프트 복사)
- `test_21`: PNG 허용오차 (실측 기반)

## 배포

`main` 푸시 시 `.github/workflows/pages.yml`이 `app/dist`를 빌드해 GitHub Pages에 배포합니다.
