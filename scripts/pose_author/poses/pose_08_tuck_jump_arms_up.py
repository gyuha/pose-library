import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import *

# Tuck jump, airborne; both knees pulled up, arms in a V; ground(..., 'body', airborne=AIR) (see examples/p08.py).
# Reproduction script: the final Euler angles (XYZ, degrees, as stored in the pose file) and the root offset
# are encoded directly; the original IK/authoring runs were interactive and are kept only as reference in
# scripts/pose_author/examples/.
E = {
    'pelvis': [-6.0, 0.0, 0.0],
    'spine_01': [2.0, 0.0, 0.0],
    'spine_03': [-3.0, 0.0, 0.0],
    'spine_04': [-2.0, 0.0, 0.0],
    'neck_01': [-6.0, 0.0, 0.0],
    'head': [-8.0, 0.0, 0.0],
    'clavicle_l': [0.0, 0.0, 16.0],
    'upperarm_l': [48.0, -10.0, 62.0],
    'lowerarm_l': [-15.0, -20.0, 0.0],
    'hand_l': [-10.0, 0.0, 0.0],
    'thumb_01_l': [-15.0, 0.0, 15.0],
    'index_01_l': [0.0, 0.0, 8.0],
    'index_02_l': [4.0, 0.0, 0.0],
    'index_03_l': [2.0, 0.0, 0.0],
    'middle_02_l': [4.0, 0.0, 0.0],
    'middle_03_l': [2.0, 0.0, 0.0],
    'ring_01_l': [0.0, 0.0, -6.0],
    'ring_02_l': [4.0, 0.0, 0.0],
    'ring_03_l': [2.0, 0.0, 0.0],
    'pinky_01_l': [0.0, 0.0, -12.0],
    'pinky_02_l': [4.0, 0.0, 0.0],
    'pinky_03_l': [2.0, 0.0, 0.0],
    'thigh_l': [-62.0, -8.0, -8.0],
    'calf_l': [105.0, 0.0, 0.0],
    'foot_l': [35.0, 0.0, -4.0],
    'ball_l': [10.0, 0.0, 0.0],
    'clavicle_r': [0.0, 0.0, -16.0],
    'upperarm_r': [48.0, 10.0, -62.0],
    'lowerarm_r': [-15.0, 20.0, 0.0],
    'hand_r': [-10.0, 0.0, 0.0],
    'thumb_01_r': [-15.0, 0.0, -15.0],
    'index_01_r': [0.0, 0.0, -8.0],
    'index_02_r': [4.0, 0.0, 0.0],
    'index_03_r': [2.0, 0.0, 0.0],
    'middle_02_r': [4.0, 0.0, 0.0],
    'middle_03_r': [2.0, 0.0, 0.0],
    'ring_01_r': [0.0, 0.0, 6.0],
    'ring_02_r': [4.0, 0.0, 0.0],
    'ring_03_r': [2.0, 0.0, 0.0],
    'pinky_01_r': [0.0, 0.0, 12.0],
    'pinky_02_r': [4.0, 0.0, 0.0],
    'pinky_03_r': [2.0, 0.0, 0.0],
    'thigh_r': [-55.0, 8.0, 8.0],
    'calf_r': [110.0, 0.0, 0.0],
    'foot_r': [35.0, 0.0, 4.0],
    'ball_r': [10.0, 0.0, 0.0],
}
# Airborne: lowest vertex 0.32 m above the floor on the mean of female/male (both stay >= 0.30 m).
AIR = 0.32
r = ground(E, [0, 0, 0], "body", airborne=AIR)

report(E, r, "pose_08_tuck_jump_arms_up", render=False)

if "--write" in sys.argv:
    write_pose("pose_08_tuck_jump_arms_up", 'Tuck jump, arms raised',
               "In the air with both feet about 31 cm (female) to 33 cm (male) off the floor. Both knees pulled up and bent with the feet pointed, arms raised in a wide V above the shoulders with open hands, chin slightly up. Left/right are the character's own.",
               ['Airborne: the lowest vertex is ~0.31 m above the floor on the female and ~0.33 m on the male (root height chosen so the mean of the two is 0.32 m). The raised hands rise above the standard preview frame; framing is handled by the camera, not by lowering the jump.', 'Authored on rig/female.glb; the male uses the same rotations and the hips-height-relative root offset. The root height is the mean of the female and male heights that put the contact on y = 0, so both models land within a few millimetres of the floor.'],
               E, r, "scripts/pose_author/poses/pose_08_tuck_jump_arms_up.py")
