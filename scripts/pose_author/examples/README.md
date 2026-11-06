# examples — pose_02~08 저작 스크립트 원본

`/tmp/pose-author/`에서 pose_02~08을 만들 때 쓴 스크립트를 그대로 옮겨 둔 참고 자료입니다. 실행용이 아니라 `lib.py` 사용 예시로 봅니다.

- 각 스크립트는 `from lib import *` 한 줄로 시작하며, 작업 디렉터리에 `.pkl` 파일을 쓰는 옛 방식입니다.
- 실제 포즈 파일은 `/tmp/pose-author/build_all.py`가 pkl을 읽어 썼습니다.

| 파일 | 포즈 | 볼 만한 기법 |
|---|---|---|
| p02.py | 뒤돌아보며 서기 | 척추·목 비틀림 분배 |
| p03.py | 손 흔들어 인사 | `arm_with_hand`로 손바닥 방향 맞추기 |
| p04.py, p04b.py | 무릎 세워 앉기 | 엉덩이 접지(`ground(..., "body")`), 손 접촉 |
| p05.py | 뒤로 손 짚고 기대앉기 | `ik`에 손 목표와 `axis_obj` 방향 목표를 함께 주기 |
| p06.py, p07.py | 걷기, 달리기 | 보폭 배치, `foot_on_ball` |
| p08.py | 무릎 당겨 점프 | 공중 자세(`ground(..., airborne=…)`) |

새 포즈는 `../poses/pose_NN_<slug>.py`에 씁니다. 형식은 `.claude/skills/image-to-pose/SKILL.md` 2절을 따릅니다.
