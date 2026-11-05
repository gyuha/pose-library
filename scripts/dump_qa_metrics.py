"""female QA 지표를 JSON 으로 덤프한다 -> tests/reports/female_qa_metrics.json (보고서의 수치 출처)."""
import collections
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
import bust_eval as be
from qa_metrics import (chest_partner_sets, chest_topology_changed, correspondence, full_female, hip_breadth, preserved_triangles,
                        abdomen_poke, shoulder_breadth, chest_groove, edge_strain, face_normal_rotation, group_of, intersection_sets, label_of_welded,
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
    # [v2] 토폴로지 / 비율 / 가슴
    f = full_female(); f2m, _ = correspondence()
    miss, ex, extra = preserved_triangles()
    out["topology"] = {"male_vertices": 4106, "female_vertices": int(f.n_verts), "added_vertices": int((f2m < 0).sum()),
                       "male_triangles": 2088, "female_triangles": int(len(f.tri)), "chest_replaced": bool(chest_topology_changed()),
                       "non_chest_triangles_missing": miss}
    fm, mm_ = models()[1], models()[0]
    out["v2_proportions"] = {w: {"shoulder_m": shoulder_breadth(x), "hip_breadth_m": hip_breadth(x)[0], "hip_breadth_zone_0.44_0.56": hip_breadth(x)[0],
                                 "hip_breadth_trochanter_0.50_0.56": hip_breadth(x, (0.50, 0.56))[0], "H": proportions(x)["H"],
                                 "shoulder_over_hip": shoulder_breadth(x) / hip_breadth(x)[0], "whr": torso_measures(x)["whr"]}
                             for w, x in (("male", mm_), ("female", fm))}
    bust = {}
    for w in ("male", "female"):
        r = be.evaluate(w)
        a = {k: v for k, v in r["analysis"].items() if not k.startswith("_") and k != "plane_coef"}
        bust[w] = {**{k: v for k, v in r.items() if k != "analysis"}, **a}
    bust["partner_new_faces"] = {c: len(s[1] - s[0]) for c, s in chest_partner_sets().items()}
    pk, mk, vi = abdomen_poke(); bust["abdomen_poke_mm"] = {"female": pk * 1000, "male": mk * 1000, "vertex": vi}
    bust["lower_rim_sharp_edges"] = {w: list(be.lower_rim_sharp_edges(w)) for w in ("male", "female")}
    bust["front_asymmetry_mm"] = {w: be.front_asymmetry(w)[0] * 1000 for w in ("male", "female")}
    out["bust"] = bust
    p = ROOT / "tests" / "reports" / "female_qa_metrics.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o), ensure_ascii=False))
    print("wrote", p)


if __name__ == "__main__":
    main()
