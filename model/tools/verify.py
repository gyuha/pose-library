"""Independent topology, accessor, finite-value and strict surface-intersection checks."""
from make_female import *
def triangles(j,b):
 out=[]
 for m in j['meshes']:
  p=m['primitives'][0]; out.extend(arr(j,b,p['attributes']['POSITION'])[arr(j,b,p['indices']).reshape(-1,3)])
 return np.array(out,dtype=float)
def intersections(t):
 pairs=set(); mins=t.min(1); maxs=t.max(1)
 for i,a in enumerate(t):
  ids=np.where((np.arange(len(t))>i)&np.all(maxs>=mins[i]-1e-8,axis=1)&np.all(mins<=maxs[i]+1e-8,axis=1))[0]
  if not len(ids): continue
  bs=t[ids]; hit=np.zeros(len(ids),dtype=bool)
  # Test both sets of edges; exclude endpoint/shared-edge contact.
  for reverse in [False,True]:
   aa=bs if reverse else np.broadcast_to(a,bs.shape); bb=np.broadcast_to(a,bs.shape) if reverse else bs
   e1=bb[:,1]-bb[:,0]; e2=bb[:,2]-bb[:,0]
   for k in range(3):
    o=aa[:,k]; d=aa[:,(k+1)%3]-o; h=np.cross(d,e2); det=np.sum(e1*h,1); good=abs(det)>1e-10; inv=np.zeros(len(ids)); inv[good]=1/det[good]; s=o-bb[:,0]; u=inv*np.sum(s*h,1); q=np.cross(s,e1); v=inv*np.sum(d*q,1); r=inv*np.sum(e2*q,1); hit|=good&(u>1e-6)&(v>1e-6)&(u+v<1-1e-6)&(r>1e-6)&(r<1-1e-6)
  pairs.update((i,int(ids[k])) for k in np.where(hit)[0])
 return pairs
current,_=read(ROOT/'female.glb')
if len(current['meshes'])==1 and len(current['meshes'][0]['primitives'])==2:
 from check_refined import main
 main()
 raise SystemExit(0)
j,b=read(ROOT/'male.glb'); k,c=read(ROOT/'female.glb')
for m,n in zip(j['meshes'],k['meshes']):
 p=m['primitives'][0]; q=n['primitives'][0]
 assert np.array_equal(arr(j,b,p['indices']),arr(k,c,q['indices']))
 for attr in ['TEXCOORD_0','JOINTS_0','WEIGHTS_0']: assert np.array_equal(arr(j,b,p['attributes'][attr]),arr(k,c,q['attributes'][attr]))
 for attr in ['POSITION','NORMAL']: assert np.isfinite(arr(k,c,q['attributes'][attr])).all()
a=intersections(triangles(j,b)); d=intersections(triangles(k,c)); result={'exact_indices_and_vertex_order':True,'source_strict_intersection_pairs':len(a),'female_strict_intersection_pairs':len(d),'new_strict_intersection_pairs':len(d-a),'resolved_strict_intersection_pairs':len(a-d),'note':'Non-coplanar strict interior intersections; shared edges/endpoints and coplanar contacts excluded. Source mannequin has overlapping shell/joint pieces.'}; (ROOT/'validation'/'intersection_validation.json').write_text(json.dumps(result,indent=2)); print(result)
