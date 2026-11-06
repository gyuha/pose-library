from lib import *
import pickle, sys
# walking: left foot forward (heel strike), right foot back on the ball; arms swing opposite
E = {"pelvis":[2,-6,-2], "spine_01":[1,2,1],"spine_02":[1,2,0],"spine_03":[0,3,0],"spine_04":[0,3,0],
     "neck_01":[-2,-2,0],"head":[-2,-3,0],
     "upperarm_l":[-22,-4,-21],"lowerarm_l":[-10,10,0],"hand_l":[6,0,0],
     "upperarm_r":[16,-6,30],"lowerarm_r":[18,-15,0],"hand_r":[6,0,0]}
fingers(E,"l",(12,15,10),([-10,0,0],5,5)); fingers(E,"r",(12,15,10),([-10,0,0],5,5))
r=[0.0,-0.035,0.0]
ay=ankle_y()
for it in range(3):
    Rl = rigcore.axis_angle([1,0,0],-12) @ yaw(4) @ rest_global_R("foot_l")
    place_leg(E,r,"l",[0.08,ay+0.025,0.30],[0,0,1],Rl)
    ank,Rr = foot_on_ball("r",[-0.085,-0.20],-6,32)
    place_leg(E,r,"r",ank,[0,0,1],Rr)
    E["ball_r"]=[-30,0,0]
    r=ground(E,r,"sole")
print({b:np.round(v,1).tolist() for b,v in E.items() if b.split('_')[0] in ('thigh','calf','foot','ball','pelvis')})
print(heads_posed("female",E,r,["pelvis","calf_l","foot_l","foot_r","ball_r"]))
report(E,r,"p06",render=len(sys.argv)>1)
pickle.dump((E,r),open("p06.pkl","wb"))
