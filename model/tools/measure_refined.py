"""Canonical-pool checks and chest/underbust hull girths, without old QA Model assumptions."""
import sys,json
import numpy as np
from make_female import ROOT,read,arr
from deformation import shell_labels
sys.path.insert(0,str(ROOT.parent/'tests'))
from qa_metrics import section_points,hull_area_perimeter

def load():
 j,b=read(ROOT/'female.glb');p=j['meshes'][0]['primitives'][0];P=arr(j,b,p['attributes']['POSITION']).astype(float);T=[arr(j,b,p['indices']).reshape(-1,3).copy() for p in j['meshes'][0]['primitives']];return j,b,P,T

def main():
 j,b,P,T=load();s,sb=read(ROOT/'male.glb');parts=[];faces=[];base=0
 for pid,m in enumerate(s['meshes']):
  p=m['primitives'][0];v=arr(s,sb,p['attributes']['POSITION']);f=arr(s,sb,p['indices']).reshape(-1,3);parts.extend(shell_labels(v,f,pid));faces.extend(f+base);base+=len(v)
 parts=np.array(parts+['chest']*(len(P)-4106));allT=np.concatenate(T);sel=np.isin(parts[allT[:,0]],['chest','abdomen','pelvis','waist_band','hip_joint']);torso=P[allT[sel]]
 def girth(y):
  pts=section_points(torso,np.array([0,1,0]),y);return hull_area_perimeter(pts[:,[0,2]])[1]
 ys=np.linspace(1.25,1.37,121);g=np.array([girth(y) for y in ys]);i=g.argmax();under_y=1.20;under=girth(under_y)
 r=json.loads((ROOT/'validation'/'breast_metrics.json').read_text());r.update(bust_girth_m=float(g[i]),bust_measure_y_m=float(ys[i]),underbust_girth_m=float(under),underbust_measure_y_m=under_y,bust_minus_underbust_m=float(g[i]-under),vertices=len(P),triangles=len(allT));print(json.dumps(r,indent=2));(ROOT/'validation'/'breast_metrics.json').write_text(json.dumps(r,indent=2))
if __name__=='__main__':main()
