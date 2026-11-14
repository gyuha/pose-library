import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import *

# Running mid-stride; stride placement with two_bone + foot_on_ball (see examples/p07.py).
# Reproduction script: the final Euler angles (XYZ, degrees, as stored in the pose file) and the root offset
# are encoded directly; the original IK/authoring runs were interactive and are kept only as reference in
# scripts/pose_author/examples/.
E = {
    'pelvis': [12.0, -8.0, -3.0],
    'spine_01': [2.0, 3.0, 1.0],
    'spine_02': [2.0, 3.0, 1.0],
    'spine_03': [1.0, 4.0, 0.0],
    'spine_04': [0.0, 3.0, 0.0],
    'neck_01': [-8.0, -2.0, 0.0],
    'head': [-6.0, -3.0, 0.0],
    'clavicle_l': [-6.0, 0.0, 0.0],
    'upperarm_l': [-38.0, 0.0, -18.0],
    'lowerarm_l': [62.0, 10.0, 0.0],
    'hand_l': [10.0, 0.0, 0.0],
    'thumb_01_l': [5.0, 0.0, 0.0],
    'thumb_02_l': [15.0, 0.0, 0.0],
    'thumb_03_l': [15.0, 0.0, 0.0],
    'index_01_l': [40.0, 0.0, 0.0],
    'index_02_l': [55.0, 0.0, 0.0],
    'index_03_l': [35.0, 0.0, 0.0],
    'middle_01_l': [40.0, 0.0, 0.0],
    'middle_02_l': [55.0, 0.0, 0.0],
    'middle_03_l': [35.0, 0.0, 0.0],
    'ring_01_l': [40.0, 0.0, 0.0],
    'ring_02_l': [55.0, 0.0, 0.0],
    'ring_03_l': [35.0, 0.0, 0.0],
    'pinky_01_l': [40.0, 0.0, 0.0],
    'pinky_02_l': [55.0, 0.0, 0.0],
    'pinky_03_l': [35.0, 0.0, 0.0],
    'thigh_l': [-68.0, -4.0, -3.0],
    'calf_l': [105.0, 0.0, 0.0],
    'foot_l': [22.0, 0.0, -4.0],
    'clavicle_r': [8.0, 0.0, 0.0],
    'upperarm_r': [42.0, 0.0, 22.0],
    'lowerarm_r': [68.0, -10.0, 0.0],
    'hand_r': [10.0, 0.0, 0.0],
    'thumb_01_r': [5.0, 0.0, 0.0],
    'thumb_02_r': [15.0, 0.0, 0.0],
    'thumb_03_r': [15.0, 0.0, 0.0],
    'index_01_r': [40.0, 0.0, 0.0],
    'index_02_r': [55.0, 0.0, 0.0],
    'index_03_r': [35.0, 0.0, 0.0],
    'middle_01_r': [40.0, 0.0, 0.0],
    'middle_02_r': [55.0, 0.0, 0.0],
    'middle_03_r': [35.0, 0.0, 0.0],
    'ring_01_r': [40.0, 0.0, 0.0],
    'ring_02_r': [55.0, 0.0, 0.0],
    'ring_03_r': [35.0, 0.0, 0.0],
    'pinky_01_r': [40.0, 0.0, 0.0],
    'pinky_02_r': [55.0, 0.0, 0.0],
    'pinky_03_r': [35.0, 0.0, 0.0],
    'thigh_r': [-17.473, -1.483, -13.679],
    'calf_r': [39.988, 0.0, 0.0],
    'foot_r': [-0.938, -2.766, 6.235],
    'ball_r': [-32.0, 0.0, 0.0],
}
r = [0.0, -0.049543, 0.0]

report(E, r, "pose_07_running", render=False)

if "--write" in sys.argv:
    write_pose("pose_07_running", 'Running, left knee driving forward',
               "Running stride. Right foot behind on the ball of the foot pushing off; left knee driven forward and up with the lower leg folded back. Torso leans forward; elbows bent about 90 degrees with the right arm forward and the left arm back, hands in loose fists. Left/right are the character's own.",
               ['Shown in the support phase (right ball on the floor) rather than the flight phase, so the lowest point is on the floor.', 'Authored on rig/female.glb; the male uses the same rotations and the hips-height-relative root offset. The root height is the mean of the female and male heights that put the contact on y = 0, so both models land within a few millimetres of the floor.'],
               E, r, "scripts/pose_author/poses/pose_07_running.py")
