from lib import *
import pickle
E = {"pelvis":[0,4,-2], "spine_01":[0,0,1],"spine_02":[0,0,1],"spine_03":[0,2,0],"spine_04":[0,2,0],
     "neck_01":[2,4,-3],"head":[2,6,-5],
     "clavicle_r":[0,0,-8],
     "upperarm_l":[4,0,-27],"lowerarm_l":[-10,8,0],"hand_l":[8,0,0]}
fingers(E,"l",(12,15,10),([-10,0,0],5,5))
fingers(E,"r",(3,4,2),([-10,0,-10],0,0))
r=[-0.02,-0.008,0]
ay=ankle_y()
two_bone(E,r,"thigh_l","calf_l","foot_l",[0.13,ay,0.03],[0.2,0,1])
two_bone(E,r,"thigh_r","calf_r","foot_r",[-0.10,ay,-0.01],[0,0,1])
flat_foot(E,r,"l",10); flat_foot(E,r,"r",-8)
c=arm_with_hand(E,r,"r",[-0.43,1.38,0.0],[-0.40,1.63,0.05],frame_from([0.1,1,0.05],[0,0,1]))
print("arm cost",round(c,2))
r=ground(E,r,"sole")
print({b:np.round(v,1).tolist() for b,v in E.items() if b.endswith('_r') and b.split('_')[0] in ('upperarm','lowerarm','hand')})
report(E,r,"p03")
pickle.dump((E,r),open("p03.pkl","wb"))
