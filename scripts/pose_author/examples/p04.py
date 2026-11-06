from lib import *
import pickle, sys
a=[float(v) for v in sys.argv[1:]] if len(sys.argv)>1 else [-28,8,0.33,0.10,0.3]
PT,SF,AZ,AX,KO=a
E = {"pelvis":[PT,0,0], "spine_01":[SF,0,0],"spine_02":[SF,0,0],"spine_03":[SF,0,0],"spine_04":[SF*0.7,0,0],
     "neck_01":[0,0,0],"head":[-8,0,0]}
E.update({k:list(v) for k,v in ARMS_DOWN.items()})
r=[0,-0.84,0]
ay=ankle_y()
for it in range(2):
    two_bone(E,r,"thigh_l","calf_l","foot_l",[AX,ay,AZ],[KO,1,0.3])
    two_bone(E,r,"thigh_r","calf_r","foot_r",[-AX,ay,AZ],[-KO,1,0.3])
    flat_foot(E,r,"l",0); flat_foot(E,r,"r",0)
    r=ground(E,r,"body")
print({b:np.round(v,1).tolist() for b,v in E.items() if b.split('_')[0] in ('thigh','calf','foot','pelvis')})
print(heads_posed("female",E,r,["pelvis","calf_l","foot_l","spine_04","upperarm_l","head"]))
report(E,r,"p04",render=False)
pickle.dump((E,r),open("p04_base.pkl","wb"))
