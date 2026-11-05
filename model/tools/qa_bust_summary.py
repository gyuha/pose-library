"""Read QA v2 measurements without modifying QA files."""
import sys,json
from make_female import ROOT
sys.path.insert(0,str(ROOT.parent/'tests'))
from bust_eval import evaluate
from qa_metrics import chest_partner_sets,abdomen_poke,proportions,torso_measures,models,hip_breadth,shoulder_breadth
r=evaluate('female');[r['analysis'].pop(k,None) for k in list(r['analysis']) if k.startswith('_')];r['cup_difference_cm']=(r['bust_girth']-r['underbust_girth'])*100
r['new_chest_partner_faces']={k:len(f-m) for k,(m,f) in chest_partner_sets().items()}
poke,mpoke,vi=abdomen_poke();r['abdomen_poke_m']=float(poke)
r['shoulder_hip_ratio']=shoulder_breadth(models()[1])/hip_breadth(models()[1])[0];r['whr']=torso_measures(models()[1])['whr']
(ROOT/'validation'/'qa_bust_v2.json').write_text(json.dumps(r,indent=2,default=lambda v:v.tolist() if hasattr(v,"tolist") else str(v)));print(json.dumps(r,indent=2,default=lambda v:v.tolist() if hasattr(v,"tolist") else str(v)))
