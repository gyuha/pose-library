import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import *   # noqa: F401,F403
import numpy as np

# 1) Torso / head / clavicles (Euler [X, Y, Z] deg, rest local frame).
E = {"pelvis": [0, 0, 0], "spine_01": [0, 0, 0], "spine_02": [0, 0, 0], "spine_03": [-2, 0, 0], "spine_04": [-2, 0, 0],
     "neck_01": [2, 0, 0], "head": [2, 0, 0],
     "clavicle_l": [0, 0, 22], "clavicle_r": [0, 0, -22]}
fingers(E, "l", (4, 4, 2), ([-5, 0, 0], 0, 0))
fingers(E, "r", (4, 4, 2), ([-5, 0, 0], 0, 0))
r = [0, 0, 0]

# 2) Legs: straight, feet a little wider than the hips, toes slightly out.
ay = ankle_y()
two_bone(E, r, "thigh_l", "calf_l", "foot_l", [0.165, ay, -0.06], [0, 0, 1])
two_bone(E, r, "thigh_r", "calf_r", "foot_r", [-0.165, ay, -0.06], [0, 0, 1])
flat_foot(E, r, "l", 8); flat_foot(E, r, "r", -8)

# Arms: nearly vertical overhead, upper arm ~10 deg out from vertical, elbow almost straight,
# palms facing each other, turned ~30 deg forward, arms assumed in the frontal plane (slightly forward).
UA, FA = bone_len("upperarm_l", "lowerarm_l"), bone_len("lowerarm_l", "hand_l")
for s, sg in (("l", 1), ("r", -1)):
    sh = heads_posed("female", E, r, [f"upperarm_{s}"])[f"upperarm_{s}"]
    d1 = np.array([sg * np.sin(np.radians(10)), 1.0, 0.03]); d1 /= np.linalg.norm(d1)
    d2 = np.array([sg * np.sin(np.radians(4)), 1.0, 0.0]); d2 /= np.linalg.norm(d2)
    elbow = sh + UA * d1
    wrist = elbow + FA * 0.999 * d2
    arm_with_hand(E, r, s, elbow, wrist, frame_from([sg * 0.03, 1, 0], [-sg * 1, 0, 0.6]))

# 3) Ground + checks.
r = ground(E, r, "sole")
report(E, r, "pose_10_overhead_stretch")

if "--write" in sys.argv:
    write_pose("pose_10_overhead_stretch", "Standing overhead stretch",
               "Standing upright with the feet a little wider than the hips and both arms stretched straight overhead, "
               "slightly spread, palms facing each other and turned a little forward. Left/right are the character's own.",
               ["Reference: user-supplied image (ai-pose-gallery.pages.dev full_single_P019, viewed only; not stored in the repository).",
                "Front view only: the arms are assumed to lie in the frontal plane with a slight forward tilt (~2 deg); torso and head are upright with no lean.",
                "Palms are assumed to face each other, turned ~30 deg forward, read from the narrow edge-on hands in the image.",
                "Shoulders are elevated with clavicle_* (~22 deg) as in an overhead reach.",
                "Authored on rig/female.glb; the male uses the same rotations and the hips-height-relative root offset."],
               E, r, "scripts/pose_author/poses/pose_10_overhead_stretch.py")
