import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import *

# Walking mid-stride; stride placement with two_bone + foot_on_ball (see examples/p06.py).
# Reproduction script: the final Euler angles (XYZ, degrees, as stored in the pose file) and the root offset
# are encoded directly; the original IK/authoring runs were interactive and are kept only as reference in
# scripts/pose_author/examples/.
E = {
    'pelvis': [2.0, -6.0, -2.0],
    'spine_01': [1.0, 2.0, 1.0],
    'spine_02': [1.0, 2.0, 0.0],
    'spine_03': [0.0, 3.0, 0.0],
    'spine_04': [0.0, 3.0, 0.0],
    'neck_01': [-2.0, -2.0, 0.0],
    'head': [-2.0, -3.0, 0.0],
    'upperarm_l': [-22.0, -4.0, -21.0],
    'lowerarm_l': [-10.0, 10.0, 0.0],
    'hand_l': [6.0, 0.0, 0.0],
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
    'thigh_l': [-30.012, -6.547, 0.309],
    'calf_l': [-2.977, 0.0, 0.0],
    'foot_l': [18.835, 2.224, -7.853],
    'upperarm_r': [16.0, -6.0, 30.0],
    'lowerarm_r': [18.0, -15.0, 0.0],
    'hand_r': [6.0, 0.0, 0.0],
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
    'thigh_r': [-1.641, -5.549, -10.545],
    'calf_r': [27.223, 0.0, 0.0],
    'foot_r': [3.304, 1.85, 7.598],
    'ball_r': [-30.0, 0.0, 0.0],
}
r = [0.0, -0.016518, 0.0]

report(E, r, "pose_06_walking", render=False)

if "--write" in sys.argv:
    write_pose("pose_06_walking", 'Walking, left foot forward',
               "Mid-stride walk. Left leg forward with a nearly straight knee, landing on the heel with the toes up; right leg behind with the heel raised, pushing off from the ball of the foot. Arms swing opposite to the legs: right arm forward with a slightly bent elbow, left arm back. Left/right are the character's own.",
               ['Stride ~50 cm (female); the lowest sole touches the floor.', 'Authored on rig/female.glb; the male uses the same rotations and the hips-height-relative root offset. The root height is the mean of the female and male heights that put the contact on y = 0, so both models land within a few millimetres of the floor.'],
               E, r, "scripts/pose_author/poses/pose_06_walking.py")
