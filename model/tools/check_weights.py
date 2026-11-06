"""Read-only skin-weight report for the chest shell (for the rigger; weights are not repainted here).

Groups joints of the source skin (spine / neck / shoulder / upper arm / other) and reports, for original and
appended chest vertices, the weight share per group, with emphasis on shoulder/arm influence inside the breast
mounds. Writes validation/chest_weight_check.json.
"""
import json
import numpy as np
from make_female import ROOT,read,arr
from deformation import shell_labels

GROUPS={'spine':['DEF-spine'],'neck_head':['DEF-neck','DEF-head'],'shoulder':['DEF-shoulder'],'upper_arm':['DEF-upper_arm'],'lower_arm_hand':['DEF-forearm','DEF-hand','DEF-f_','DEF-thumb']}

def main():
 s,sb=read(ROOT/'male.glb');names=[s['nodes'][i]['name'] for i in s['skins'][0]['joints']]
 group=np.array([next((g for g,p in GROUPS.items() if any(n.startswith(x) for x in p)),'other') for n in names])
 j,b=read(ROOT/'female.glb');at=j['meshes'][0]['primitives'][0]['attributes']
 P=arr(j,b,at['POSITION']).astype(float);J=arr(j,b,at['JOINTS_0']).astype(int);W=arr(j,b,at['WEIGHTS_0']).astype(float)
 bt=arr(s,sb,s['meshes'][0]['primitives'][0]['indices']).reshape(-1,3);labels=shell_labels(arr(s,sb,s['meshes'][0]['primitives'][0]['attributes']['POSITION']),bt,0)
 T=np.concatenate([arr(j,b,p['indices']).reshape(-1,3) for p in j['meshes'][0]['primitives'][:1]]);used=np.unique(T)
 chest=np.zeros(len(P),bool);chest[:2858]=labels=='chest';chest[4106:]=True;chest&=np.isin(np.arange(len(P)),used)
 share=np.zeros((len(P),len(GROUPS)+1));keys=list(GROUPS)+['other']
 for k,g in enumerate(keys):share[:,k]=(W*(group[J]==g)).sum(1)
 arm=share[:,keys.index('shoulder')]+share[:,keys.index('upper_arm')]+share[:,keys.index('lower_arm_hand')]
 # breast mound: front of the chest, inside the footprint band (both sides), where a raised arm must not pull
 mound=chest&(np.abs(P[:,0])>.02)&(np.abs(P[:,0])<.14)&(P[:,1]>1.19)&(P[:,1]<1.37)&(P[:,2]>.06)
 def summary(sel):
  if not sel.any():return None
  return {'vertices':int(sel.sum()),'mean_share':{k:round(float(share[sel,i].mean()),4) for i,k in enumerate(keys)},
   'max_shoulder_arm_share':round(float(arm[sel].max()),4),'vertices_with_shoulder_arm_over_0.05':int((arm[sel]>.05).sum()),
   'dominant_joint_counts':{names[int(k)]:int(v) for k,v in zip(*np.unique(J[sel][np.arange(sel.sum()),W[sel].argmax(1)],return_counts=True))}}
 orig=chest.copy();orig[4106:]=False;new=chest.copy();new[:4106]=False
 worst=np.where(chest)[0][np.argsort(-arm[chest])][:8]
 r={'groups':{g:[n for n,gg in zip(names,group) if gg==g] for g in keys},'all_chest_original':summary(orig),'all_chest_appended':summary(new),
  'breast_mound_appended':summary(mound&new),'breast_mound_original_reference':summary(mound&orig),
  'highest_shoulder_arm_share':[{'index':int(i),'xyz':np.round(P[i],4).tolist(),'share':round(float(arm[i]),4),'joints':[names[int(x)] for x in J[i]],'weights':np.round(W[i],4).tolist()} for i in worst],
  'weights_sum_max_error':float(np.abs(W[chest].sum(1)-1).max()),
  'note':'Appended vertices interpolate the source chest-shell triangle under them (barycentric, per joint id, top 4 renormalised). Breast mound = |x| 0.02-0.14, y 1.19-1.37, z>0.06.'}
 (ROOT/'validation'/'chest_weight_check.json').write_text(json.dumps(r,indent=2));print(json.dumps({k:v for k,v in r.items() if k!='groups'},indent=1))
if __name__=='__main__':main()
