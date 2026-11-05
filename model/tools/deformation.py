"""Connected-shell classification and restrained feminine deformation, independent of QA."""
import numpy as np
import math

def shell_labels(pos,faces,pid):
 _,inv=np.unique(np.round(pos/1e-5).astype(np.int64),axis=0,return_inverse=True)
 parent=list(range(int(inv.max())+1))
 def root(i):
  while parent[i]!=i: parent[i]=parent[parent[i]]; i=parent[i]
  return i
 for face in inv[faces]:
  for a,b in [(face[0],face[1]),(face[1],face[2])]: parent[root(a)]=root(b)
 comps=np.array([root(int(i)) for i in inv]); labels=np.empty(len(pos),dtype=object)
 for c in set(comps):
  sel=comps==c; x,y,z=pos[sel].mean(0); x=abs(x)
  if pid==0:
   name='head' if y>1.7 else 'hand' if x>.5 and y<1.13 else 'chest' if y>1.3 and x<.02 else 'upper_arm' if x>.2 and y>1.3 else 'forearm' if x>.3 and y>1.05 else 'abdomen' if y>1.05 and x<.02 else 'pelvis' if y>.85 and x<.02 else 'thigh' if y>.6 else 'shin' if y>.25 else 'foot'
  else:
   name='neck' if y>1.55 else 'shoulder' if y>1.4 else 'elbow' if y>1.15 else 'wrist' if y>1.09 and x>.3 else 'waist_band' if y>.95 and x<.02 else 'hip_joint' if y>.7 else 'knee' if y>.35 else 'ankle'
  labels[sel]=name
 return labels

def morph(p,part):
 x,y,z=map(float,p); ax=abs(x)
 # Smooth torso field; hip articulation gets a common affine plateau.
 waist=math.exp(-((y-1.12)/.16)**2)*math.exp(-(ax/.26)**8)
 hip=math.exp(-((y-.90)/.18)**2)*math.exp(-(ax/.32)**8)
 shoulder=math.exp(-((y-1.48)/.18)**2)
 xx=x*(1-.12*waist+.27*hip-.07*shoulder)
 zz=z*(1-.05*waist)
 if part in ['pelvis','hip_joint','thigh'] and y<.99 and y>.78:
  xx=x*1.23; zz=z*1.10
 if part in ['upper_arm','forearm','hand','shoulder','elbow','wrist']:
  xx=x*.94; zz=z
 if part=='chest':
  front=max(0,min(1,(z-.005)/.065))
  zz+=.028*math.exp(-((ax-.07)/.15)**2)*math.exp(-((y-1.365)/.19)**2)*front*max(0,min(1,(y-1.20)/.12))*math.exp(-(ax/.15)**8)*max(0,min(1,(1.53-y)/.08))
 if part in ['neck','head']:
  t=.10*max(0,min(1,(y-1.62)/.06)) if part=='neck' else .06
  xx*=1-t; zz*=1-t
 return np.array([xx,y,zz])*.925

def geometry_normals(old,new,faces,original):
 # Preserve authored hard edges using source-normal smoothing groups, then area-weight final faces.
 keys=np.column_stack([np.round(old/1e-5),np.round(original/1e-3)]).astype(np.int64)
 _,groups=np.unique(keys,axis=0,return_inverse=True)
 fn=np.cross(new[faces[:,1]]-new[faces[:,0]],new[faces[:,2]]-new[faces[:,0]])
 sums=np.zeros((groups.max()+1,3))
 for k in range(3): np.add.at(sums,groups[faces[:,k]],fn)
 n=sums[groups]; return n/np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-15)
