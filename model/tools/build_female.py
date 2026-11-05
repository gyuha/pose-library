"""Reproducible complete female GLB build (NumPy; no Blender/GUI/network)."""
import json,shutil
from make_female import main as base,ROOT,read,arr
from refine_chest import main as refine
from measure_refined import main as measure

def main():
 base()
 shutil.copyfile(ROOT/'female.glb',ROOT/'validation'/'female_before_breast_refinement.glb')
 refine()
 measure()
 j,b=read(ROOT/'female.glb');p=j['meshes'][0]['primitives'][0];P=arr(j,b,p['attributes']['POSITION']);metrics=json.loads((ROOT/'validation'/'breast_metrics.json').read_text());report={'vertices':len(P),'triangles':sum(j['accessors'][p['indices']]['count']//3 for m in j['meshes'] for p in m['primitives']),'original_vertex_range':[0,4105],'appended_vertex_range':[4106,len(P)-1],'bbox':[P.min(0).tolist(),P.max(0).tolist()],'height_m':float(P[:,1].max()-P[:,1].min()),'breast_metrics':metrics};(ROOT/'validation'/'validation.json').write_text(json.dumps(report,indent=2))
if __name__=='__main__':main()
