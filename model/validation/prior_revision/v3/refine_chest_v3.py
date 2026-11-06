"""Low-poly faceted chest remesh with breast edge flow; one shared canonical pool, original 0:4106 intact.

The front of the connected chest shell (both halves) is replaced by a new patch whose boundary is made of
original shell edges. Per breast: an apex pole, 16-segment rings laid on contour lines of a teardrop
displacement, one plain wall ring, then straight runs to the closest points of the shell boundary (sternum,
upper chest/axilla, side, under-bust edge) and a rim strip that tucks under at the shell's bottom edge.
Side/top faces sharing a subdivided boundary edge are fanned in their own plane (no T-junctions). Each
quad/triangle carries its own flat normal, matching the faceted source mannequin. Deterministic; NumPy only.
"""
import json,struct
import numpy as np
from make_female import ROOT,read,arr
from deformation import morph,shell_labels

# ---- design parameters (female metres, Y-up, +Z front; right breast, left is mirrored) ----
CENTER=np.array([.079,1.274])              # footprint centre of the displacement (the apex is placed at the most projecting point)
# footprint radius by direction (deg: 0 lateral, 90 up, 180 medial, 270 down): wide base, upper-lateral tail to the axilla
RADIUS={0:.068,45:.090,90:.101,135:.086,180:.062,225:.082,270:.076,315:.082}
PROJECTION=.052                             # peak displacement along the breast axis
LEAN=np.radians(10)                         # breast axis yaw: lateral lean of the mass (rests on the curved ribcage)
SEGMENTS=16
RING_LEVELS=[.94,.8,.6,.4,.22,.08,0.]          # rings are contour lines of the displacement (fraction of the apex height)
WALL_RING=.5                                     # one plain ring halfway between the footprint and the shell boundary
UPPER_EXP=3.2                               # upper pole: (1-r)^c(1+cr+ar^2), straight/slightly concave slope
UPPER_ROUND=2.8                             # a: rounds the apex (curvature ~ -2(c(c+1)/2-a)) without filling the upper pole
LOWER_EXP=2.4                               # lower pole: 1-r^n, full and convex, round apex, finite IMF slope
LOWER_SECTOR=1.2                            # IMF profile weight rises over the lower half (smooth contour transition)
RIM_TOP_Y=1.152                             # new under-bust edge just above the abdomen shell front
RIM_RETREAT=.41                             # removes this fraction of the old rim overhang over the abdomen front (smaller ledge)
IMF_FOLD=.0047                              # under-bust wall ring pulled back below the IMF ...
ABDOMEN_PLATEAU=.08                         # ... over the abdomen's flat front (|x| < this)
ABDOMEN_CLEARANCE=.0008                     # ... but kept this far in front of the abdomen shell front
WALL_SAMPLES=4                              # wall = smoothing TPS through n-subdivision samples of the original front faces
WALL_SMOOTH=2e-6                            # TPS regulariser: removes the coarse-face creases without overshoot
OUTER_SMOOTH=2                              # neighbour smoothing passes of the closest-point runs along the outer loop
SNAP=.008                                   # outer-loop targets closer than this to a loop corner reuse it

def add_accessor(j,b,data,kind,component=5126,target=34962):
 b+=b'\0'*((-len(b))%4); offset=len(b);dtype={5126:'<f4',5125:'<u4',5123:'<u2'}[component];a=np.asarray(data,dtype=dtype);b.extend(a.tobytes());view=len(j['bufferViews']);j['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':a.nbytes,'target':target});acc={'bufferView':view,'componentType':component,'count':len(a),'type':kind}
 if kind=='VEC3':acc.update(min=a.min(0).tolist(),max=a.max(0).tolist())
 j['accessors'].append(acc);return len(j['accessors'])-1

# ---- breast shape ----
def radius(theta):
 """Periodic Catmull-Rom through RADIUS (theta in radians)."""
 keys=sorted(RADIUS);a=np.radians(keys);r=np.array([RADIUS[k] for k in keys]);n=len(a)
 t=np.mod(theta,2*np.pi);i=np.searchsorted(a,t,side='right')-1
 a0=a[i%n]+2*np.pi*(i<0);a1=a[(i+1)%n]+2*np.pi*((i+1)>=n);u=(t-a0)/(a1-a0)
 p0,p1,p2,p3=r[(i-1)%n],r[i%n],r[(i+1)%n],r[(i+2)%n]
 return .5*(2*p1+(-p0+p2)*u+(2*p0-5*p1+4*p2-p3)*u*u+(-p0+3*p1-3*p2+p3)*u**3)

def profile(rho,theta):
 """Upper/medial/lateral fade with zero slope into the chest; only the lower sector meets the wall at the IMF."""
 upper=(1-rho)**UPPER_EXP*(1+UPPER_EXP*rho+UPPER_ROUND*rho*rho)
 lower=1-rho**LOWER_EXP
 w=upper_weight(theta)
 return w*upper+(1-w)*lower

def upper_weight(theta):
 q=np.clip((np.sin(theta)+LOWER_SECTOR)/LOWER_SECTOR,0,1);return q*q*(3-2*q)


# ---- chest wall: smoothing thin-plate spline over dense samples of the original front faces ----
class Wall:
 def __init__(self,xy,z,smooth=0.):
  self.c=xy;d=np.linalg.norm(xy[:,None]-xy[None],axis=2);K=self.k(d)+smooth*np.eye(len(xy));P=np.column_stack([np.ones(len(xy)),xy]);n=len(xy)
  A=np.zeros((n+3,n+3));A[:n,:n]=K;A[:n,n:]=P;A[n:,:n]=P.T;s=np.linalg.solve(A,np.concatenate([z,np.zeros(3)]));self.w=s[:n];self.a=s[n:]
 @staticmethod
 def k(d):return np.where(d>0,d*d*np.log(np.maximum(d,1e-12)),0.)
 def __call__(self,xy):
  xy=np.atleast_2d(xy);d=np.linalg.norm(xy[:,None]-self.c[None],axis=2);return self.k(d)@self.w+self.a[0]+xy@self.a[1:]

def source_shell():
 """Original chest shell in chest-wall morph coordinates: welded ids, patch faces and the ordered right boundary."""
 source,sb=read(ROOT/'male.glb');orig=np.concatenate([arr(source,sb,m['primitives'][0]['attributes']['POSITION']).copy() for m in source['meshes']])
 bt=arr(source,sb,source['meshes'][0]['primitives'][0]['indices']).reshape(-1,3).copy();jt=arr(source,sb,source['meshes'][1]['primitives'][0]['indices']).reshape(-1,3).copy()+2858
 labels=shell_labels(orig[:2858],bt,0);chestids=np.where(labels=='chest')[0];chestface=labels[bt[:,0]]=='chest'
 wall=np.zeros((len(orig),3))
 for i in chestids:wall[i]=morph(orig[i],'chest_wall')
 wall=wall.astype(np.float32).astype(float)        # exactly the stored float32 values
 _,inv=np.unique(np.round(wall[chestids]/1e-5).astype(np.int64),axis=0,return_inverse=True);weld=np.full(len(orig),-1);weld[chestids]=inv.ravel()
 front=wall[:,2]>-.045
 patch=chestface&front[bt].all(1)
 # Ordered boundary of the patch (welded ids), right half from bottom midline round the side to top midline.
 count={}
 for f in bt[patch]:
  for a,b in ((f[0],f[1]),(f[1],f[2]),(f[2],f[0])):count.setdefault((weld[a],weld[b]),0);count[(weld[a],weld[b])]+=1
 directed={a:b for (a,b) in count if (b,a) not in count}
 rep={weld[i]:i for i in chestids[::-1]};pos=lambda g:wall[rep[g]]
 start=min((g for g in directed if abs(pos(g)[0])<1e-6),key=lambda g:pos(g)[1]);chain=[start];g=directed[start]
 while abs(pos(g)[0])>1e-6:chain.append(g);g=directed[g]
 chain.append(g)
 if pos(chain[1])[0]<0:   # walk the other way round for the right half
  back={b:a for a,b in directed.items()};chain=[start];g=back[start]
  while abs(pos(g)[0])>1e-6:chain.append(g);g=back[g]
  chain.append(g)
 # Front-most abdomen profile z(|x|) over the height the chest bottom overlaps (abdomen top row excluded).
 ab=np.where(labels=='abdomen')[0];abd=np.zeros((len(orig),3));abd[ab]=[morph(orig[i],'abdomen') for i in ab]
 abdomen=abd[bt[labels[bt[:,0]]=='abdomen']]
 return dict(orig=orig,bt=bt,jt=jt,labels=labels,chestids=chestids,chestface=chestface,wall=wall,weld=weld,patch=patch,chain=chain,rep=rep,abdomen=abdomen[abdomen[:,:,2].max(1)>0])

def front_height(T,q):
 """Front-most z of triangles T (m,3,3) above the point q=(x,y); -inf where none covers it."""
 a,b,c=T[:,0],T[:,1],T[:,2];v0=b[:,:2]-a[:,:2];v1=c[:,:2]-a[:,:2];v2=np.asarray(q)[:2]-a[:,:2]
 d=v0[:,0]*v1[:,1]-v0[:,1]*v1[:,0];ok=np.abs(d)>1e-14;d=np.where(ok,d,1)
 u=(v2[:,0]*v1[:,1]-v2[:,1]*v1[:,0])/d;v=(v0[:,0]*v2[:,1]-v0[:,1]*v2[:,0])/d;inside=ok&(u>=-1e-9)&(v>=-1e-9)&(u+v<=1+1e-9)
 z=a[:,2]+u*(b[:,2]-a[:,2])+v*(c[:,2]-a[:,2]);return float(z[inside].max()) if inside.any() else -np.inf

def build(projection=None):
 """Right-half patch geometry. Returns points (final), pre-displacement xy, polygons and bookkeeping."""
 projection=PROJECTION if projection is None else projection;lean=np.array([np.sin(LEAN),0,np.cos(LEAN)])
 S=source_shell();wall=S['wall'];rep=S['rep'];pos=lambda g:wall[rep[g]]
 chain=[pos(g) for g in S['chain']]
 bottom=[p for p in chain if p[1]<1.16];side=[p for p in chain if p[1]>=1.1517-1e-4 and p[0]>.12];top=[p for p in chain if p[1]>=1.44]
 assert len(bottom)==4 and len(side)==4 and len(top)==4 and side[0] is bottom[-1] and side[-1] is top[0],(len(bottom),len(side),len(top))
 # Wall: the original front faces above the rim, with the old rim-top row replaced by the retreated
 # under-bust edge, sampled densely (both halves) and fitted by a smoothing TPS (no overshoot between rows).
 rimrow=lambda p:abs(p[1]-1.1517)<.002 and abs(p[0])<.1
 abz=lambda x,y:front_height(S['abdomen'],[x,y])
 near=lambda x:max(abz(x+d,y) for d in np.linspace(-.03,.03,13) for y in (1.115,1.15,1.2))+ABDOMEN_CLEARANCE
 design=lambda p:np.array([p[0],RIM_TOP_Y,max(p[2]-RIM_RETREAT*max(0.,p[2]-abz(p[0],1.15)),near(p[0]))]) if rimrow(p) else p
 samples={}
 for f in S['bt'][S['patch']]:
  c=np.array([design(wall[v]) for v in f])
  if c[:,1].min()<1.14:continue
  n=WALL_SAMPLES
  for a in range(n+1):
   for b_ in range(n+1-a):
    p=np.array([n-a-b_,a,b_])@c/n;samples[tuple(np.round(p[:2],6))]=p[2]
 ctrl=np.array([[x,y,z] for (x,y),z in sorted(samples.items())])
 W=Wall(ctrl[:,:2],ctrl[:,2],WALL_SMOOTH);wz=lambda q:float(W(np.asarray(q,float))[0])
 # Abdomen shell front (behind the chest bottom): the under-bust may not be pulled back through it.
 floor=lambda x,y:abz(x,y)+ABDOMEN_CLEARANCE
 pts=[];xy=[];kind=[]
 def add(p,q,k):pts.append(np.asarray(p,float));xy.append(np.asarray(q,float)[:2]);kind.append(k);return len(pts)-1
 def polar(q):
  d=np.asarray(q,float)-CENTER;t=float(np.arctan2(d[1],d[0]));return float(np.linalg.norm(d)/radius(t)),t
 def surf(q,amount=None):
  rho,t=polar(q);a=projection if amount is None else amount
  return np.array([q[0],q[1],wz(q)])+(a*profile(rho,t)*lean if rho<1 else 0)
 # Rings are centred on the most projecting point along the breast axis (the apex faces the axis direction,
 # not the backward-leaning upper-chest wall) and follow the axial height, normalised per ray between the apex
 # and the footprint edge: contour-like near the apex, conforming to the teardrop footprint at the IMF.
 axial=lambda q:float(surf(q,PROJECTION)@lean)   # layout always from the design surface (control mesh = same layout)
 g=[CENTER+[dx,dy] for dx in np.linspace(-.04,.04,41) for dy in np.linspace(-.06,.03,46)];pole=max(g,key=axial)
 g=[pole+[dx,dy] for dx in np.linspace(-.002,.002,9) for dy in np.linspace(-.002,.002,9)];pole=max(g,key=axial)
 corner=np.array([ABDOMEN_PLATEAU-.006,RIM_TOP_Y+.03]);phase=(np.arctan2(*(corner-pole)[::-1])%(2*np.pi))/(2*np.pi)*SEGMENTS%1
 theta=(np.arange(SEGMENTS)+phase)*2*np.pi/SEGMENTS;ray=lambda t:np.array([np.cos(t),np.sin(t)])
 def bisect(f,lo,hi):
  for _ in range(50):
   m=(lo+hi)/2;lo,hi=(m,hi) if f(m) else (lo,m)
  return hi
 apex=add(surf(pole),pole,'apex');h0=axial(pole);rings=[[] for _ in RING_LEVELS]
 for t in theta:
  u=ray(t);edge=bisect(lambda r:polar(pole+r*u)[0]<1,0.,.25);he=axial(pole+edge*u)
  for k,lv in enumerate(RING_LEVELS):
   r=edge if lv<=0 else bisect(lambda r:axial(pole+r*u)>he+lv*(h0-he),0.,edge);q=pole+r*u
   rings[k].append(add(surf(q),q,'ring'))
 polys=[(apex,rings[0][j],rings[0][(j+1)%SEGMENTS]) for j in range(SEGMENTS)]
 for a,b in zip(rings,rings[1:]):polys+=[(a[j],b[j],b[(j+1)%SEGMENTS],a[(j+1)%SEGMENTS]) for j in range(SEGMENTS)]
 # Outer loop L0, counter-clockwise from the front: under-bust edge, side, upper chest, sternum.
 # Segments: (start, end, kind); kind 'edge' = original shell edge (new points on it fan the neighbour face).
 corner_mid=np.array([0,RIM_TOP_Y,wz([0,RIM_TOP_Y])])
 ids_fixed={}
 def fixed(p,k='boundary'):
  key=tuple(np.round(p,9))
  if key not in ids_fixed:ids_fixed[key]=add(p,p,k)
  return ids_fixed[key]
 loop=[(corner_mid,'rimtop')]+[(p,'boundary') for p in side]+[(p,'boundary') for p in top[1:]]
 segs=[]
 for e in range(len(loop)):
  (a,ka),(b,kb)=loop[e],loop[(e+1)%len(loop)]
  segs.append((a,b,'rimtop' if e==0 else 'midline' if e==len(loop)-1 else 'edge'))
 L0=[[fixed(a,'rimtop' if e==0 else 'boundary')] for e,(a,b,kind_) in enumerate(segs)]
 # under-bust edge points: above the original bottom-edge vertices and the old rim-top row (keeps the plate's
 # front corner lateral of the abdomen's front corner, and the tuck strip near-planar)
 rim_x=sorted({round(float(p[0]),6) for p in bottom[1:-1]}|{round(float(wall[i,0]),6) for i in rep.values() if rimrow(wall[i]) and wall[i,0]>1e-6})
 L0[0]+=[add([x,RIM_TOP_Y,wz([x,RIM_TOP_Y])],[x,RIM_TOP_Y],'rimtop') for x in rim_x]
 # Each footprint vertex runs straight out to its closest point on the outer loop: edges meet the sternum,
 # upper chest, side and under-bust edge at right angles, like a torso grid around the breast.
 def closest(q):
  best=None
  for e,(a,b,kind_) in enumerate(segs):
   ab=b[:2]-a[:2];u=float(np.clip((q-a[:2])@ab/(ab@ab),0,1));d=np.linalg.norm(a[:2]+u*ab-q)
   if best is None or d<best[0]:best=(d,e,u)
  return best[1],best[2]
 # Arc-length along the loop; closest-point positions are smoothed with their neighbours so the runs fan out
 # gradually round the loop's corners (no jump between adjacent runs).
 seglen=[np.linalg.norm(b[:2]-a[:2]) for a,b,_ in segs];cum=np.concatenate([[0],np.cumsum(seglen)]);total=cum[-1]
 s0=np.array([cum[e]+u*seglen[e] for e,u in map(closest,[xy[v] for v in rings[-1]])])
 s0=s0[0]+np.concatenate([[0],np.cumsum((np.diff(s0)+total/2)%total-total/2)])   # unwrap (monotone along the ring)
 for _ in range(OUTER_SMOOTH):s0=np.convolve(np.concatenate([[s0[-1]-total],s0,[s0[0]+total]]),[.25,.5,.25],'valid')
 hits={};targets=[]
 for j,t in enumerate(theta):
  sj=s0[j]%total;e=min(int(np.searchsorted(cum,sj,side='right'))-1,len(segs)-1);u=(sj-cum[e])/seglen[e]
  a,b,kind_=segs[e];p=a+(b-a)*u;targets.append(p[:2].copy())
  if kind_!='edge':p[2]=wz(p[:2])
  if kind_=='rimtop':hits[j]=min(L0[e]+[fixed(b)],key=lambda i:np.linalg.norm(xy[i]-p[:2]));continue
  if np.linalg.norm(p[:2]-a[:2])<SNAP:hits[j]=L0[e][0]
  elif np.linalg.norm(p[:2]-b[:2])<SNAP:hits[j]=L0[(e+1)%len(segs)][0]
  else:hits[j]=add(p,p,kind_ if kind_!='edge' else 'lateral');L0[e].append(hits[j])
 # order points along each segment, record inserted points on original edges (neighbour faces get fanned)
 inserted={};ring_order=[]
 for e,(a,b,kind_) in enumerate(segs):
  inner=sorted(L0[e][1:],key=lambda i:np.linalg.norm(pts[i][:2]-a[:2]))
  if kind_=='edge':inserted[(tuple(a),tuple(b))]=inner
  ring_order+=[L0[e][0]]+inner
 # plain wall ring halfway to the outer loop
 foot=rings[-1];last=[]
 for j in range(SEGMENTS):
  q=xy[foot[j]]+(targets[j]-xy[foot[j]])*WALL_RING
  last.append(add([q[0],q[1],wz(q)-IMF_FOLD*(1-upper_weight(theta[j]))],q,'wallring'))
 polys+=[(foot[j],last[j],last[(j+1)%SEGMENTS],foot[(j+1)%SEGMENTS]) for j in range(SEGMENTS)]
 where={v:i for i,v in enumerate(ring_order)}
 for j in range(SEGMENTS):
  i0,i1=where[hits[j]],where[hits[(j+1)%SEGMENTS]]
  chainq=[ring_order[(i0+k)%len(ring_order)] for k in range((i1-i0)%len(ring_order)+1)]
  r0,r1=last[j],last[(j+1)%SEGMENTS]
  if len(chainq)==2:polys.append((r0,chainq[0],chainq[1],r1));continue
  if len(chainq)==1:polys.append((r0,chainq[0],r1));continue
  mid=(len(chainq)-1)//2
  polys+=[(r0,chainq[k],chainq[k+1]) for k in range(mid)]+[(r0,chainq[mid],r1)]+[(r1,chainq[k],chainq[k+1]) for k in range(mid,len(chainq)-1)]
 # Rim strip: zipper (by x) between the original bottom edge and the new under-bust edge; tucks back under.
 n_front=len(polys);B=[fixed(p) for p in bottom];T=[L0[0][0]]+sorted(L0[0][1:],key=lambda i:pts[i][0])+[fixed(side[0])]
 i=k=0
 while i<len(B)-1 or k<len(T)-1:
  if i<len(B)-1 and (k==len(T)-1 or pts[B[i+1]][0]<=pts[T[k+1]][0]):tri=(B[i],B[i+1],T[k]);i+=1
  else:tri=(B[i],T[k+1],T[k]);k+=1
  if len(set(tri))==3:polys.append(tri)
 # The abdomen shell's top hides inside the chest bottom: no chest face may dip behind it (sampled inside every
 # face, since faces span the abdomen's convex front corner). Free vertices are lifted (least-norm), boundary fixed.
 P=np.array(pts);free=np.array([k not in ('boundary','lateral') for k in kind]);bary=[np.array([a,b_,8-a-b_])/8 for a in range(9) for b_ in range(9-a)]
 for it in range(8):
  lift=np.zeros(len(P))
  for t in [t for poly in polys[:n_front] for t in triangulate(poly,P)]:   # the rim strip tucks under by design
   c=P[list(t)]
   if c[:,1].min()>1.25 or c[:,1].max()<1.10:continue
   for w in bary:
    q=w@c
    if abs(q[0])>ABDOMEN_PLATEAU:continue   # beyond the abdomen's front plateau the source shells already overlap
    d=floor(q[0],q[1])-q[2]
    if d>1e-5:
     ww=w*free[list(t)]
     if ww.sum()>0:
      for v,wi in zip(t,np.minimum(ww*d/(ww@ww),d)):lift[v]=max(lift[v],wi)
  if not lift.any():break
  P[:,2]+=lift
 return dict(S=S,points=P,xy=np.array(xy),kind=kind,polys=polys,apex=apex,rings=rings,inserted=inserted,wall=W)

def triangulate(poly,P):
 if len(poly)==3:return [poly]
 a,b,c,d=poly
 # Convex fold: split along the diagonal whose midpoint lies further out along the quad normal.
 n=np.cross(P[c]-P[a],P[d]-P[b]);m1=(P[a]+P[c])/2;m2=(P[b]+P[d])/2
 return [(a,b,c),(a,c,d)] if (m1-m2)@n>=0 else [(a,b,d),(b,c,d)]

def breast_shape(G):
 """Generator-side shape diagnostics for the right breast (left is its mirror), against the same mesh with zero
 breast displacement. 'apex' is the apex pole (nipple position); the most forward vertex is reported separately."""
 import sys;sys.path.insert(0,str(ROOT.parent/'tests'))
 from bust_metrics import heightfield
 G0=build(0.);P,P1=G['points'],G0['points'];tris=[t for poly in G['polys'] for t in triangulate(poly,P)]
 vol=sum(np.linalg.det(P[list(t)])-np.linalg.det(P1[list(t)]) for t in tris)/6
 apex=P[G['apex']];breast=[G['apex']]+[v for r in G['rings'] for v in r];front=P[breast[int(np.argmax(P[breast,2]))]]
 xs=np.arange(0,.2,.002);ys=np.arange(1.10,1.50,.002);T=np.array([P[list(t)] for t in tris]);T0=np.array([P1[list(t)] for t in tris])
 E=np.nan_to_num(heightfield(T,xs,ys)-heightfield(T0,xs,ys));rows=np.where((E>.003).any(1))[0];y_top,y_bot=ys[rows.max()],ys[rows.min()]
 fan=[np.cross(P[b]-P[a],P[c]-P[a]) for a,b,c in G['polys'][:SEGMENTS]];n=np.sum(fan,0);n/=np.linalg.norm(n)
 axis=apex-P[G['rings'][-1]].mean(0);W=G['wall'];h=1e-4;gx=(W(CENTER+[h,0])[0]-W(CENTER-[h,0])[0])/(2*h)
 return {'source':'refine_chest.py design surface vs. the same mesh with zero breast displacement (not the QA method)',
  'per_breast_volume_cm3':float(vol*1e6),'apex_m':apex.tolist(),'most_forward_vertex_m':front.tolist(),
  'apex_projection_from_wall_m':float(apex[2]-W(apex[:2])[0]),'max_dz_over_wall_m':float(E.max()),'design_displacement_m':PROJECTION,
  'excess_over_3mm_y_bottom_top_m':[float(y_bot),float(y_top)],'apex_relative_height':float((apex[1]-y_bot)/(y_top-y_bot)),
  'upper_volume_fraction':float(E[ys>apex[1]].sum()/E.sum()),'imf_y_m':float(P[G['rings'][-1],1].min()),
  'outward_deg':{'apex_normal_yaw':float(np.degrees(np.arctan2(n[0],n[2]))),'base_to_apex_axis_yaw':float(np.degrees(np.arctan2(axis[0],axis[2]))),
   'wall_normal_yaw_at_centre':float(np.degrees(np.arctan2(-gx,1))),'design_lean':float(np.degrees(LEAN))},
  'apex_normal_pitch_deg':float(np.degrees(np.arctan2(n[1],n[2])))}

def main(projection=None,write=True,source=None):
 """source: base-morph female GLB (default: model/female.glb as written by make_female.py)."""
 j,b=read(source or ROOT/'female.glb')
 attrs={name:np.concatenate([arr(j,b,m['primitives'][0]['attributes'][name]).copy() for m in j['meshes']]) for name in ['POSITION','NORMAL','TEXCOORD_0','JOINTS_0','WEIGHTS_0']}
 G=build(projection);S=G['S'];bt,jt,wall,patch=S['bt'],S['jt'],S['wall'],S['patch'];chestids=S['chestids']
 base=attrs['POSITION'].astype(float).copy();base[chestids]=wall[chestids]
 positions=list(base);normals=list(attrs['NORMAL'].astype(float));uv=list(attrs['TEXCOORD_0']);joints=list(attrs['JOINTS_0']);weights=list(attrs['WEIGHTS_0']);mapping=[]
 def append(p,n,face,w):
  idx=len(positions);positions.append(p);normals.append(n);w=np.clip(w,0,None);w=w/w.sum();uv.append(w@attrs['TEXCOORD_0'][face])
  blend={}
  for parent,coef in zip(face,w):
   for jj,ww in zip(attrs['JOINTS_0'][parent],attrs['WEIGHTS_0'][parent]):blend[int(jj)]=blend.get(int(jj),0)+float(coef*ww)
  top=sorted(blend.items(),key=lambda x:(-x[1],x[0]))[:4];top+=[(0,0.)]*(4-len(top));jw=np.array([v for _,v in top]);jw/=jw.sum()
  joints.append([q for q,_ in top]);weights.append(jw);mapping.append({'index':idx,'source_triangle':[int(f) for f in face],'barycentric':w.tolist()});return idx
 patch_ids=np.where(patch)[0]
 def locate(q,sign):
  """Original patch triangle (male id) containing xy q on the given side, with barycentrics."""
  best=None
  for t in patch_ids:
   f=bt[t];c=wall[f][:,:2]
   if np.sign(c[:,0].mean())!=sign:continue
   T=np.column_stack([c[1]-c[0],c[2]-c[0]])
   if abs(np.linalg.det(T))<1e-12:continue
   u,v=np.linalg.solve(T,q-c[0]);w=np.array([1-u-v,u,v]);score=w.min()
   if best is None or score>best[0]:best=(score,t,w)
  return best[1],best[2]
 P0=G['points'];XY=G['xy'];polys=G['polys']
 newtri=[];face_source=[];chest_new=[]
 for sign in [1,-1]:
  P=P0*[sign,1,1];P[np.abs(P[:,0])<1e-12,0]=0.;Q=XY*[sign,1]
  P=P.astype(np.float32).astype(float)
  for poly in polys:
   tris=triangulate(poly,P)
   if sign<0:tris=[(a,c,bb) for a,bb,c in tris]
   n=sum(np.cross(P[t[1]]-P[t[0]],P[t[2]]-P[t[0]]) for t in tris);n/=np.linalg.norm(n)
   src,_=locate(Q[list(poly)].mean(0),sign);local={}
   for v in poly:
    t,w=locate(Q[v],sign);local[v]=append(P[v],n,bt[t],w)
   for t in tris:newtri.append([local[v] for v in t]);face_source.append(int(src));chest_new.append(newtri[-1])
 # Side faces sharing a subdivided boundary edge are fanned through the new (collinear) points: same plane, no T-junction.
 fan_vertices=[]
 for fid,f in enumerate(bt):
  if patch[fid]:continue
  done=False
  if S['chestface'][fid]:
   for sign in [1,-1]:
    for (a,bb),new in G['inserted'].items():
     if not new:continue
     pa=np.array(a)*[sign,1,1];pb=np.array(bb)*[sign,1,1];corner=[np.allclose(wall[v],pa,atol=1e-7) for v in f],[np.allclose(wall[v],pb,atol=1e-7) for v in f]
     if any(corner[0]) and any(corner[1]):
      ia=corner[0].index(True);ib=corner[1].index(True);ic=3-ia-ib
      chain=[f[ia]]+[None]*len(new)+[f[ib]]
      pts=[P0[k]*[sign,1,1] for k in new]
      for s,p in enumerate(pts):
       w=np.zeros(3);t=(s+1)/(len(new)+1);w[ia]=1-t;w[ib]=t;chain[s+1]=append(p.astype(np.float32).astype(float),np.zeros(3),f,w);fan_vertices.append((chain[s+1],fid))
      # keep original winding: (ia,ib,ic) order in f is cyclic
      forward=(ib-ia)%3==1
      for s in range(len(chain)-1):
       tri=[chain[s],chain[s+1],f[ic]] if forward else [chain[s+1],chain[s],f[ic]]
       newtri.append(tri);face_source.append(fid);chest_new.append(tri)
      done=True
  if not done:
   newtri.append(f.tolist());face_source.append(fid)
   if S['chestface'][fid]:chest_new.append(f.tolist())
 P=np.array(positions);chest_new=np.array(chest_new)
 # Original chest vertices no longer referenced (old front interior) are placed on the new surface.
 used=np.zeros(len(P),bool);used[np.array(newtri).ravel()]=True;used[jt.ravel()]=True
 Tn=np.array(newtri);front_tris=Tn[np.isin(Tn,np.arange(4106,len(P))).all(1)]
 for i in chestids[~used[chestids]]:
  q=P[i,:2];best=None
  for t in front_tris:
   c=P[t];T=np.column_stack([c[1,:2]-c[0,:2],c[2,:2]-c[0,:2]])
   if abs(np.linalg.det(T))<1e-14:continue
   u,v=np.linalg.solve(T,q-c[0,:2])
   if min(u,v,1-u-v)>-1e-9:
    z=c[0,2]+u*(c[1,2]-c[0,2])+v*(c[2,2]-c[0,2])
    if best is None or z>best[0]:best=(z,np.cross(c[1]-c[0],c[2]-c[0]))
  P[i,2]=best[0];normals[i]=best[1]/np.linalg.norm(best[1])
 ns=np.array(normals,float)
 # Kept/fanned original chest faces: flat normals recomputed per source smoothing group on the final positions.
 for v,fid in fan_vertices:f=bt[fid];n=np.cross(P[f[1]]-P[f[0]],P[f[2]]-P[f[0]]);ns[v]=n/np.linalg.norm(n)
 kept=np.array([t for t in newtri if min(t)<2858 and S['labels'][min(t)]=='chest'])
 if len(kept):
  grp={};fn=np.cross(P[kept[:,1]]-P[kept[:,0]],P[kept[:,2]]-P[kept[:,0]])
  key=lambda v:(tuple(np.round(P[v]/1e-5).astype(int)),tuple(np.round(attrs['NORMAL'][v]/1e-3).astype(int)))
  for t,n in zip(kept,fn):
   for v in t:
    if v<4106:grp.setdefault(key(v),np.zeros(3));grp[key(v)]+=n
  for v in np.unique(kept):
   if v<4106:n=grp[key(v)];ns[v]=n/np.linalg.norm(n)
 out={'G':G,'P':P,'normals':ns,'triangles':newtri,'chest_triangles':chest_new,'face_source':face_source,'mapping':mapping,'jt':jt}
 if not write:return out
 j['accessors']=[];j['bufferViews']=[];b=bytearray();at={}
 for name,data,kind,ct in [('POSITION',P,'VEC3',5126),('NORMAL',ns,'VEC3',5126),('TEXCOORD_0',uv,'VEC2',5126),('JOINTS_0',joints,'VEC4',5123),('WEIGHTS_0',weights,'VEC4',5126)]:at[name]=add_accessor(j,b,data,kind,ct)
 prims=[]
 for tris,mat in [(newtri,0),(jt,1)]:
  ia=add_accessor(j,b,np.array(tris).reshape(-1,1),'SCALAR',5125,34963);prims.append({'attributes':at.copy(),'indices':ia,'mode':4,'material':mat})
 j['meshes']=[{'name':'Female_refined','primitives':prims}];j['nodes']=[{'name':'Female_refined','mesh':0}];j['scenes']=[{'nodes':[0]}];j['scene']=0;j['buffers']=[{'byteLength':len(b)}];j['asset']['generator']='make_female.py + refine_chest.py';j['asset']['extras']['modification']='Append-only canonical vertex pool; low-poly faceted chest front remeshed with breast edge flow; original global indices 0..4105 retained.'
 raw=json.dumps(j,separators=(',',':')).encode();raw+=b' '*((-len(raw))%4);b+=b'\0'*((-len(b))%4);out_bytes=struct.pack('<III',0x46546c67,2,28+len(raw)+len(b))+struct.pack('<II',len(raw),0x4e4f534a)+raw+struct.pack('<II',len(b),0x004e4942)+b;(ROOT/'female.glb').write_bytes(out_bytes)
 shape=breast_shape(G);(ROOT/'validation'/'breast_metrics.json').write_text(json.dumps(shape,indent=2));print(shape)
 report={'method':'faceted chest-front remesh: apex pole, displacement-contour rings, wall ring, closest-point runs to the shell boundary, rim strip; side/top faces fanned at subdivided edges','segments':SEGMENTS,'ring_levels':RING_LEVELS,'wall_ring':WALL_RING,'original_vertices':4106,'vertices':len(P),'triangles':len(newtri)+len(jt),'original_triangles':2088,'append_range':[4106,len(P)-1],'refined_chest_triangles':len(chest_new),'unreferenced_original_chest_vertices':[int(i) for i in chestids[~used[chestids]]],'mapping':mapping,'triangle_source':face_source+list(range(1456,2088))};(ROOT/'validation'/'chest_vertex_mapping.json').write_text(json.dumps(report,indent=2));print({k:v for k,v in report.items() if k not in ['mapping','triangle_source','unreferenced_original_chest_vertices']})
 return out
if __name__=='__main__':main()
