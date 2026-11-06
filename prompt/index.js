import { ko } from './phrases.ko.js';

const camera = {front:[0,0], side:[90,0], three_quarter:[45,0], high:[0,45], low:[0,-30]};
export const ANGLE_PRESETS = Object.freeze(Object.fromEntries(
 Object.entries(camera).map(([key, [yawDeg, pitchDeg]]) =>
  [key, Object.freeze({...ko.angles[key], yawDeg, pitchDeg})]),
));

// three.js Euler XYZ extraction from a unit quaternion's rotation matrix.
// Local angles are only descriptive heuristics, not FK: sums of spine/neck
// angles approximate direction; shoulder thresholds account for the rest A-pose.
// They cannot establish hand contact, world-space gaze, foot contact or forces.
// Pelvis roll suggests a support side only; deep hip/knee flexion suppresses it.
function xyz(q = [0,0,0,1]) {
 const norm = Math.hypot(...q);
 const [x,y,z,w] = q.map(v => v / norm);
 const m13 = 2*(x*z+w*y);
 const ey = Math.asin(Math.max(-1, Math.min(1, m13)));
 let ex, ez;
 if (Math.abs(m13) < 0.9999999) {
  ex = Math.atan2(2*(w*x-y*z), 1-2*(x*x+y*y));
  ez = Math.atan2(2*(w*z-x*y), 1-2*(y*y+z*z));
 } else {
  ex = Math.atan2(2*(y*z+w*x), 1-2*(x*x+z*z));
  ez = 0;
 }
 return [ex,ey,ez].map(v => v*180/Math.PI);
}
const join = parts => parts.filter(Boolean).join(ko.join);
const direction = (value, threshold, positive, negative) =>
 value > threshold ? positive : value < -threshold ? negative : '';

export function buildPosePrompt({pose, catalogEntry, gender, angle}) {
 if (!Object.hasOwn(ko.genders, gender)) throw new Error(ko.errors.gender);
 if (!Object.hasOwn(ANGLE_PRESETS, angle)) throw new Error(ko.errors.angle);
 if (catalogEntry.id !== pose.meta.id) throw new Error(ko.errors.id);
 const bone = name => xyz(pose.bones[name]?.quaternion);
 const sum = names => names.reduce((a,name) => bone(name).map((v,i) => a[i]+v), [0,0,0]);
 const pelvis = bone('pelvis');
 const spine = sum(['spine_01','spine_02','spine_03','spine_04']);
 const neck = sum(['neck_01','head']);
 const body = join([
  direction(pelvis[0]+spine[0], 12, ko.body.forward, ko.body.back),
  direction(spine[1], 8, ko.body.left, ko.body.right),
  direction(spine[2], 6, ko.body.tiltRight, ko.body.tiltLeft),
 ]) || ko.body.neutral;
 const arms = ['l','r'].map(side => {
  const s = ko.sides[side], upper = bone('upperarm_'+side), lower = bone('lowerarm_'+side);
  const abduction = upper[2] * (side === 'l' ? 1 : -1);
  const position = abduction > 50 ? 'high' : abduction > 25 ? 'side' : upper[0] > 15 ? 'forward' : upper[0] < -15 ? 'back' : 'neutral';
  const elbow = lower[0] > 25 ? ko.arm.bent : lower[0] < -20 ? ko.arm.straight : '';
  return ko.arm.combine(ko.arm[position](s), elbow);
 });
 const legs = ['l','r'].flatMap(side => {
  const s = ko.sides[side], thigh = bone('thigh_'+side), calf = bone('calf_'+side);
  const bent = calf[0] > 20, straight = calf[0] < 0;
  const position = thigh[0] < -20 && bent ? 'forward' : thigh[0] < -20 && straight ? 'extended' : bent ? 'bent' : straight ? 'straight' : 'neutral';
  return [ko.leg[position](s), thigh[2]*(side === 'l' ? -1 : 1) > 12 ? ko.leg.outward(s) : ''];
 });
 const deeplyBent = ['l','r'].every(s => bone('thigh_'+s)[0] < -45 && bone('calf_'+s)[0] > 70);
 const seated = pelvis[0] < -20 && ['l','r'].every(s => bone('thigh_'+s)[0] < -40);
 const weight = seated ? ko.weight.seated : deeplyBent ? ko.weight.uncertain : direction(pelvis[2], 1.5, ko.weight.left, ko.weight.right) || ko.weight.uncertain;
 const gaze = join([
  direction(neck[0], 10, ko.gaze.down, ko.gaze.up),
  direction(neck[1], 8, ko.gaze.left, ko.gaze.right),
  direction(neck[2], 5, ko.gaze.tiltRight, ko.gaze.tiltLeft),
 ]) || ko.gaze.neutral;
 return [ko.genders[gender], ANGLE_PRESETS[angle].phrase, catalogEntry.description, body, join(arms), join(legs), weight, gaze]
  .map((value,i) => `${ko.labels[i]}: ${value}`).join('\n');
}
