"""Deterministic headless orthographic triangle rasterizer; no GUI/OpenGL required."""
from make_female import *
import zlib,binascii
W,H=720,900
def png(path,a):
 def chunk(t,d): return struct.pack('>I',len(d))+t+d+struct.pack('>I',binascii.crc32(t+d)&0xffffffff)
 path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',W,H,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(b'\0'+r.tobytes() for r in a)))+chunk(b'IEND',b''))
def render(which,angle,label,closeup=False):
 j,b=read(ROOT/(which+'.glb')); a=math.radians(angle); R=np.array([[math.cos(a),0,-math.sin(a)],[0,1,0],[math.sin(a),0,math.cos(a)]])
 img=np.full((H,W,3),235,dtype=np.uint8); depth=np.full((H,W),-1e9); light=np.array([-.35,.6,.72]); light/=np.linalg.norm(light)
 for p in [p for m in j['meshes'] for p in m['primitives']]:
  v=arr(j,b,p['attributes']['POSITION'])@R.T; ns=arr(j,b,p['attributes']['NORMAL'])@R.T; faces=arr(j,b,p['indices']).reshape(-1,3); screen=np.column_stack([W/2+(v[:,0]+(.11 if closeup else 0))*(2100 if closeup else 425),(H/2+(1.29-v[:,1])*2100) if closeup else H-40-v[:,1]*425,v[:,2]])
  base=np.array([168,164,160]) if p['material']==0 else np.array([53,57,61])
  for f in faces:
   tri=screen[f]; lo=np.maximum(np.floor(tri[:,:2].min(0)).astype(int),[0,0]); hi=np.minimum(np.ceil(tri[:,:2].max(0)).astype(int),[W-1,H-1])
   if np.any(hi<lo): continue
   X,Y=np.meshgrid(np.arange(lo[0],hi[0]+1)+.5,np.arange(lo[1],hi[1]+1)+.5); x0,y0=tri[0,:2]; x1,y1=tri[1,:2]; x2,y2=tri[2,:2]; den=(y1-y2)*(x0-x2)+(x2-x1)*(y0-y2)
   if abs(den)<1e-10: continue
   u=((y1-y2)*(X-x2)+(x2-x1)*(Y-y2))/den; v0=((y2-y0)*(X-x2)+(x0-x2)*(Y-y2))/den; w=1-u-v0; z=u*tri[0,2]+v0*tri[1,2]+w*tri[2,2]; sl=np.s_[lo[1]:hi[1]+1,lo[0]:hi[0]+1]; mask=(u>=0)&(v0>=0)&(w>=0)&(z>depth[sl]); n=np.cross(v[f[1]]-v[f[0]],v[f[2]]-v[f[0]]); n/=max(np.linalg.norm(n),1e-15); shade=np.full(X.shape,.38+.62*max(0,float(n@light))); colors=np.clip(shade[:,:,None]*base,0,255).astype(np.uint8); img[sl][mask]=colors[mask]; depth[sl][mask]=z[mask]
 png(ROOT/'previews'/f'{which}_{label}.png',img)
for which in ['male','female']:
 for angle,label in [(0,'front'),(90,'side'),(35,'three_quarter')]: render(which,angle,label)

render('female',90,'chest_side',True)
