from lib import *
import pickle, sys
SF,WZ,WY,CZ=[float(v) for v in sys.argv[1:5]]
E = {"pelvis":[-28,0,0], "spine_01":[SF,0,0],"spine_02":[SF,0,0],"spine_03":[SF,0,0],"spine_04":[SF*0.6,0,0],
     "neck_01":[-18,0,0],"head":[-16,0,0],"clavicle_l":[18,0,CZ],"clavicle_r":[18,0,-CZ]}
E.update({k:list(v) for k,v in ARMS_DOWN.items()})
r=[0,-0.84,0]
ay=ankle_y()
for it in range(2):
    two_bone(E,r,"thigh_l","calf_l","foot_l",[0.12,ay,0.32],[0.35,1,0.3])
    two_bone(E,r,"thigh_r","calf_r","foot_r",[-0.12,ay,0.32],[-0.35,1,0.3])
    flat_foot(E,r,"l",8); flat_foot(E,r,"r",-8)
    r=ground(E,r,"body")
fingers(E,"l",(35,45,30),([10,0,10],10,10)); fingers(E,"r",(35,45,30),([10,0,-10],10,10))
print(heads_posed("female",E,r,["calf_l","upperarm_l","spine_04","head"]))
for s,sg in (("l",1),("r",-1)):
    E[f"upperarm_{s}"]=[40,0,0]; E[f"lowerarm_{s}"]=[60,0,0]
    T=[(f"lowerarm_{s}",[sg*0.29,0.52,0.10],40),(f"hand_{s}",[sg*0.035,WY,WZ],300)]
    E,_,c=ik(E,r,arm_dofs(s,hand=False),T); print(s,"cost",round(c,2))
    E[f"hand_{s}"]=[0,0,sg*-10]
print({b:np.round(v,1).tolist() for b,v in E.items() if b.split('_')[0] in ('upperarm','lowerarm')})
print(heads_posed("female",E,r,["lowerarm_l","hand_l","lowerarm_r","hand_r"]))
report(E,r,"p04",render=len(sys.argv)>5)
pickle.dump((E,r),open("p04.pkl","wb"))
