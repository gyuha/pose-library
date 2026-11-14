import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import *

# Standing, torso/neck twisted to look back over the shoulder; twist distributed over pelvis, spine and neck (see examples/p02.py).
# Reproduction script: the final Euler angles (XYZ, degrees, as stored in the pose file) and the root offset
# are encoded directly; the original IK/authoring runs were interactive and are kept only as reference in
# scripts/pose_author/examples/.
E = {
    'pelvis': [0.0, -14.0, 2.0],
    'spine_01': [0.0, -8.0, -1.0],
    'spine_02': [0.0, -8.0, -1.0],
    'spine_03': [2.0, -8.0, 0.0],
    'spine_04': [0.0, -10.0, 0.0],
    'neck_01': [-4.0, -28.0, 3.0],
    'head': [-4.0, -26.0, 4.0],
    'upperarm_l': [8.0, 0.0, -26.0],
    'lowerarm_l': [-8.0, 10.0, 0.0],
    'hand_l': [8.0, 0.0, 0.0],
    'thumb_01_l': [-10.0, 0.0, 0.0],
    'thumb_02_l': [5.0, 0.0, 0.0],
    'thumb_03_l': [5.0, 0.0, 0.0],
    'index_01_l': [12.0, 0.0, 0.0],
    'index_02_l': [15.0, 0.0, 0.0],
    'index_03_l': [10.0, 0.0, 0.0],
    'middle_01_l': [12.0, 0.0, 0.0],
    'middle_02_l': [15.0, 0.0, 0.0],
    'middle_03_l': [10.0, 0.0, 0.0],
    'ring_01_l': [12.0, 0.0, 0.0],
    'ring_02_l': [15.0, 0.0, 0.0],
    'ring_03_l': [10.0, 0.0, 0.0],
    'pinky_01_l': [12.0, 0.0, 0.0],
    'pinky_02_l': [15.0, 0.0, 0.0],
    'pinky_03_l': [10.0, 0.0, 0.0],
    'thigh_l': [-11.626, -15.124, 3.208],
    'calf_l': [16.279, 0.0, 0.0],
    'foot_l': [-3.864, 8.794, 0.515],
    'clavicle_r': [-4.0, 0.0, 0.0],
    'upperarm_r': [-4.0, 0.0, 24.0],
    'lowerarm_r': [-5.0, -10.0, 0.0],
    'hand_r': [8.0, 0.0, 0.0],
    'thumb_01_r': [-10.0, 0.0, 0.0],
    'thumb_02_r': [5.0, 0.0, 0.0],
    'thumb_03_r': [5.0, 0.0, 0.0],
    'index_01_r': [12.0, 0.0, 0.0],
    'index_02_r': [15.0, 0.0, 0.0],
    'index_03_r': [10.0, 0.0, 0.0],
    'middle_01_r': [12.0, 0.0, 0.0],
    'middle_02_r': [15.0, 0.0, 0.0],
    'middle_03_r': [10.0, 0.0, 0.0],
    'ring_01_r': [12.0, 0.0, 0.0],
    'ring_02_r': [15.0, 0.0, 0.0],
    'ring_03_r': [10.0, 0.0, 0.0],
    'pinky_01_r': [12.0, 0.0, 0.0],
    'pinky_02_r': [15.0, 0.0, 0.0],
    'pinky_03_r': [10.0, 0.0, 0.0],
    'thigh_r': [-6.986, 2.477, 0.918],
    'calf_r': [12.762, 0.0, 0.0],
    'foot_r': [-5.17, 2.916, 1.441],
}
r = [0.03, -0.01006, 0.0]

report(E, r, "pose_02_standing_look_back", render=False)

if "--write" in sys.argv:
    write_pose("pose_02_standing_look_back", 'Standing, looking back over the right shoulder',
               "Standing with the weight shifted onto the left leg. Pelvis, spine, neck and head all turn to the character's right, so the face looks back over the right shoulder. Right foot set a little behind and turned out; both arms hang relaxed, the right arm slightly behind the body. Left/right are the character's own.",
               ['Turn split over the chain to stay inside the per-bone limits and avoid skinning folds: pelvis 14 deg, spine 34 deg in total, neck 28 deg and head 26 deg to the right (~100 deg overall).', 'Feet placed with two-bone IK: left ankle under the left hip, right ankle 10 cm behind and turned out 20 deg; both soles flat.', 'Authored on rig/female.glb; the male uses the same rotations and the hips-height-relative root offset. The root height is the mean of the female and male heights that put the contact on y = 0, so both models land within a few millimetres of the floor.'],
               E, r, "scripts/pose_author/poses/pose_02_standing_look_back.py")
