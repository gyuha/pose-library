from lib import *
import pickle, sys
AIR=float(sys.argv[2]) if len(sys.argv)>2 else 0.30
E = {"pelvis":[-6,0,0], "spine_01":[2,0,0],"spine_02":[0,0,0],"spine_03":[-3,0,0],"spine_04":[-2,0,0],
     "neck_01":[-6,0,0],"head":[-8,0,0],
     "clavicle_l":[0,0,16],"clavicle_r":[0,0,-16],
     "upperarm_l":[48,-10,62],"lowerarm_l":[-15,-20,0],"hand_l":[-10,0,0],
     "upperarm_r":[48,10,-62],"lowerarm_r":[-15,20,0],"hand_r":[-10,0,0],
     "thigh_l":[-62,-8,-8],"calf_l":[105,0,0],"foot_l":[35,0,-4],"ball_l":[10,0,0],
     "thigh_r":[-55,8,8],"calf_r":[110,0,0],"foot_r":[35,0,4],"ball_r":[10,0,0]}
fingers(E,"l",(0,4,2),([-15,0,15],0,0)); fingers(E,"r",(0,4,2),([-15,0,-15],0,0))
for s,sg in (("l",1),("r",-1)):
    for f,z in (("index",8),("ring",-6),("pinky",-12)):
        E[f"{f}_01_{s}"][2]=sg*z
r=ground(E,[0,0,0],"body",airborne=AIR)
for n in ("female","male"):
    V=skin(n,E,r); print(n,"top y",round(V[:,1].max(),3),"rest top",round(model(n).pos[:,1].max(),3))
report(E,r,"p08",render=sys.argv[1]=="r")
pickle.dump((E,r),open("p08.pkl","wb"))
