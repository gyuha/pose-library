import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import *

# Deep squat, feet flat, knees forward and slightly apart, hands resting on the knees.
E = {"pelvis": [0, 0, 0], "spine_01": [11, 0, 0], "spine_02": [11, 0, 0], "spine_03": [7, 0, 0], "spine_04": [0, 0, 0],
     "neck_01": [-22, 0, 0], "head": [-12, 0, 0]}
E.update({k: list(v) for k, v in ARMS_DOWN.items()})
fingers(E, "l", (8, 10, 6), ([-20, 0, 5], 0, 0)); fingers(E, "r", (8, 10, 6), ([-20, 0, -5], 0, 0))
r = [0, -0.6, -0.18]
ay = ankle_y()
AX, KO = 0.09, 0.15
for it in range(2):
    two_bone(E, r, "thigh_l", "calf_l", "foot_l", [AX, ay, 0.0], [KO, 0.3, 1])
    two_bone(E, r, "thigh_r", "calf_r", "foot_r", [-AX, ay, 0.0], [-KO, 0.3, 1])
    flat_foot(E, r, "l", 6); flat_foot(E, r, "r", -6)
    r = ground(E, r, "body")

K = heads_posed("female", E, r, ["calf_l", "calf_r"])
for s, sg in (("l", 1), ("r", -1)):
    k = K[f"calf_{s}"]
    wrist = [k[0] - sg * 0.01, k[1] + 0.12, k[2] - 0.02]
    arm_ik(E, r, s, wrist, [sg * 0.4, 0, -1], frame_from([sg * 0.1, -1, 0.9], [0, -0.7, -1]))
print({b: np.round(v, 1).tolist() for b, v in E.items() if b.split('_')[0] in ('upperarm', 'lowerarm', 'hand', 'thigh', 'calf', 'foot')})
report(E, r, "pose_11_squat_hands_on_knees")

if "--write" in sys.argv:
    write_pose("pose_11_squat_hands_on_knees", "Deep squat, hands on knees",
               "Deep squat with both feet flat on the floor and the hips below knee height, knees pointing forward "
               "and slightly apart, trunk leaning forward a little. Both hands rest on top of the knees with the fingers "
               "hanging over the kneecaps; the head is raised to look forward. Left/right are the character's own.",
               ["Reference: user-supplied image (ai-pose-gallery.pages.dev full_single_P061, viewed only; not stored in the repository).",
                "Front view only: the depth layout (hips about 0.18 hips-height behind the ankles, trunk flexed ~29 deg "
                "through spine_01-03, head extended back to face forward) is assumed for balance with flat feet.",
                "Feet flat: ankle dorsiflexion is capped at 25 deg by the rig limits, so the shins lean ~21 deg and the "
                "hips sit slightly behind rather than straight above the heels; buttocks stay off the floor.",
                "Knees forward and slightly apart (thighs abducted ~10 deg, externally rotated ~12 deg); feet toed out 6 deg.",
                "Hands placed palm-down on the knees with the fingers draped forward over the kneecaps; thumbs extended "
                "(thumb_01 x = -20) so the male thumb tip does not sink into the inner knee.",
                "Authored on rig/female.glb; the male uses the same rotations and the hips-height-relative root offset."],
               E, r, "scripts/pose_author/poses/pose_11_squat_hands_on_knees.py")
