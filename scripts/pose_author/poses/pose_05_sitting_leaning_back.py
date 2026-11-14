import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import *

# Sitting, leaning back on both straight arms, palms flat on the floor behind the hips; ik with hand target + axis_obj palm-down objective (see examples/p05.py).
# Reproduction script: the final Euler angles (XYZ, degrees, as stored in the pose file) and the root offset
# are encoded directly; the original IK/authoring runs were interactive and are kept only as reference in
# scripts/pose_author/examples/.
E = {
    'pelvis': [-38.0, 0.0, 0.0],
    'spine_01': [3.0, 0.0, 0.0],
    'spine_02': [3.0, 0.0, 0.0],
    'spine_03': [2.0, 0.0, 0.0],
    'neck_01': [10.0, 4.0, 0.0],
    'head': [6.0, 6.0, -4.0],
    'clavicle_l': [-8.0, 0.0, 6.0],
    'upperarm_l': [-58.94, -34.171, -16.566],
    'lowerarm_l': [12.888, 27.887, 0.0],
    'hand_l': [-62.48, 14.0, -29.0],
    'thumb_01_l': [0.0, 0.0, 8.0],
    'index_01_l': [4.0, 0.0, 0.0],
    'index_02_l': [6.0, 0.0, 0.0],
    'index_03_l': [4.0, 0.0, 0.0],
    'middle_01_l': [4.0, 0.0, 0.0],
    'middle_02_l': [6.0, 0.0, 0.0],
    'middle_03_l': [4.0, 0.0, 0.0],
    'ring_01_l': [4.0, 0.0, 0.0],
    'ring_02_l': [6.0, 0.0, 0.0],
    'ring_03_l': [4.0, 0.0, 0.0],
    'pinky_01_l': [4.0, 0.0, 0.0],
    'pinky_02_l': [6.0, 0.0, 0.0],
    'pinky_03_l': [4.0, 0.0, 0.0],
    'thigh_l': [-51.559, -3.072, 1.149],
    'calf_l': [-2.977, 0.0, 0.0],
    'foot_l': [10.0, 0.0, -6.0],
    'clavicle_r': [-8.0, 0.0, -6.0],
    'upperarm_r': [-58.844, 33.902, 16.417],
    'lowerarm_r': [12.888, -27.737, 0.0],
    'hand_r': [-62.513, -14.0, 29.0],
    'thumb_01_r': [0.0, 0.0, -8.0],
    'index_01_r': [4.0, 0.0, 0.0],
    'index_02_r': [6.0, 0.0, 0.0],
    'index_03_r': [4.0, 0.0, 0.0],
    'middle_01_r': [4.0, 0.0, 0.0],
    'middle_02_r': [6.0, 0.0, 0.0],
    'middle_03_r': [4.0, 0.0, 0.0],
    'ring_01_r': [4.0, 0.0, 0.0],
    'ring_02_r': [6.0, 0.0, 0.0],
    'ring_03_r': [4.0, 0.0, 0.0],
    'pinky_01_r': [4.0, 0.0, 0.0],
    'pinky_02_r': [6.0, 0.0, 0.0],
    'pinky_03_r': [4.0, 0.0, 0.0],
    'thigh_r': [-107.703, 3.353, 9.999],
    'calf_r': [101.653, 0.0, 0.0],
    'foot_r': [43.89, -6.233, 10.688],
}
# Root: centred on the model (z = 0, no preview-camera offset); y puts the buttocks/heels/palms on the floor.
r = [0.0, -0.837047, 0.0]

report(E, r, "pose_05_sitting_leaning_back", render=False)

if "--write" in sys.argv:
    write_pose("pose_05_sitting_leaning_back", 'Sitting on the floor, leaning back on the hands',
               "Sitting on the floor, leaning back on both straight arms with the palms flat on the floor behind the hips, fingers pointing outwards and back. Left leg stretched forward with the heel on the floor; right knee raised with the right foot flat. Head turned slightly to the left. Left/right are the character's own.",
               ['Pelvis tilted back 38 deg; palms solved with a Levenberg-Marquardt fit (palm normal down, wrist extension within the 70 deg limit).', "The palms sit 7.5 mm above the floor on the female so that the male's longer arms reach about 9 mm into it; both stay inside the 10 mm floor tolerance.", 'Authored on rig/female.glb; the male uses the same rotations and the hips-height-relative root offset. The root height is the mean of the female and male heights that put the contact on y = 0, so both models land within a few millimetres of the floor.'],
               E, r, "scripts/pose_author/poses/pose_05_sitting_leaning_back.py")
