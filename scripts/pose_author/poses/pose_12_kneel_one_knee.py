import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import *  # noqa: F401,F403

# Kneeling on the left knee, right knee raised with the right foot flat in front.
# Right hand on the right knee, left hand laid over it. Torso upright.
E = {"pelvis": [0, 0, 0], "spine_01": [10, -4, 0], "spine_02": [10, -4, 0], "spine_03": [8, -4, 0], "spine_04": [0, 0, 0],
     "neck_01": [-10, 0, 0], "head": [-10, 0, 0], "clavicle_l": [6, 0, 0], "clavicle_r": [10, 0, 0]}
E.update({k: list(v) for k, v in ARMS_DOWN.items()})
fingers(E, "l", (4, 6, 4), ([0, 0, 0], 5, 5))
fingers(E, "r", (6, 8, 5), ([0, 0, 0], 5, 5))
r = [0.0, -0.50, 0.0]
ay = ankle_y()
hh = model("female").skeleton.hips_height
L1, L2 = bone_len("thigh_l", "calf_l"), bone_len("calf_l", "foot_l")
THIGH_L = np.array([0.12, -1.0, -0.10])   # down thigh: near vertical, knee a little outside and behind
SHIN_L = np.array([0.30, 0.10, -1.0])     # shin lies back and slightly outward
SHIN_R = [0.02, -1.0, -0.10]              # front shin about vertical
fy = 0.0  # front thigh pitch (y component), adjusted so the right sole lands on the floor


def unit(v):
    return np.asarray(v, float) / np.linalg.norm(v)


for it in range(12):
    # front (right) leg: foot flat in front, shin about vertical
    Hr = heads_posed("female", E, r, ["thigh_r"])["thigh_r"]
    kn_r = Hr + L1 * unit([-0.10, fy, 1.0])
    place_limb(E, r, "thigh_r", "calf_r", kn_r, kn_r + L2 * unit(SHIN_R))
    flat_foot(E, r, "r", -4)
    # down (left) leg: knee on the floor, foot pointed so the instep rests near the floor
    H = heads_posed("female", E, r, ["thigh_l"])["thigh_l"]
    knee = H + L1 * THIGH_L / np.linalg.norm(THIGH_L)
    ankle = knee + L2 * SHIN_L / np.linalg.norm(SHIN_L)
    place_limb(E, r, "thigh_l", "calf_l", knee, ankle)
    E["foot_l"] = [45, 0, 0]
    E["ball_l"] = [10, 0, 0]
    leg_low = lowest("female", E, r, ["thigh_l", "calf_l", "foot_l", "ball_l"])
    r = [r[0], r[1] - leg_low / hh, r[2]]
    fy -= 2.0 * lowest("female", E, r, ["foot_r", "ball_r"])
r = ground(E, r, "body")
G = heads_posed("female", E, r, ["thigh_l", "calf_l", "foot_l", "ball_l", "calf_r", "foot_r", "upperarm_l", "upperarm_r"])
print(G)
kr = G["calf_r"]


def place_arm(E, s, wrist, elbow, finger_dir, w_elbow):
    """Limit-respecting arm IK: wrist on target, palm down, fingers along finger_dir, elbow pulled towards `elbow`."""
    sg = 1 if s == "l" else -1
    E[f"upperarm_{s}"], E[f"lowerarm_{s}"], E[f"hand_{s}"] = [40, 0, sg * -20], [70, 0, 0], [0, 0, 0]
    ex = [axis_obj(f"hand_{s}", 2, [0, -1, 0], 5), axis_obj(f"hand_{s}", 1, finger_dir, 3),
          lambda G: (G[rigcore.INDEX[f"lowerarm_{s}"]][:3, 3] - elbow) * w_elbow]
    E2, _, _ = ik(E, r, arm_dofs(s), [(f"hand_{s}", wrist, 300)], extra=ex)
    E.update(E2)


# right arm: elbow out to the side, hand on top of the right knee with fingers pointing inward
place_arm(E, "r", kr + [-0.06, 0.12, -0.03], np.array([-0.30, 0.75, 0.12]), [0.6, -0.1, 0.75], 1.0)
# left arm: elbow out to the left side, forearm across the belly, hand laid over the right hand's fingers
place_arm(E, "l", kr + [0.25, 0.12, -0.03], np.array([0.27, 0.80, 0.22]), [-0.8, -0.1, 0.55], 3.0)
print(heads_posed("female", E, r, ["hand_l", "hand_r", "lowerarm_l", "lowerarm_r"]))
print("sole_r female/male", {n: round(lowest(n, E, r, ["foot_r", "ball_r"]) * 1e3, 1) for n in ("female", "male")})
report(E, r, "pose_12_kneel_one_knee")

if "--write" in sys.argv:
    write_pose("pose_12_kneel_one_knee", "Kneeling on one knee, hands on the raised knee",
               "Kneels on the left knee with the left shin lying back on the floor and the foot pointed; the right knee is "
               "raised with the right foot flat on the floor in front. The torso leans forward and turns slightly to the right; "
               "the right hand rests palm-down on top of the right knee and the left forearm crosses in front of the belly so "
               "the left hand rests beside it on the inner side of the knee. Left/right are the character's own.",
               ["Reference: user-supplied image (ai-pose-gallery.pages.dev full_single_P033, viewed only; not stored in the repository).",
                "Front view only: the left shin is assumed to lie straight back on the floor (slightly outward) with the foot "
                "plantarflexed so the instep faces the floor, rather than toes tucked.",
                "The right shin is assumed near vertical with the knee about level with the hip, which puts the knee ~0.35 m in "
                "front of the hip on this rig; to reach it with bent elbows the torso leans forward ~28 deg and turns ~12 deg "
                "to the right (the reference torso looks more upright).",
                "The left hand is placed beside the right hand on the inner side of the knee instead of stacked on top of it: "
                "reaching further across pushes the left upper arm past the joint limit and the 60 mm upperarm~torso cap.",
                "Authored on rig/female.glb; the male uses the same rotations and the hips-height-relative root offset."],
               E, r, "scripts/pose_author/poses/pose_12_kneel_one_knee.py")
