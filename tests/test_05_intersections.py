"""(e) 메시 교차: male 대비 새로 생긴 엄밀 삼각형 교차쌍을 부위쌍별로 집계.
male 은 설계상 Joints-Body 겹침과 손가락 자체 교차가 있으므로 '새로 생긴 것'만 본다.
기준: Body 쉘끼리 새로 생긴 교차 4쌍 이하(눈에 보이는 표면 관통), 전체 신규 10쌍 이하."""
import collections

from qa_metrics import chest_topology_changed, intersection_sets, pair_key

# 가슴 쉘이 세분화되면 가슴이 낀 교차쌍의 '개수'는 해상도에 따라 부풀기 때문에 비교할 수 없다.
# 가슴이 낀 쌍은 test_08_bust.py (상대 쪽 삼각형 집합 비교, 배 쉘 돌출 높이)가 본다.
CHEST_REPLACED = chest_topology_changed()


def _new():
    a, b = intersection_sets()
    keep = (lambda p: "body:chest" not in pair_key(p)) if CHEST_REPLACED else (lambda p: True)
    na, nb = {p for p in a if keep(p)}, {p for p in b if keep(p)}
    return collections.Counter(pair_key(p) for p in nb - na), len(nb - na), len(na - nb), len(na), len(nb)


def test_total_new_intersections_small():
    c, n_new, n_res, n_m, n_f = _new()
    assert n_new <= 10, f"신규 {n_new} (해소 {n_res}, male {n_m} -> female {n_f}); " + ", ".join(f"{k}:{v}" for k, v in c.most_common(8))


def test_no_new_shell_to_shell_penetration():
    c, *_ = _new()
    shell = {k: v for k, v in c.items() if k.count("joint:") == 0}
    assert sum(shell.values()) <= 4, "Body 쉘끼리 신규 교차: " + ", ".join(f"{k}:{v}" for k, v in sorted(shell.items(), key=lambda x: -x[1]))
