"""Read-only QA metrics integration; writes model/validation only."""
import sys,json,collections,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'tests'))
from qa_metrics import models,proportions,torso_measures,intersection_sets,pair_key,chest_groove
m,f=models();a,b=intersection_sets()
r={'proportions':proportions(f),'torso':torso_measures(f),'new_intersections':len(b-a),'resolved_intersections':len(a-b),'intersection_breakdown':dict(collections.Counter(pair_key(p) for p in b-a)),'chest_groove_m':chest_groove(f)[0]}
(ROOT/'validation'/'revised_qa_metrics.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
