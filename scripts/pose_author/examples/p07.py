from lib import *
import pickle, sys
E = {"pelvis":[12,-8,-3], "spine_01":[2,3,1],"spine_02":[2,3,1],"spine_03":[1,4,0],"spine_04":[0,3,0],
     "neck_01":[-8,-2,0],"head":[-6,-3,0],
     "clavicle_l":[-6,0,0],"clavicle_r":[8,0,0],
     "upperarm_l":[-38,0,-18],"lowerarm_l":[62,10,0],"hand_l":[10,0,0],
     "upperarm_r":[42,0,22],"lowerarm_r":[68,-10,0],"hand_r":[10,0,0],
     "thigh_l":[-68,-4,-3],"calf_l":[105,0,0],"foot_l":[22,0,-4]}
fingers(E,"l",(40,55,35),([5,0,0],15,15)); fingers(E,"r",(40,55,35),([5,0,0],15,15))
r=[0.0,-0.07,0.0]
for it in range(3):
    ank,Rr = foot_on_ball("r",[-0.07,-0.20],-4,34)
    place_leg(E,r,"r",ank,[-0.05,0,1],Rr)
    E["ball_r"]=[-32,0,0]
    r=ground(E,r,"sole")
print({b:np.round(v,1).tolist() for b,v in E.items() if b.split('_')[0] in ('thigh','calf','foot','ball','pelvis')})
print(heads_posed("female",E,r,["pelvis","calf_r","foot_r","foot_l"]))
report(E,r,"p07",render=len(sys.argv)>1)
pickle.dump((E,r),open("p07.pkl","wb"))
