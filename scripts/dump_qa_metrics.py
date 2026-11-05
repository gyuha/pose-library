"""female QA 지표를 JSON 으로 덤프한다 -> tests/reports/female_qa_metrics.json (보고서의 수치 출처)."""
import collections
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from qa_metrics import (chest_groove, edge_strain, face_normal_rotation, group_of, intersection_sets, label_of_welded,
                        members, mirror_map, asymmetry, models, pair_key, parts, proportions, seam_drift, seam_pairs,
                        torso_measures, tri_dev_from_normals, umbrella_delta, vdesc)


def main():
    m, f = models(); L = parts(); lab = label_of_welded()
    out = {}
    # 교차
    a, b = intersection_sets()
    out["intersections"] = {"male": len(a), "female": len(b), "new": len(b - a), "resolved": len(a - b),
                            "new_by_pair": collections.Counter(pair_key(p) for p in b - a).most_common()}
    # 변형 매끄러움
    E, ratio, M, F = edge_strain()
    bad = np.where((ratio < 0.65) | (ratio > 1.5))[0]
    out["edge_strain"] = {"min": float(ratio.min()), "max": float(ratio.max()), "p1": float(np.percentile(ratio, 1)), "p99": float(np.percentile(ratio, 99)),
                          "n_outside_0.65_1.50": int(len(bad)), "by_part": collections.Counter(group_of(l) for l in lab[E[bad, 0]]).most_common()}
    dn, _, _ = umbrella_delta()
    o = np.argsort(-np.abs(dn))[:14]
    out["umbrella_top"] = [{"delta_mm": round(float(dn[i] * 1000), 1), "part": lab[i], "vertex_indices": [int(x) for x in members(i)], "male": [round(float(x), 3) for x in M[i]], "female": [round(float(x), 3) for x in F[i]]} for i in o]
    out["umbrella_over_15mm_by_part"] = collections.Counter(group_of(l) for l in lab[np.abs(dn) > 0.015]).most_common()
    g, y, k = chest_groove(f); gm, _, _ = chest_groove(m)
    out["chest_groove"] = {"female_mm": round(g * 1000, 1), "male_mm": round(gm * 1000, 1), "male_row_y": y, "bump_vertex": k}
    dm, df = tri_dev_from_normals(m), tri_dev_from_normals(f)
    bad = np.where((dm < 5) & (df > 15))[0]
    out["normal_mismatch"] = {"n_triangles": int(len(bad)), "by_part": collections.Counter(group_of(L[f.tri[t, 0]]) for t in bad).most_common(), "max_deg": float(df[bad].max())}
    rot = face_normal_rotation(m, f); bad = np.where(rot > 30)[0]
    out["face_rotation_over_30"] = {"n": int(len(bad)), "max_deg": float(rot.max()), "by_part": collections.Counter(group_of(L[f.tri[t, 0]]) for t in bad).most_common()}
    # 이음매
    out["seams"] = [r for r in (seam_drift(J, B) for J, B in seam_pairs()) if r]
    # 비율
    out["proportions_female"] = proportions(f); out["proportions_male"] = proportions(m)
    tf, tm = torso_measures(f), torso_measures(m)
    out["torso_female"] = tf; out["torso_male"] = tm
    # 대칭
    mm, md = mirror_map(m)
    out["symmetry_mm"] = {"male_max": float(asymmetry(m, mm).max() * 1000), "female_max": float(asymmetry(f, mm).max() * 1000)}
    p = ROOT / "tests" / "reports" / "female_qa_metrics.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o), ensure_ascii=False))
    print("wrote", p)


if __name__ == "__main__":
    main()
