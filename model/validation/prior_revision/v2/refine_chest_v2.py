"""Subdivide existing chest shell; one shared canonical vertex pool, original 0:4106 intact."""
import json,struct
import numpy as np
from make_female import ROOT,read,arr
from deformation import morph,shell_labels
N=10
AMPLITUDE=.0618
CY=1.295
UPPER=.18
LOWER=.095
CX=.085

def breast_height(x,y):
 # Overlapping asymmetric lobes have one smooth midline minimum (no central ridge).
 q=np.where(y>=CY,(y-CY)/UPPER,(CY-y)/LOWER)
 q=np.clip(q,0,1)
 qu=q*q*1.1/(q+.1)
 upper=np.maximum(0,1-qu)**3.7
 lower=1-3*q**4+2*q**6
 lateral=0.
 for side in [-1,1]:
  d=side*x-CX
  width=np.where(d<0,.045,.040)
  lateral+=np.exp(-(d/width)**2)
 return AMPLITUDE*lateral*np.where(y>=CY,upper,lower)

def add_accessor(j,b,data,kind,component=5126,target=34962):
 b+=b'\0'*((-len(b))%4); offset=len(b);dtype={5126:'<f4',5125:'<u4',5123:'<u2'}[component];a=np.asarray(data,dtype=dtype);b.extend(a.tobytes());view=len(j['bufferViews']);j['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':a.nbytes,'target':target});acc={'bufferView':view,'componentType':component,'count':len(a),'type':kind}
 if kind=='VEC3':acc.update(min=a.min(0).tolist(),max=a.max(0).tolist())
 j['accessors'].append(acc);return len(j['accessors'])-1

def main():
 j,b=read(ROOT/'female.glb');source,sb=read(ROOT/'male.glb')
 attrs={name:np.concatenate([arr(j,b,m['primitives'][0]['attributes'][name]).copy() for m in j['meshes']]) for name in ['POSITION','NORMAL','TEXCOORD_0','JOINTS_0','WEIGHTS_0']}
 orig=np.concatenate([arr(source,sb,m['primitives'][0]['attributes']['POSITION']).copy() for m in source['meshes']]);body=source['meshes'][0]['primitives'][0];bt=arr(source,sb,body['indices']).reshape(-1,3).copy();jt=arr(source,sb,source['meshes'][1]['primitives'][0]['indices']).reshape(-1,3).copy()+2858
 labels=shell_labels(orig[:2858],bt,0);chest=labels[bt[:,0]]=='chest';chestids=np.where(labels=='chest')[0]
 base=attrs['POSITION'].astype(float).copy()
 for i in chestids:base[i]=morph(orig[i],'chest_wall')
 positions=list(base);uv=list(attrs['TEXCOORD_0']);joints=list(attrs['JOINTS_0']);weights=list(attrs['WEIGHTS_0']);normals=list(attrs['NORMAL']);mapping=[];cache={};newtri=[];chestfaces=[];face_source=[]
 # Reuse existing exact corner indices; append edge/interior points, respecting UV/hard seams.
 def vertex(face,w):
  nonzero=np.where(w>1e-9)[0]
  if len(nonzero)==1:return int(face[nonzero[0]])
  key=tuple(sorted((int(face[k]),int(round(w[k]*N))) for k in nonzero))
  if key in cache:return cache[key]
  idx=len(positions);cache[key]=idx;positions.append(w@base[face]);uv.append(w@attrs['TEXCOORD_0'][face]);normals.append(w@attrs['NORMAL'][face])
  blend={}
  for parent,coef in zip(face,w):
   for joint,weight in zip(attrs['JOINTS_0'][parent],attrs['WEIGHTS_0'][parent]):blend[int(joint)]=blend.get(int(joint),0)+float(coef*weight)
  top=sorted(blend.items(),key=lambda x:-x[1])[:4];top+= [(0,0)]*(4-len(top));jw=np.array([w for _,w in top]);jw/=jw.sum();joints.append([i for i,_ in top]);weights.append(jw);mapping.append({'index':idx,'source_triangle':face.tolist(),'barycentric':w.tolist()});return idx
 for source_id,(selected,face) in enumerate(zip(chest,bt)):
  if not selected:newtri.append(face.tolist());face_source.append(source_id);continue
  ids={}
  for i in range(N+1):
   for k in range(N+1-i):ids[i,k]=vertex(face,np.array([N-i-k,i,k],dtype=float)/N)
  for i in range(N):
   for k in range(N-i):
    t=[ids[i,k],ids[i+1,k],ids[i,k+1]];newtri.append(t);chestfaces.append(t);face_source.append(source_id)
    if i+k<N-1:
     t=[ids[i+1,k],ids[i+1,k+1],ids[i,k+1]];newtri.append(t);chestfaces.append(t);face_source.append(source_id)
 P=np.array(positions);B=P.copy();chestfaces=np.array(chestfaces);used=np.unique(chestfaces)
 # Displacement only on the anterior chest shell; base remains untouched everywhere else.
 front=np.clip((P[used,2]-.005)/.065,0,1)
 # A local fold return stays inside the breast footprint, outside the fit annulus.
 foot=0.
 for side in [-1,1]:
  foot+=.009*np.exp(-((P[used,0]-side*CX)/.045)**4)*np.exp(-((P[used,1]-1.185)/.017)**4)
 wall_smooth=.008*np.exp(-((P[used,1]-1.268)/.018)**2)*np.exp(-((np.abs(P[used,0])-CX)/.055)**8)
 rim=.0005*np.exp(-((P[used,1]-1.145)/.015)**2)*np.exp(-(P[used,0]/.14)**8)
 P[used,2]+=(breast_height(P[used,0],P[used,1])-foot-wall_smooth-rim)*front
 # A smooth lower ribcage return increases underbust depth inside the chest shell only.
 back=np.clip((-B[used,2]-.02)/.06,0,1)
 P[used,2]-=.0075*np.exp(-((P[used,1]-1.19)/.05)**2)*back
 # Measure breast-only volume relative to the remodeled wall, excluding ribcage/IMF corrections.
 B=P.copy();B[used,2]-=breast_height(P[used,0],P[used,1])*front
 def volume(V,T):return np.einsum('ij,ij->i',V[T[:,0]],np.cross(V[T[:,1]],V[T[:,2]]))/6
 delta=volume(P,chestfaces)-volume(B,chestfaces)
 centroid=B[chestfaces].mean(1)
 volumes=[float(delta[centroid[:,0]>0].sum()*1e6),float(delta[centroid[:,0]<0].sum()*1e6)]
 def projected_slice_volume(upper):
  total=0.
  for face in chestfaces:
   # Integrate linear displacement over each triangle clipped at peak height.
   poly=[np.array([B[k,0],B[k,1],P[k,2]-B[k,2]]) for k in face]
   out=[]
   for aa,bb in zip(poly,poly[1:]+poly[:1]):
    ina=(aa[1]>=CY) if upper else (aa[1]<=CY);inb=(bb[1]>=CY) if upper else (bb[1]<=CY)
    if ina:out.append(aa)
    if ina!=inb:out.append(aa+(bb-aa)*((CY-aa[1])/(bb[1]-aa[1])))
   for k in range(1,len(out)-1):
    aa,bb,cc=out[0],out[k],out[k+1];signed_area=((bb[0]-aa[0])*(cc[1]-aa[1])-(bb[1]-aa[1])*(cc[0]-aa[0]))/2;total+=signed_area*(aa[2]+bb[2]+cc[2])/3
  return total
 uvv=projected_slice_volume(True);lvv=projected_slice_volume(False)
 metric={'per_breast_volume_cm3':volumes,'max_projection_m':float((P[:,2]-B[:,2]).max()),'chest_peak_y_m':CY,'breast_top_y_m':CY+UPPER,'breast_bottom_y_m':CY-LOWER,'upper_lower_volume_fraction':[uvv/(uvv+lvv),lvv/(uvv+lvv)]}
 (ROOT/'validation'/'breast_metrics.json').write_text(json.dumps(metric,indent=2)); print(metric)
 # Recompute final chest normals across position-welded refinement seams.
 ns=np.array(normals);_,inv=np.unique(np.column_stack([np.round(B[used]/1e-6),np.where(((B[used,2]<.025)|(B[used,1]>1.46))[:,None],np.round(ns[used]/1e-3),0)]).astype(np.int64),axis=0,return_inverse=True);group=np.full(len(P),-1);group[used]=inv;sums=np.zeros((inv.max()+1,3));fn=np.cross(P[chestfaces[:,1]]-P[chestfaces[:,0]],P[chestfaces[:,2]]-P[chestfaces[:,0]])
 for k in range(3):np.add.at(sums,group[chestfaces[:,k]],fn)
 n=sums[inv];ns[used]=n/np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-15)
 # Fresh compact buffer. All primitives refer to the same canonical pool.
 j['accessors']=[];j['bufferViews']=[];b=bytearray();at={}
 for name,data,kind,ct in [('POSITION',P,'VEC3',5126),('NORMAL',ns,'VEC3',5126),('TEXCOORD_0',uv,'VEC2',5126),('JOINTS_0',joints,'VEC4',5123),('WEIGHTS_0',weights,'VEC4',5126)]:at[name]=add_accessor(j,b,data,kind,ct)
 prims=[]
 for tris,mat in [(newtri,0),(jt,1)]:
  ia=add_accessor(j,b,np.array(tris).reshape(-1,1),'SCALAR',5125,34963);prims.append({'attributes':at.copy(),'indices':ia,'mode':4,'material':mat})
 j['meshes']=[{'name':'Female_refined','primitives':prims}];j['nodes']=[{'name':'Female_refined','mesh':0}];j['scenes']=[{'nodes':[0]}];j['scene']=0;j['buffers']=[{'byteLength':len(b)}];j['asset']['generator']='make_female.py + refine_chest.py';j['asset']['extras']['modification']='Append-only canonical vertex pool; locally subdivided chest shell; original global indices 0..4105 retained.'
 raw=json.dumps(j,separators=(',',':')).encode();raw+=b' '*((-len(raw))%4);b+=b'\0'*((-len(b))%4);out=struct.pack('<III',0x46546c67,2,28+len(raw)+len(b))+struct.pack('<II',len(raw),0x4e4f534a)+raw+struct.pack('<II',len(b),0x004e4942)+b;(ROOT/'female.glb').write_bytes(out)
 report={'method':'uniform barycentric subdivision of connected chest shell','subdivision':N,'original_vertices':4106,'vertices':len(P),'triangles':len(newtri)+len(jt),'original_triangles':2088,'append_range':[4106,len(P)-1],'refined_chest_triangles':len(chestfaces),'mapping':mapping,'triangle_source':face_source+list(range(1456,2088))};(ROOT/'validation'/'chest_vertex_mapping.json').write_text(json.dumps(report,indent=2));print({k:v for k,v in report.items() if k not in ['mapping','triangle_source']})
if __name__=='__main__':main()
