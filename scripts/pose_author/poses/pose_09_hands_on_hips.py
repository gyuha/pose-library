import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import *

# Torso / head / clavicles: upright, square to camera, chin slightly up.
E = {"pelvis": [0, 0, 0], "spine_01": [0, 0, 0], "spine_02": [-1, 0, 0], "spine_03": [-1, 0, 0], "spine_04": [0, 0, 0],
     "neck_01": [0, 0, 0], "head": [-3, 0, 0], "clavicle_l": [-4, 0, 4], "clavicle_r": [-4, 0, -4]}
fingers(E, "l", (15, 15, 10), ([0, 0, 0], 0, 0))
fingers(E, "r", (15, 15, 10), ([0, 0, 0], 0, 0))
r = [0, 0, 0]

# Legs: wide stance, knees straight, toes turned out a little.
ay = ankle_y()
two_bone(E, r, "thigh_l", "calf_l", "foot_l", [0.22, ay, -0.03], [0.2, 0, 1])
two_bone(E, r, "thigh_r", "calf_r", "foot_r", [-0.22, ay, -0.03], [-0.2, 0, 1])
flat_foot(E, r, "l", 10); flat_foot(E, r, "r", -10)

# Arms: wrists on the front-lateral waist above the iliac crest, elbows out to the side and back,
# fingers forward-down towards the groin. Seed with arm_ik, then refine elbow+wrist+hand direction with ik
# (joint limits enforced; upperarm internal rotation saturates near its 70 deg limit).
ELBOW, WRIST = [0.37, 1.21, -0.15], [0.205, 1.035, -0.035]
for s, k in (("l", 1), ("r", -1)):
    m = lambda v: [k * v[0], v[1], v[2]]
    R = frame_from([k * -0.15, -0.75, 0.6], [k * -1.0, 0, -0.2])
    arm_ik(E, r, s, m([0.18, 0.99, 0.0]), [k * 1.0, 0.1, -1.3], R)
    E, _, c = ik(E, r, arm_dofs(s) + [(f"clavicle_{s}", 0), (f"clavicle_{s}", 2)],
                 [(f"lowerarm_{s}", m(ELBOW), 2.0), (f"hand_{s}", m(WRIST), 4.0)],
                 extra=[axis_obj(f"hand_{s}", 1, R[:, 1], 0.5), axis_obj(f"hand_{s}", 2, R[:, 2], 0.5)])

r = ground(E, r, "sole")
print({b: np.round(v, 1).tolist() for b, v in E.items() if b.split('_')[0] in ('upperarm', 'lowerarm', 'hand', 'clavicle')})
print(heads_posed("female", E, r, ["upperarm_l", "lowerarm_l", "hand_l", "middle_01_l", "lowerarm_r", "hand_r"]))
report(E, r, "pose_09_hands_on_hips")

if "--write" in sys.argv:
    write_pose("pose_09_hands_on_hips", "Standing, hands on hips",
               "Standing upright and square to the viewer with the feet planted wider than the hips, toes turned slightly out "
               "and both knees straight. Both hands rest on the sides of the waist just above the hips, fingers pointing "
               "forward and down, with the elbows bent and flared out to the sides and slightly back. Head level, facing "
               "forward. Left/right are the character's own.",
               ["Reference: user-supplied image (ai-pose-gallery.pages.dev full_single_P018, viewed only; not stored in the repository).",
                "Single front view, so depth is assumed: torso upright with no twist; ankles ~0.44 m apart and ~3 cm behind "
                "the hip line, feet flat and turned out 10 deg each.",
                "Hands: wrists on the front-lateral waist just above the iliac crest (female wrist ~0.22 m off the midline, "
                "~2 cm behind the pelvis centre), palms facing the body, fingers pointing forward-down; elbows ~8 cm behind "
                "the shoulders. The drawing's elbows flare further out in the frontal plane, but that needs upper-arm internal "
                "rotation beyond the 70 deg limit, so the elbows sit back and the upper-arm internal rotation is held at 69 deg.",
                "Shoulders raised slightly (clavicle elevation ~14 deg) to let the elbows flare; the upper-arm shells then sink "
                "~44 mm (female) / ~47 mm (male) into the torso, within the 60 mm upperarm~torso allowance.",
                "Authored on rig/female.glb; the male uses the same rotations and the hips-height-relative root offset. "
                "On the male the palms end ~4-5 cm off the pelvis surface (narrower hips relative to arm span)."],
               E, r, "scripts/pose_author/poses/pose_09_hands_on_hips.py")
