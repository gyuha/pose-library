---
name: image-to-pose
description: 사람 포즈 이미지(사용자가 준 사진·일러스트·포즈 갤러리 화면 캡처)를 이 저장소의 3D 마네킹(rig/female.glb, rig/male.glb)에 적용할 포즈 파일(poses/pose_NN_*.json)로 바꾸고 포즈 카탈로그에 등록한다. 등록된 포즈는 갤러리 웹앱(app/)에서 선택하면 3D 모델이 그 포즈를 취한다. "이 이미지 포즈로 만들어줘", "이미지를 포즈 파일로", "포즈 추가", "image to pose", "ai-pose-gallery 포즈를 3D로" 같은 요청에 쓴다.
---

# image-to-pose — 이미지 → 포즈 파일

이미지 한 장을 보고 관절 회전을 직접 정한 뒤 렌더로 대조하며 고치는 스킬입니다. 관절 회전은 Claude가 이미지를 보고 판단하고, 외부 포즈 추정 모델은 쓰지 않습니다. 결과물은 다음 세 가지입니다.

- 포즈 파일 `poses/pose_NN_<slug>.json`
- 저작 스크립트 `scripts/pose_author/poses/pose_NN_<slug>.py` (재현용)
- 카탈로그 항목 `poses/catalog.ko.json`

"포즈를 고르면 3D 모델이 그 포즈를 취하는" 화면은 갤러리 웹앱(forge 계획 `pose-gallery-3d-2of2`, `app/`)이 맡습니다. 웹앱은 `poses/*.json`과 카탈로그를 `import.meta.glob`으로 읽으므로, 이 스킬로 등록한 포즈는 별도 작업 없이 썸네일 목록에 나타납니다. `app/`이 아직 없다면 사용자에게 그 사실을 알리고, 결과는 렌더 시트로 보여 줍니다.

```
이미지 해석 → 저작 스크립트 → 검사(관절 한계·접지·관통) → 렌더 대조
                   ↑                                      ↓ 차이 큼
                   └──────────────────────────────────────┘
→ 포즈 파일 쓰기 → 렌더를 보고 정식 설명 작성 → 카탈로그 등록 → 스냅샷 갱신 → DoD 검사
```

## 지켜야 할 경계

- **입력은 사용자가 준 이미지, 또는 사용자가 지정한 레퍼런스 사이트(ai-pose-gallery.pages.dev)의 개별 이미지입니다.** 사이트 이용 조건이 일괄 다운로드(도구를 이용한 자동 수집 포함)와 재배포를 금지하므로, 사용자가 고른 몇 장만 한 장씩 `/tmp/aipg/img/`로 받습니다. 성적인 카테고리(`セクシー系`, `2人絡み` 등)는 고르지 않습니다(`.forge/CONTEXT.md`의 '레퍼런스 사이트').
- **입력 이미지를 저장소에 넣지 않습니다.** `meta.sourceImage`는 비워 두고, `meta.assumptions`에 출처(사이트 이미지라면 사이트 id)와 "저장소 미포함"을 적습니다.
- **다른 팀 소유 파일은 읽기만 합니다.** `rig/` 전체, `poses/schema.json`, 기존 `poses/pose_0*.json`, `poses/reference/`가 해당합니다(ADR `261105-214739`). `rig/tools/check_limits.py`와 `render_pose.py`는 `rig/` 아래에 파일을 쓰므로 직접 실행하지 않습니다. 같은 검사는 `scripts/pose_author/lib.py`로 합니다.
- **테스트 기준을 완화해 통과시키지 않습니다.** 리그로 만들 수 없는 포즈(예: 팔짱. 위팔 셸이 가슴에 60~80 mm 묻힘)는 가장 가까운 대안을 사용자에게 제안합니다.

## 환경

```sh
export PYTHONDONTWRITEBYTECODE=1
PY=/tmp/pose-qa-venv/bin/python                                   # NumPy, Pillow, jsonschema, pytest
export POSE_AUTHOR_OUT=/tmp/pose-author/out                        # 렌더 시트 출력 위치
```

`/tmp/pose-qa-venv`가 없으면 `python3 -m venv /tmp/pose-qa-venv && /tmp/pose-qa-venv/bin/pip install -r tests/requirements.txt`로 만듭니다.

## 1. 이미지 해석 (코드 작성 전)

이미지를 Read로 보고 다음을 짧게 적어 사용자에게 보여 줍니다.

- **좌우는 캐릭터 기준입니다.** 정면을 향한 인물이면 화면 왼쪽이 인물의 오른쪽입니다.
- 분류 하나를 고릅니다: `서기` / `앉기` / `동작`.
- 부위별 각도 추정(도 단위 어림값): 골반 기울기·회전, 척추 굽힘·비틀림, 머리·목, 위팔·팔꿈치·손목(좌우), 허벅지·무릎·발(좌우), 손가락 쥠 정도.
- 접지 상태: 어느 발·손·엉덩이가 바닥에 닿는지, 또는 공중인지.
- 이미지 한 장으로 정해지지 않는 깊이 방향 가정. 이 내용은 `meta.assumptions`에 들어갑니다.

해석이 애매한 곳(예: 다리가 안쪽으로 모였는지 바깥으로 벌어졌는지)은 이미지를 확대해 보고 판단 근거를 적습니다.

## 2. 저작 스크립트

`scripts/pose_author/poses/pose_NN_<slug>.py`를 만듭니다. `NN`은 `ls poses/pose_*.json`의 최대 번호 + 1이고, `<slug>`는 영어 snake_case입니다. 같은 폴더의 기존 스크립트나 아래 예시에서 시작합니다.

```python
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import *   # rigcore, quat, two_bone, arm_ik, arm_with_hand, flat_foot, foot_on_ball, place_leg,
                    # fingers, ik, ground, report, write_pose, heads_posed, frame_from, ankle_y, limit_errors

# 1) 몸통·머리·쇄골은 오일러 [X, Y, Z] 도(rest 로컬 프레임 기준)로 직접 정합니다.
E = {"pelvis": [0, 4, -2], "spine_01": [0, 0, 1], "spine_02": [0, 0, 1], "spine_03": [0, 2, 0], "spine_04": [0, 2, 0],
     "neck_01": [2, 4, -3], "head": [2, 6, -5], "clavicle_r": [0, 0, -8],
     "upperarm_l": [4, 0, -27], "lowerarm_l": [-10, 8, 0], "hand_l": [8, 0, 0]}
fingers(E, "l", (12, 15, 10), ([-10, 0, 0], 5, 5))       # 손가락 굽힘(_01,_02,_03), 엄지
fingers(E, "r", (3, 4, 2), ([-10, 0, -10], 0, 0))
r = [-0.02, -0.008, 0]                                     # 루트 이동(골반 높이 비율)

# 2) 팔다리는 IK로 끝점 목표(모델 공간 m: +Y 위, +Z 앞, +X 캐릭터 왼쪽)를 줍니다.
ay = ankle_y()
two_bone(E, r, "thigh_l", "calf_l", "foot_l", [0.13, ay, 0.03], [0.2, 0, 1])   # 목표, 무릎 방향
two_bone(E, r, "thigh_r", "calf_r", "foot_r", [-0.10, ay, -0.01], [0, 0, 1])
flat_foot(E, r, "l", 10); flat_foot(E, r, "r", -8)                             # 발바닥 평평, 발끝 yaw
arm_with_hand(E, r, "r", [-0.43, 1.38, 0.0], [-0.40, 1.63, 0.05],               # 팔꿈치, 손목, 손 방향
              frame_from([0.1, 1, 0.05], [0, 0, 1]))

# 3) 접지 후 검사·렌더
r = ground(E, r, "sole")          # 서기: "sole", 앉기/눕기: "body", 점프: airborne=0.15
report(E, r, "pose_NN_<slug>")    # 한계·접지·관통 출력 + $POSE_AUTHOR_OUT/<tag>.png

if "--write" in sys.argv:
    write_pose("pose_NN_<slug>", "English name", "English description. Left/right are the character's own.",
               ["참고 이미지: 사용자 제공, 저장소 미포함", "<깊이 가정 …>",
                "Authored on rig/female.glb; the male uses the same rotations and the hips-height-relative root offset."],
               E, r, "scripts/pose_author/poses/pose_NN_<slug>.py")
```

축의 뜻은 `rig/README.md` 3절 표를 따릅니다. 예를 들어 spine의 +X는 앞으로 굽힘, thigh의 +X는 다리를 뒤로 보내는 신전, upperarm_l의 +Z는 외전입니다. 오른쪽 뼈는 Y·Z 부호가 반대입니다. 관절 한계는 `rig/joint_limits.json`에 있습니다. 앉기처럼 여러 접촉점이 필요한 포즈는 `ik(E, r, dofs, targets, extra=…)`로 손·엉덩이 목표를 함께 풉니다. 포즈 유형별 예시는 `scripts/pose_author/examples/`(pose_02~08 원본 스크립트, README에 기법 표)에 있습니다.

## 3. 검사 → 렌더 대조 루프

`$PY scripts/pose_author/poses/pose_NN_<slug>.py`를 실행한 뒤 다음을 확인합니다.

| 항목 | 통과 기준 (tests/ 와 같음) |
|---|---|
| `limits:` | `OK`. 관절 한계를 벗어나지 않아야 합니다(test_10). |
| `lows (sole, body)` | 서기: 발바닥 최저점이 ±10 mm. 앉기: 몸 최저점이 ±10 mm. 공중: 몸 최저점 ≥ −10 mm (test_11). |
| `penetration` | 새로 생긴 관통이 일반 쌍 25 mm 이하, `upperarm_*~torso`는 60 mm 이하 (test_12). female·male 모두. |

그다음 렌더 시트 PNG를 Read로 열어 원본 이미지와 나란히 비교합니다. 시트는 female/male × 정면/사선/측면입니다. 팔다리 방향, 무릎·팔꿈치 각도, 몸통 기울기, 머리 방향, 접지를 차례로 보고, 차이가 큰 부위 하나둘씩 고쳐 다시 실행합니다. **최대 6회**까지 반복합니다. 그래도 남는 차이(리그 비례 차이, 관절 한계 때문에 만들 수 없는 각도)는 `meta.assumptions`와 사용자 보고에 적습니다.

## 4. 파일 쓰기와 카탈로그 등록

1. `$PY scripts/pose_author/poses/pose_NN_<slug>.py --write`를 실행하면 `poses/pose_NN_<slug>.json`이 생깁니다.
2. **정식 설명은 원본 이미지가 아니라 최종 렌더를 보고 씁니다.** 이미지에서는 뒤를 돌아보는데 렌더에서는 머리가 30°만 돌아갔다면, 설명에도 렌더대로 씁니다(pose_02 회고 교훈).
3. `poses/catalog.ko.json`의 `poses` 배열 끝에 항목을 추가합니다.

```json
{ "id": "pose_NN_<slug>", "name": "한국어 이름", "tags": ["서기", "추가 태그"],
  "description": "한국어 정식 설명 1~2문장. 좌우는 캐릭터 기준." }
```

`tags`에는 분류 태그(`서기`/`앉기`/`동작`)가 정확히 하나만 들어가야 합니다.

4. 프롬프트 스냅숏을 갱신합니다. 갱신 전에 새 포즈의 female/정면 출력을 출력해 정식 설명과 모순이 없는지 읽어 봅니다.

```sh
node --input-type=module -e '
import { readFileSync, readdirSync, writeFileSync } from "node:fs";
import { buildPosePrompt } from "./prompt/index.js";
const cat = JSON.parse(readFileSync("poses/catalog.ko.json", "utf8")).poses;
const out = {};
for (const f of readdirSync("poses").filter(n => /^pose_.*\.json$/.test(n)).sort()) {
  const pose = JSON.parse(readFileSync("poses/" + f, "utf8"));
  out[pose.meta.id] = buildPosePrompt({ pose, catalogEntry: cat.find(e => e.id === pose.meta.id), gender: "female", angle: "front" });
}
writeFileSync("prompt/snapshots.ko.json", JSON.stringify(out, null, 2) + "\n");
console.log(out[Object.keys(out).at(-1)]);'
```

기존 포즈의 스냅숏 값이 바뀌었다면 회귀입니다. `git diff prompt/snapshots.ko.json`으로 새 키만 추가되었는지 확인합니다.

## 5. 완료 조건 (모두 직접 실행해 확인)

```sh
GLTF_VALIDATOR_NODE_PATH=/private/tmp/pose-model-validator/node_modules $PY -m pytest \
  tests/test_10_pose_files.py tests/test_11_pose_apply.py tests/test_12_pose_intersections.py tests/test_13_prompt.py -q -p no:cacheprovider
(cd prompt && node --test)
shasum -a 256 rig/male.glb rig/female.glb rig/joint_limits.json poses/schema.json   # 작업 전 값과 같아야 함
```

- pytest와 `node --test`가 exit 0이어야 합니다.
- 다른 팀 파일의 SHA는 작업 전후로 같아야 합니다.
- `tests/artifacts/pose_contact_sheet_{female,male}.png`(test_12가 갱신)에서 새 포즈 칸을 Read로 열어 사용자에게 보여 줍니다.

## 6. 보고

사용자에게 다음을 알립니다.

- 만든 파일 세 개
- 원본 이미지와 렌더의 대조 결과: 맞춘 부분과 남은 차이, 그리고 그 이유
- `meta.assumptions`에 적은 가정
- 3D 확인 방법: `app/`이 있으면 `cd app && npm run dev`로 띄워 새 썸네일을 누르면 됩니다. 없으면 갤러리 웹앱 계획(`pose-gallery-3d-2of2`)을 먼저 실행해야 한다고 안내합니다.

여러 이미지를 한꺼번에 받으면 이미지마다 1~4단계를 반복하고, 5단계는 마지막에 한 번만 실행합니다.
