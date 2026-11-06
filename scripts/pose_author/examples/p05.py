from lib import *
import pickle, sys
PT,WZ,WX=[float(v) for v in sys.argv[2:5]]
E = {"pelvis":[PT,0,0], "spine_01":[3,0,0],"spine_02":[3,0,0],"spine_03":[2,0,0],"spine_04":[0,0,0],
     "neck_01":[10,4,0],"head":[6,6,-4],"clavicle_l":[-8,0,6],"clavicle_r":[-8,0,-6]}
E.update({k:list(v) for k,v in ARMS_DOWN.items()})
fingers(E,"l",(4,6,4),([0,0,8],0,0)); fingers(E,"r",(4,6,4),([0,0,-8],0,0))
r=[0,-0.84,0.0]
ay=ankle_y()
for it in range(2):
    two_bone(E,r,"thigh_l","calf_l","foot_l",[0.13,0.085,0.82],[0,1,0.1])
    E["foot_l"]=[10,0,-6]
    two_bone(E,r,"thigh_r","calf_r","foot_r",[-0.15,ay,0.40],[-0.15,1,0.3])
    flat_foot(E,r,"r",-8)
    r=ground(E,r,"body")
G=heads_posed("female",E,r,["pelvis","upperarm_l","calf_l","foot_l","calf_r"]); print(G)
for s,sg in (("l",1),("r",-1)):
    wy=0.08
    E[f"upperarm_{s}"]=[-30,0,sg*10]; E[f"lowerarm_{s}"]=[-20,0,0]; E[f"hand_{s}"]=[-60,0,0]
    for it in range(3):
        T=[(f"hand_{s}",[sg*WX,wy,WZ],300)]
        ex=[axis_obj(f"hand_{s}",2,[0,-1,0],20), axis_obj(f"hand_{s}",1,[sg*0.6,0,-0.8],3)]
        E,_,c=ik(E,r,arm_dofs(s),T,extra=ex)
        low=lowest("female",E,r,HAND_BONES[s]); wy-=low-0.0075
    print(s,"cost",round(c,2),"wrist y",round(wy,3),"hand low",round(low,4))

print({b:np.round(v,1).tolist() for b,v in E.items() if b.split('_')[0] in ('upperarm','lowerarm','hand','thigh','calf','foot','pelvis')})
print(heads_posed("female",E,r,["hand_l","hand_r","foot_l"]))
report(E,r,"p05",render=len(sys.argv)>1)
pickle.dump((E,r),open("p05.pkl","wb"))
