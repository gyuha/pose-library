"""Independent geometry/attribute and collision checks for the canonical refined vertex pool."""
import json,sys,collections
import numpy as np
from make_female import ROOT,read,arr
from deformation import shell_labels,morph
from refine_chest import breast_height
from measure_refined import load
sys.path.insert(0,str(ROOT.parent/'tests'))
from qa_metrics import strict_intersections

def main():
 j,b,P,prims=load();T=np.concatenate(prims);mapping=json.loads((ROOT/'validation'/'chest_vertex_mapping.json').read_text());sourcefaces=np.array(mapping['triangle_source']);s,sb=read(ROOT/'male.glb');before,bb=read(ROOT/'validation'/'female_before_breast_refinement.glb');original=[];baseline=[];labels=[];oldtri=[];base=0
 for pid,m in enumerate(s['meshes']):
  at=m['primitives'][0]['attributes'];v=arr(s,sb,at['POSITION']);t=arr(s,sb,m['primitives'][0]['indices']).reshape(-1,3);labels.extend(shell_labels(v,t,pid));original.extend(v);baseline.extend(arr(before,bb,before['meshes'][pid]['primitives'][0]['attributes']['POSITION']));oldtri.extend(t+base);base+=len(v)
 labels=np.array(labels+['chest']*(len(P)-4106));oldtri=np.array(oldtri);original=np.array(original);baseline=np.array(baseline);nonchest=np.where(labels[:4106]!='chest')[0]
 assert np.array_equal(P[nonchest],baseline[nonchest]),'Non-chest positions changed'
 for name in ['TEXCOORD_0','JOINTS_0','WEIGHTS_0']:
  expected=np.concatenate([arr(s,sb,m['primitives'][0]['attributes'][name]) for m in s['meshes']]);actual=arr(j,b,j['meshes'][0]['primitives'][0]['attributes'][name]);assert np.array_equal(actual[:4106],expected),name
 at=j['meshes'][0]['primitives'][0]['attributes'];W=arr(j,b,at['WEIGHTS_0']);normals=arr(j,b,at['NORMAL']);assert np.max(abs(W.sum(1)-1))<1e-5;assert np.isfinite(P).all() and np.isfinite(normals).all();assert np.max(abs(np.linalg.norm(normals,axis=1)-1))<1e-5
 # Only test chest against other components; other geometry was byte-identical.
 chest=labels[T[:,0]]=='chest';ct=T[chest];oi=np.where(~chest)[0];ot=T[oi];csource=sourcefaces[chest]
 active_hits=set()
 def collisions(X,check_active=False):
  A=X[ct];B=X[ot];bmin=B.min(1);bmax=B.max(1);pairs=set()
  for i,a in enumerate(A):
   ids=np.where(np.all(bmax>=a.min(0)-1e-8,1)&np.all(bmin<=a.max(0)+1e-8,1))[0]
   if not len(ids):continue
   bs=B[ids];hit=np.zeros(len(ids),bool)
   for rev in [False,True]:
    aa=bs if rev else np.broadcast_to(a,bs.shape);bb=np.broadcast_to(a,bs.shape) if rev else bs;e1=bb[:,1]-bb[:,0];e2=bb[:,2]-bb[:,0]
    for k in range(3):
     o=aa[:,k];d=aa[:,(k+1)%3]-o;h=np.cross(d,e2);det=np.sum(e1*h,1);good=abs(det)>1e-10;inv=np.zeros(len(ids));inv[good]=1/det[good];ss=o-bb[:,0];u=inv*np.sum(ss*h,1);q=np.cross(ss,e1);v=inv*np.sum(d*q,1);r=inv*np.sum(e2*q,1);hit|=good&(u>1e-6)&(v>1e-6)&(u+v<1-1e-6)&(r>1e-6)&(r<1-1e-6)
   for k in np.where(hit)[0]:
    pairs.add((int(csource[i]),int(sourcefaces[oi[ids[k]]])))
    if check_active and np.max(abs(P[ct[i],2]-unexpanded[ct[i],2]))>1e-6:active_hits.add((i,int(oi[ids[k]])))
  return pairs
 oldset=strict_intersections(baseline[oldtri]);oldchest={tuple(p if labels[oldtri[p[0],0]]=='chest' else p[::-1]) for p in oldset if 'chest' in [labels[oldtri[p[0],0]],labels[oldtri[p[1],0]]]}
 unexpanded=P.copy()
 for idx in np.where(labels[:4106]=='chest')[0]:unexpanded[idx]=morph(original[idx],'chest_wall')
 for row in mapping['mapping']:unexpanded[row['index']]=np.array(row['barycentric'])@unexpanded[row['source_triangle']]
 raw_front=np.clip((unexpanded[:,2]-.005)/.065,0,1)
 unexpanded=P.copy();chest_vertex_mask=labels=='chest'
 unexpanded[chest_vertex_mask,2]-=breast_height(P[chest_vertex_mask,0],P[chest_vertex_mask,1])*raw_front[chest_vertex_mask]
 hits=collisions(P,True);control_hits=collisions(unexpanded);breast_only_new=hits-control_hits;new=hits-oldchest
 labeltri=lambda t:labels[oldtri[t,0]]
 summary=collections.Counter(labeltri(q) for p,q in new)
 # Kinematic lowered-arm proxy: rotate all arm segments around each shoulder ring center.
 static_active_count=len(active_hits)
 proxy=[]
 for angle in [30,40,45]:
  Q=P.copy();QB=unexpanded.copy()
  for sign in [-1,1]:
   side=(np.sign(original[:,0])==sign);sh=np.where((labels[:4106]=='shoulder')&side)[0];pivot=baseline[sh].mean(0);sel=np.where(np.isin(labels,['upper_arm','forearm','hand','elbow','wrist'])&(np.sign(P[:,0])==sign))[0];a=np.radians(-angle*sign);R=np.array([[np.cos(a),-np.sin(a),0],[np.sin(a),np.cos(a),0],[0,0,1]]);Q[sel]=(P[sel]-pivot)@R.T+pivot;QB[sel]=(unexpanded[sel]-pivot)@R.T+pivot
  active_hits.clear();h=collisions(Q,True);active_arm_count=sum(labels[T[t,0]] in ['upper_arm','forearm','hand'] for c,t in active_hits);hb=collisions(QB);arms=[p for p in h if labeltri(p[1]) in ['upper_arm','forearm','hand']];proxy.append({'inward_rotation_deg':angle,'expanded_breast_surface_arm_contacts':active_arm_count,'chest_arm_source_pairs':len(arms),'new_pairs_due_to_breast_volume':len([p for p in h-hb if labeltri(p[1]) in ['upper_arm','forearm','hand']]),'baseline_chest_arm_source_pairs':len([p for p in hb if labeltri(p[1]) in ['upper_arm','forearm','hand']])})
 areas=np.linalg.norm(np.cross(P[T[:,1]]-P[T[:,0]],P[T[:,2]]-P[T[:,0]]),axis=1)
 assert (areas>1e-10).all(),'Degenerate triangles'
 assert (T>=0).all() and (T<len(P)).all(),'Invalid indices'
 result={'degenerate_triangles':int((areas<1e-10).sum()),'indices_valid':True,'original_attribute_prefix_preserved':True,'non_chest_positions_identical':True,'vertices':len(P),'triangles':len(T),'append_range':mapping['append_range'],'active_displaced_breast_triangle_collisions':static_active_count,'new_static_source_pairs_due_to_breast_field':len(breast_only_new),'new_chest_collision_source_pairs_vs_previous':len(new),'new_chest_collision_by_other_part':dict(summary),'lowered_arm_proxy':proxy,'note':'The unexpanded control retains current wall/IMF/ribcage corrections and removes only the breast field. Source-face-pair changes and QA opposite-partner-face changes are different metrics. Collision counts collapse refined triangles to source-face pairs. The source already has connector and shell overlaps. Arm lowering is a rigid kinematic proxy, not a skinned animation.'};print(json.dumps(result,indent=2));(ROOT/'validation'/'refined_checks.json').write_text(json.dumps(result,indent=2))
if __name__=='__main__':main()
