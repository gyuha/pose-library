import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { buildPosePrompt, ANGLE_PRESETS } from './index.js';
const read = name => JSON.parse(readFileSync(new URL(name, import.meta.url), 'utf8'));
const catalog = read('../poses/catalog.ko.json').poses;
const poses = readdirSync(new URL('../poses/', import.meta.url)).filter(n => /^pose_.*\.json$/.test(n)).sort().map(n => read('../poses/' + n));
const input = pose => ({ pose, catalogEntry: catalog.find(e => e.id === pose.meta.id), gender: 'female', angle: 'front' });
const expected01 = `인물: 여성 인물, 전신
앵글: 정면에서 바라본 전신
자세: ${catalog.find(e => e.id === poses[0].meta.id).description}
몸통: 몸통을 오른쪽으로 기울임
팔: 왼팔을 높이 들고 팔꿈치를 굽힘, 오른팔을 몸 옆에 두고 팔꿈치를 굽힘
다리: 왼허벅지를 앞으로 기울이고 무릎을 굽힘, 왼다리를 옆으로 벌림, 오른다리는 무릎을 거의 폄
체중: 오른쪽을 지지 중심으로 둔 자세로 추정
시선: 몸통에 비해 고개를 듦, 고개를 오른쪽으로 기울임`;
test('pose_01: README와 축 정의를 대조한 전체 출력', () => assert.equal(buildPosePrompt(input(poses[0])), expected01));
test('all combinations', () => {
 assert.ok(poses.length >= 8);
 let count = 0;
 for (const pose of poses) for (const gender of ['female','male']) for (const angle of Object.keys(ANGLE_PRESETS)) {
  const args = { ...input(pose), gender, angle };
  const result = buildPosePrompt(args); const lines = result.split('\n');
  assert.equal(lines.length, 8);
  assert.deepEqual(lines.map(l => l.split(':')[0]), ['인물','앵글','자세','몸통','팔','다리','체중','시선']);
  assert.ok(lines.every(l => /^.+: \S.+$/.test(l)));
  assert.equal(lines[0], `인물: ${gender === 'female' ? '여성' : '남성'} 인물, 전신`);
  assert.equal(lines[1], `앵글: ${ANGLE_PRESETS[angle].phrase}`);
  assert.equal(lines[2], `자세: ${args.catalogEntry.description}`);
  assert.equal(buildPosePrompt(args), result); count++;
 }
 assert.equal(count, poses.length * 2 * Object.keys(ANGLE_PRESETS).length);
});
test('invalid gender, angle and mismatched catalog', () => {
 const args = input(poses[0]);
 for (const gender of ['other', 'toString', undefined]) assert.throws(() => buildPosePrompt({...args, gender}), Error);
 for (const angle of ['other', 'toString', undefined]) assert.throws(() => buildPosePrompt({...args, angle}), Error);
 assert.throws(() => buildPosePrompt({...args, catalogEntry: {...args.catalogEntry, id:'bad'}}), Error);
});
test('presets and camera definitions are frozen', () => {
 assert.ok(Object.isFrozen(ANGLE_PRESETS));
 assert.deepEqual(Object.keys(ANGLE_PRESETS), ['front','side','three_quarter','high','low']);
 assert.deepEqual(Object.values(ANGLE_PRESETS).map(p => [p.yawDeg,p.pitchDeg]), [[0,0],[90,0],[45,0],[0,45],[0,-30]]);
 for (const p of Object.values(ANGLE_PRESETS)) assert.ok(Object.isFrozen(p));
});
test('female/front snapshot', () => {
 const snapshot = read('./snapshots.ko.json');
 assert.deepEqual(Object.fromEntries(poses.map(p => [p.meta.id, buildPosePrompt(input(p))])), snapshot);
});
test('quaternion is authoritative; missing joints and tiny rotations remain neutral', () => {
 const args = input(poses[0]);
 const pose = structuredClone(args.pose);
 for (const bone of Object.values(pose.bones)) bone.euler = {order:'XYZ', degrees:[0,0,0]};
 assert.equal(buildPosePrompt({...args, pose}), expected01);
 const neutral = {...pose, bones:{}};
 const result = buildPosePrompt({...args, pose:neutral});
 const tiny = {...pose, bones:{head:{quaternion:[0.0001,0,0,Math.sqrt(1-0.0001**2)]}}};
 assert.equal(buildPosePrompt({...args, pose:tiny}), result);
});
test('mirrored arm elevation uses the character’s left/right', () => {
 const args = input(poses[0]);
 const pose = structuredClone(args.pose);
 pose.bones = Object.fromEntries(Object.entries(pose.bones).map(([name, value]) => {
  const mirrored = name.endsWith('_l') ? name.slice(0,-2)+'_r' : name.endsWith('_r') ? name.slice(0,-2)+'_l' : name;
  const [x,y,z,w] = value.quaternion;
  return [mirrored, {quaternion:[x,-y,-z,w]}];
 }));
 const lines = buildPosePrompt({...args, pose}).split('\n');
 assert.equal(lines[4], '팔: 왼팔을 몸 옆에 두고 팔꿈치를 굽힘, 오른팔을 높이 들고 팔꿈치를 굽힘');
 assert.equal(lines[6], '체중: 왼쪽을 지지 중심으로 둔 자세로 추정');
 assert.equal(lines[7], '시선: 몸통에 비해 고개를 듦, 고개를 왼쪽으로 기울임');
});
test('XYZ singularity and quaternion sign do not change turn direction', () => {
 const args = input(poses[0]);
 for (const sign of [1,-1]) {
  const q = [0, Math.SQRT1_2 * sign, 0, Math.SQRT1_2 * sign];
  const pose = {...args.pose, bones:{head:{quaternion:q}}};
  assert.equal(buildPosePrompt({...args, pose}).split('\n')[7], '시선: 몸통에 비해 고개를 왼쪽으로 돌림');
 }
});
