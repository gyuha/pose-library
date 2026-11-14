import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import *

# Sitting on the floor with knees raised, hands resting near the shins; buttocks grounded via ground(..., 'body') (see examples/p04.py, p04b.py).
# Reproduction script: the final Euler angles (XYZ, degrees, as stored in the pose file) and the root offset
# are encoded directly; the original IK/authoring runs were interactive and are kept only as reference in
# scripts/pose_author/examples/.
E = {
    'pelvis': [-28.0, 0.0, 0.0],
    'spine_01': [18.0, 0.0, 0.0],
    'spine_02': [18.0, 0.0, 0.0],
    'spine_03': [18.0, 0.0, 0.0],
    'spine_04': [10.8, 0.0, 0.0],
    'neck_01': [-18.0, 0.0, 0.0],
    'head': [-16.0, 0.0, 0.0],
    'clavicle_l': [18.0, 0.0, 12.0],
    'upperarm_l': [62.771, 39.601, -30.98],
    'lowerarm_l': [34.332, -0.0, 0.0],
    'hand_l': [0.0, 0.0, -10.0],
    'thumb_01_l': [10.0, 0.0, 10.0],
    'thumb_02_l': [10.0, 0.0, 0.0],
    'thumb_03_l': [10.0, 0.0, 0.0],
    'index_01_l': [35.0, 0.0, 0.0],
    'index_02_l': [45.0, 0.0, 0.0],
    'index_03_l': [30.0, 0.0, 0.0],
    'middle_01_l': [35.0, 0.0, 0.0],
    'middle_02_l': [45.0, 0.0, 0.0],
    'middle_03_l': [30.0, 0.0, 0.0],
    'ring_01_l': [35.0, 0.0, 0.0],
    'ring_02_l': [45.0, 0.0, 0.0],
    'ring_03_l': [30.0, 0.0, 0.0],
    'pinky_01_l': [35.0, 0.0, 0.0],
    'pinky_02_l': [45.0, 0.0, 0.0],
    'pinky_03_l': [30.0, 0.0, 0.0],
    'thigh_l': [-122.274, -10.856, -19.444],
    'calf_l': [116.734, 0.0, 0.0],
    'foot_l': [32.476, 13.559, -20.023],
    'clavicle_r': [18.0, 0.0, -12.0],
    'upperarm_r': [62.772, -39.602, 30.98],
    'lowerarm_r': [34.332, -0.0, 0.0],
    'hand_r': [0.0, 0.0, 10.0],
    'thumb_01_r': [10.0, 0.0, -10.0],
    'thumb_02_r': [10.0, 0.0, 0.0],
    'thumb_03_r': [10.0, 0.0, 0.0],
    'index_01_r': [35.0, 0.0, 0.0],
    'index_02_r': [45.0, 0.0, 0.0],
    'index_03_r': [30.0, 0.0, 0.0],
    'middle_01_r': [35.0, 0.0, 0.0],
    'middle_02_r': [45.0, 0.0, 0.0],
    'middle_03_r': [30.0, 0.0, 0.0],
    'ring_01_r': [35.0, 0.0, 0.0],
    'ring_02_r': [45.0, 0.0, 0.0],
    'ring_03_r': [30.0, 0.0, 0.0],
    'pinky_01_r': [35.0, 0.0, 0.0],
    'pinky_02_r': [45.0, 0.0, 0.0],
    'pinky_03_r': [30.0, 0.0, 0.0],
    'thigh_r': [-122.274, 10.856, 19.444],
    'calf_r': [116.734, 0.0, 0.0],
    'foot_r': [32.476, -13.559, 20.023],
}
r = [0.0, -0.801963, -0.09231]

report(E, r, "pose_04_sitting_knees_up", render=False)

if "--write" in sys.argv:
    write_pose("pose_04_sitting_knees_up", 'Sitting on the floor, knees up, arms on the knees',
               "Sitting on the floor with both knees raised and apart and both feet flat in front. The torso leans forward, both forearms rest over the knees and the hands meet between the shins. Head up, looking forward. Left/right are the character's own.",
               ['No seat: the buttocks rest on the floor plane (lowest vertex at y = 0).', 'Knees kept apart (thighs abducted ~19 deg and externally rotated): with the knees together, hip flexion above ~110 deg pushes the thigh shell into the abdomen shell.', 'Clavicles slightly raised and protracted to keep the shoulder shell out of the chest when the arms reach forward.', 'Root shifted 8 cm backwards (model space) to centre the figure for previews.', 'Authored on rig/female.glb; the male uses the same rotations and the hips-height-relative root offset. The root height is the mean of the female and male heights that put the contact on y = 0, so both models land within a few millimetres of the floor.'],
               E, r, "scripts/pose_author/poses/pose_04_sitting_knees_up.py")
