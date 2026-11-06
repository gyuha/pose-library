// pytest(tests/test_13_prompt.py) 가 prompt/ 엔진을 node 로 부르는 얇은 브리지.
// stdin: JSON [{pose, catalogEntry, gender, angle}, ...]  stdout: JSON [{ok:true,text}|{ok:false,error}, ...]
// 출력 객체에 ANGLE_PRESETS 도 angles 로 함께 낸다.
import { readFileSync } from 'node:fs';
import { buildPosePrompt, ANGLE_PRESETS } from '../prompt/index.js';

const cases = JSON.parse(readFileSync(0, 'utf8'));
const results = cases.map((c) => {
  try {
    return { ok: true, text: buildPosePrompt(c) };
  } catch (e) {
    return { ok: false, error: String(e && e.message) };
  }
});
process.stdout.write(JSON.stringify({ angles: ANGLE_PRESETS, results }));
