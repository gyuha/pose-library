import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import *

PID = "pose_13_bend_forward_hands_on_knees"
PT, S1, S2, S3, S4 = 45, 8, 7, 4, 3          # trunk flexion split: pelvis (hip flexion) + spine
E = {"pelvis": [PT, 0, 0], "spine_01": [S1, 0, 0], "spine_02": [S2, 0, 0], "spine_03": [S3, 0, 0], "spine_04": [S4, 0, 0],
     "neck_01": [-34, 0, 0], "head": [-24, 0, 0], "clavicle_l": [0, 0, 10], "clavicle_r": [0, 0, -10]}
fingers(E, "l", (6, 8, 5), ([0, 0, 0], 5, 5))
fingers(E, "r", (6, 8, 5), ([0, 0, 0], 5, 5))
r = [0, -0.12, -0.2]
WB, WU, WX = 0.10, 0.115, 0.01

ay = ankle_y()
two_bone(E, r, "thigh_l", "calf_l", "foot_l", [0.17, ay, -0.06], [0.15, 0, 1])
two_bone(E, r, "thigh_r", "calf_r", "foot_r", [-0.17, ay, -0.06], [-0.15, 0, 1])
flat_foot(E, r, "l", 6); flat_foot(E, r, "r", -6)
r = ground(E, r, "sole")

E.update({"upperarm_l": [50, 0, -25], "upperarm_r": [50, 0, 25], "lowerarm_l": [-15, 0, 0], "lowerarm_r": [-15, 0, 0]})
for s, sx in (("l", 1), ("r", -1)):
    H = heads_posed("female", E, r, [f"thigh_{s}", f"calf_{s}"])
    hip, knee = H[f"thigh_{s}"], H[f"calf_{s}"]
    td = (knee - hip) / np.linalg.norm(knee - hip)                 # thigh direction (hip -> knee)
    up_n = np.array([0, 1, 0]) - td[1] * td; up_n /= np.linalg.norm(up_n)   # thigh top-surface normal
    wrist = knee - WB * td + WU * up_n + np.array([sx * WX, 0, 0])
    fdir = td + np.array([-sx * 0.25, -0.6, 0])                     # fingers down over the knee, slightly inward
    E, _, _ = ik(E, r, arm_dofs(s), [(f"hand_{s}", wrist, 30.0)],
                 extra=[axis_obj(f"hand_{s}", 1, fdir, 2.0), axis_obj(f"hand_{s}", 2, -up_n, 2.0)])
r = ground(E, r, "sole")
report(E, r, PID)

if "--write" in sys.argv:
    write_pose(PID, "Bending forward, hands on knees",
               "Standing with feet a little wider than the hips and the knees bent about 60 deg, the body hinges forward at the hips; "
               "both hands rest on the front of the thighs just above the knees with the elbows nearly straight, and the head is lifted to look ahead and slightly down. "
               "Left/right are the character's own.",
               ["Reference: user-supplied image (ai-pose-gallery.pages.dev full_single_P067, viewed only; not stored in the repository).",
                "Depth (front view only): the trunk is assumed to hinge about 45 deg at the hips (pelvis) plus about 22 deg spread over spine_01-04, with the hips pushed back and both knees bent about 60 deg (calf x 51 deg on top of the 8 deg rest bend) so the hands reach the knees; the head is extended to the neck/head limits to look forward.",
                "The hands are assumed to rest on the front of the lower thighs just above the kneecaps (palms on the thighs, fingers pointing down and slightly inward), placed so the female's palms hover about 11 mm above the thighs while the male's (shared rotations, larger hands) sink in by up to 19 mm; clavicles are raised 10 deg to keep the upper-arm shells out of the chest.",
                "Feet are assumed flat, about 34 cm apart at the ankles with the toes turned out 6 deg.",
                "Authored on rig/female.glb; the male uses the same rotations and the hips-height-relative root offset."],
               E, r, f"scripts/pose_author/poses/{PID}.py")
