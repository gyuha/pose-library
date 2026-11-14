import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import *

# Standing, one hand raised in a wave; palm direction matched with arm_with_hand (see examples/p03.py).
# Reproduction script: the final Euler angles (XYZ, degrees, as stored in the pose file) and the root offset
# are encoded directly; the original IK/authoring runs were interactive and are kept only as reference in
# scripts/pose_author/examples/.
E = {
    'pelvis': [0.0, 4.0, -2.0],
    'spine_01': [0.0, 0.0, 1.0],
    'spine_02': [0.0, 0.0, 1.0],
    'spine_03': [0.0, 2.0, 0.0],
    'spine_04': [0.0, 2.0, 0.0],
    'neck_01': [2.0, 4.0, -3.0],
    'head': [2.0, 6.0, -5.0],
    'upperarm_l': [4.0, 0.0, -27.0],
    'lowerarm_l': [-10.0, 8.0, 0.0],
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
    'thigh_l': [-15.666, -6.981, -1.257],
    'calf_l': [13.083, 0.0, 0.0],
    'foot_l': [2.761, 2.266, -0.326],
    'clavicle_r': [0.0, 0.0, -8.0],
    'upperarm_r': [50.322, 37.143, -33.114],
    'lowerarm_r': [72.534, 10.0, 0.0],
    'hand_r': [-19.732, 0.068, 3.502],
    'thumb_01_r': [-10.0, 0.0, -10.0],
    'index_01_r': [3.0, 0.0, 0.0],
    'index_02_r': [4.0, 0.0, 0.0],
    'index_03_r': [2.0, 0.0, 0.0],
    'middle_01_r': [3.0, 0.0, 0.0],
    'middle_02_r': [4.0, 0.0, 0.0],
    'middle_03_r': [2.0, 0.0, 0.0],
    'ring_01_r': [3.0, 0.0, 0.0],
    'ring_02_r': [4.0, 0.0, 0.0],
    'ring_03_r': [2.0, 0.0, 0.0],
    'pinky_01_r': [3.0, 0.0, 0.0],
    'pinky_02_r': [4.0, 0.0, 0.0],
    'pinky_03_r': [2.0, 0.0, 0.0],
    'thigh_r': [-9.22, 5.437, -6.782],
    'calf_r': [10.833, 0.0, 0.0],
    'foot_r': [-1.605, 0.699, 9.922],
}
r = [-0.02, -0.006098, 0.0]

report(E, r, "pose_03_standing_wave", render=False)

if "--write" in sys.argv:
    write_pose("pose_03_standing_wave", 'Standing, waving with the right hand',
               "Standing upright, weight slightly on the right leg. Right upper arm raised out to the side to about shoulder height with the elbow bent so the forearm points up; the open right palm faces forward at head height. Left arm hangs relaxed. Head turned and tilted slightly to the left. Left/right are the character's own.",
               ['Right arm placed analytically (elbow and wrist targets), forearm twist chosen so the palm faces forward within the wrist limits; fingers nearly straight, thumb slightly open.', 'Authored on rig/female.glb; the male uses the same rotations and the hips-height-relative root offset. The root height is the mean of the female and male heights that put the contact on y = 0, so both models land within a few millimetres of the floor.'],
               E, r, "scripts/pose_author/poses/pose_03_standing_wave.py")
