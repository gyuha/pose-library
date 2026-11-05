"""(b) male 과 female 의 토폴로지 동일성: 정점 수, 인덱스, 정점 순서(UV/JOINTS/WEIGHTS 동일), 시임 정점 일치."""
import numpy as np

from glb_io import FEMALE, MALE, Model, read_glb, accessor
from qa_metrics import models, parts, vdesc, weld


def test_vertex_and_triangle_counts_equal():
    m, f = models()
    assert m.n_verts == f.n_verts == 4106
    assert len(m.tri) == len(f.tri) == 2088
    assert [(a, b) for _, a, b in m.prims] == [(a, b) for _, a, b in f.prims]  # 메시 이름은 바뀌므로 정점 범위만 비교


def test_index_buffers_identical():
    m, f = models()
    assert np.array_equal(m.tri, f.tri)


def test_vertex_order_preserved_via_attributes():
    """UV/JOINTS/WEIGHTS 가 인덱스별로 동일 = 정점 순서가 그대로이므로 가중치 전이가 가능하다."""
    gm, bm = read_glb(MALE); gf, bf = read_glb(FEMALE)
    for pm, pf in zip(gm["meshes"], gf["meshes"]):
        for attr in ("TEXCOORD_0", "JOINTS_0", "WEIGHTS_0"):
            a = accessor(gm, bm, pm["primitives"][0]["attributes"][attr])
            b = accessor(gf, bf, pf["primitives"][0]["attributes"][attr])
            assert np.array_equal(a, b), f"{attr} 불일치"


def test_seam_duplicates_stay_coincident():
    """male 에서 같은 위치였던 중복 정점(셰이딩/UV 시임)은 female 에서도 같은 위치여야 한다(균열 방지)."""
    m, f = models()
    inv = weld(m.pos)
    order = np.argsort(inv, kind="stable")
    first = np.zeros(inv.max() + 1, int)
    first[inv[order][::-1]] = order[::-1]
    spread = np.linalg.norm(f.pos - f.pos[first[inv]], axis=1)
    bad = np.where(spread > 1e-6)[0]
    assert len(bad) == 0, f"시임 균열 {len(bad)}개: " + "; ".join(vdesc(i) for i in bad[:5])


def test_part_labels_cover_all_vertices():
    """QA 부위 분류가 모든 정점을 덮는지(다른 테스트의 전제)."""
    L = parts()
    assert all(isinstance(x, str) and ":" in x for x in L)
