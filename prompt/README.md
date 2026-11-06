# pose-prompt

Node 24와 Vite 브라우저 번들에서 동일하게 동작하는 의존성 없는 ES 모듈입니다. 라이브러리는 파일을 읽지 않으며, 호출자가 파싱한 포즈 파일과 일치하는 포즈 카탈로그 항목을 전달합니다.

```js
import { buildPosePrompt, ANGLE_PRESETS } from './prompt/index.js';
const text = buildPosePrompt({
  pose, catalogEntry, gender: 'female', angle: 'front',
});
```

`gender`는 `female` 또는 `male`, `angle`은 `front`, `side`, `three_quarter`, `high`, `low`입니다. 알 수 없는 값이나 서로 다른 id는 Error를 던집니다. 입력은 유효한 포즈 스키마를 만족해야 합니다. 입력을 변경하지 않습니다.

반환값은 인물·앵글·자세·몸통·팔·다리·체중·시선 순서의 정확히 8줄입니다. 자세에는 `catalogEntry.description`을 그대로 씁니다. 한국어 문구는 `phrases.ko.js`에 모아 두었습니다.

`ANGLE_PRESETS`와 각 항목은 동결되어 있으며 `{ label, phrase, yawDeg, pitchDeg }`를 제공합니다. 옆/사선의 양의 yaw는 인물 오른쪽 카메라, 양의 pitch는 위에서 내려다보는 카메라입니다. 각도 단위는 도입니다.

회전은 참고용 `euler`가 아닌 quaternion에서 three.js XYZ 방식으로 추출합니다. 빠진 관절은 rest 회전입니다. 몸통 전후 기울임 12°, 척추 회전 8°/옆굽힘 6°, 목 회전 8°/전후 10°/옆기울임 5° 이하 등 작은 변화는 생략합니다. 팔꿈치는 rest의 약 30° 굽힘을 고려하여 추가 굴곡 25° 초과를 명시합니다. 중립 문구는 세부 변화가 작다는 뜻이며 해부학적 영점은 아닙니다.

로컬 각도를 합하는 근사 규칙으로 FK를 수행하지 않습니다. 몸통 회전은 골반 기준, 고개 회전은 몸통 기준입니다. 손과 머리/허리의 접촉, 발의 접지, 시선의 실제 도착점, 지지점 하중은 계산하지 않습니다. 체중은 골반 기울기에 따른 추정이고, 양쪽 고관절·무릎을 크게 굽힌 자세는 접지를 추정하지 않습니다. 앉은 자세는 골반 및 고관절 굴곡 조합으로 분류합니다. 정확한 접촉 설명은 정식 설명을 참고합니다.

검증: `cd prompt && node --test`. 전체 80조합, pose_01 전체 기대 문자열, 좌우 미러와 XYZ 특이점, quaternion 우선 사용, 예외, 결정성 및 `snapshots.ko.json`의 8개 여성/정면 출력을 검사합니다. 스냅샷 변경은 생성한 문구를 정식 설명과 대조한 뒤 검토합니다.
