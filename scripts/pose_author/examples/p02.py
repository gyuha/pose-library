from lib import *
import pickle
E = {"pelvis":[0,-14,2], "spine_01":[0,-8,-1],"spine_02":[0,-8,-1],"spine_03":[2,-8,0],"spine_04":[0,-10,0],
     "neck_01":[-4,-28,3],"head":[-4,-26,4],
     "clavicle_l":[0,0,0],"clavicle_r":[-4,0,0],
     "upperarm_l":[8,0,-26],"lowerarm_l":[-8,10,0],"hand_l":[8,0,0],
     "upperarm_r":[-4,0,24],"lowerarm_r":[-5,-10,0],"hand_r":[8,0,0]}
fingers(E,"l",(12,15,10),([-10,0,0],5,5)); fingers(E,"r",(12,15,10),([-10,0,0],5,5))
r=[0.03,-0.012,0]
ay=ankle_y()
two_bone(E,r,"thigh_l","calf_l","foot_l",[0.10,ay,0.01],[0,0,1])
two_bone(E,r,"thigh_r","calf_r","foot_r",[-0.13,ay,-0.10],[-0.3,0,1])
flat_foot(E,r,"l",-6); flat_foot(E,r,"r",-20)
r=ground(E,r,"sole")
print({b:np.round(v,1).tolist() for b,v in E.items() if b.split('_')[0] in ('thigh','calf','foot','pelvis')})
report(E,r,"p02",views=("front","three_quarter","side","back_three_quarter"))
pickle.dump((E,r),open("p02.pkl","wb"))
