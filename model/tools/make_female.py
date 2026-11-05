"""Exact-index GLB morph. Run with Blender's bundled Python (numpy)."""
import json,struct,math,pathlib
import numpy as np
ROOT=pathlib.Path(__file__).resolve().parents[1]
def read(path):
 b=path.read_bytes(); n=struct.unpack_from('<I',b,12)[0]; j=json.loads(b[20:20+n]); p=20+n; size=struct.unpack_from('<I',b,p)[0]; return j,bytearray(b[p+8:p+8+size])
def arr(j,b,i):
 a=j['accessors'][i]; v=j['bufferViews'][a['bufferView']]; sizes={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}; dt={5126:'<f4',5125:'<u4',5123:'<u2'}[a['componentType']]; d=np.dtype(dt); return np.ndarray((a['count'],sizes[a['type']]),dtype=d,buffer=b,offset=v.get('byteOffset',0)+a.get('byteOffset',0),strides=(v.get('byteStride',d.itemsize*sizes[a['type']]),d.itemsize))
def gauss(v,c,w): return math.exp(-((v-c)/w)**2)
def morph(p):
 x,y,z=map(float,p); ax=abs(x); s=1 if x>=0 else -1
 # Smooth, symmetric fields in source Y-up space. Front is +Z.
 torso=math.exp(-(ax/.245)**8)
 waist=gauss(y,1.12,.115)*torso
 hip=gauss(y,.91,.13)*math.exp(-(ax/.29)**8)
 shoulder=gauss(y,1.48,.14)
 xx=x*(1-.32*waist+.38*hip-.22*shoulder)
 # Arms translate inward with shoulders and become less bulky in depth.
 arm=max(0,min(1,(ax-.20)/.12))*gauss(y,1.25,.40)
 xx-=s*.037*arm
 zz=z*(1-.14*waist-.16*arm)
 # Paired breast mounds, restricted to anterior chest surface.
 front=max(0,min(1,(z-.005)/.065))
 zz+=.085*gauss(ax,.095,.071)*gauss(y,1.365,.085)*front*torso
 # Rounded gluteal mass and fuller upper thighs.
 zz-=.048*gauss(y,.91,.11)*gauss(ax,.11,.12)*max(0,min(1,(-z+.005)/.065))
 thigh=gauss(y,.72,.17)*gauss(ax,.13,.10)
 xx+=s*.018*thigh
 zz*=1+.12*thigh
 # Narrow neck, tapered jaw, smaller softer head.
 neck=gauss(y,1.635,.065)*math.exp(-(ax/.09)**6)
 xx*=1-.17*neck; zz*=1-.12*neck
 head=max(0,min(1,(y-1.69)/.055))
 xx*=1-.08*head-.10*gauss(y,1.72,.045)
 zz*=1-.06*head
 return np.array([xx*.925,y*.925,zz*.925])
def main():
 j,b=read(ROOT/'male.glb'); report={'source_nodes':len(j['nodes']),'source_skins':len(j.get('skins',[])),'source_joints':len(j['skins'][0]['joints']),'meshes':[]}
 allold=[]; allnew=[]
 for m in j['meshes']:
  p=m['primitives'][0]; old=arr(j,b,p['attributes']['POSITION']).copy(); new=np.array([morph(v) for v in old]); arr(j,b,p['attributes']['POSITION'])[:]=new
  a=j['accessors'][p['attributes']['POSITION']]; a['min']=new.min(axis=0).tolist(); a['max']=new.max(axis=0).tolist()
  # Transform original normals by inverse transpose of numerical deformation Jacobian.
  normals=arr(j,b,p['attributes']['NORMAL']); orig=normals.copy(); mindet=1e9
  for i,v in enumerate(old):
   eps=1e-4; jac=np.column_stack([(morph(v+np.eye(3)[k]*eps)-morph(v-np.eye(3)[k]*eps))/(2*eps) for k in range(3)])
   mindet=min(mindet,float(np.linalg.det(jac))); n=np.linalg.solve(jac.T,orig[i]); normals[i]=n/np.linalg.norm(n)
  faces=arr(j,b,p['indices']).reshape(-1,3); a0=np.cross(old[faces[:,1]]-old[faces[:,0]],old[faces[:,2]]-old[faces[:,0]]); a1=np.cross(new[faces[:,1]]-new[faces[:,0]],new[faces[:,2]]-new[faces[:,0]])
  report['meshes'].append({'name':m['name'],'vertices':len(old),'triangles':len(faces),'min_sampled_jacobian_determinant':mindet,'degenerate_triangles':int((np.linalg.norm(a1,axis=1)<1e-10).sum()),'face_normal_reversals':int((np.sum(a0*a1,axis=1)<0).sum())})
  m['name']=m['name'].replace('Male_v2','Female'); allold.extend(old); allnew.extend(new)
 # Clean static rest meshes; preserve vertex attributes including source weights for transfer.
 j['nodes']=[{'name':'Female_Body','mesh':0},{'name':'Female_Joints','mesh':1}]; j['scenes']=[{'nodes':[0,1]}]; j['scene']=0; j.pop('skins',None); j.pop('animations',None)
 j['asset']['generator']='make_female.py; exact topology morph'; j['asset']['extras']['title']='Female mannequin base'; j['asset']['extras']['modification']='Procedural feminine proportions; 0.925 height; static unskinned base; source joint attributes retained.'
 raw=json.dumps(j,separators=(',',':')).encode(); raw+=b' '*((-len(raw))%4); b+=b'\0'*((-len(b))%4)
 out=struct.pack('<III',0x46546c67,2,12+8+len(raw)+8+len(b))+struct.pack('<II',len(raw),0x4e4f534a)+raw+struct.pack('<II',len(b),0x004e4942)+b
 (ROOT/'female.glb').write_bytes(out)
 for key,vs in [('male',allold),('female',allnew)]:
  v=np.array(vs); report[key+'_bbox']=[v.min(axis=0).tolist(),v.max(axis=0).tolist()]; report[key+'_height']=float(np.ptp(v[:,1]))
 report['height_ratio']=report['female_height']/report['male_height']; (ROOT/'validation.json').write_text(json.dumps(report,indent=2)); print(json.dumps(report,indent=2))
if __name__=='__main__': main()
