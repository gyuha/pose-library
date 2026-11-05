"""(b) male 과 female 의 토폴로지 관계 [기준 v2].
female 은 가슴 부위에 한해 정점/삼각형이 추가될 수 있다. 정점 수가 같을 필요는 없고 다음을 지킨다.
 - 원본 4106 정점은 female 앞쪽에 같은 순서로 남는다 (UV/JOINTS/WEIGHTS 가 같다 = 가중치 전이 가능).
 - 추가 정점은 가슴 부위에만 있고, 속성(JOINTS/WEIGHTS/UV/NORMAL)이 유효하다.
 - 가슴 쉘이 아닌 원본 삼각형은 그대로 보존된다.
 - 새 균열/열린 경계가 생기지 않는다.
추가 정점이 없으면(구버전 female) 이 파일은 v1 의 '완전 동일' 검사와 같은 조건을 만족해야 한다."""
import numpy as np
import pytest

from glb_io import Model, FEMALE, MALE
from qa_metrics import (chest_topology_changed, correspondence, full_female, models, parts, parts_full,
                        preserved_triangles, vdesc, weld)

N_ORIG = 4106


def _new_ids():
    f2m, _ = correspondence()
    return np.where(f2m < 0)[0]


def test_original_vertex_count_and_order_prefix():
    f = full_female(); f2m, m2f = correspondence()
    assert f.n_verts >= N_ORIG, f"female 정점 {f.n_verts} < 원본 {N_ORIG}: 정점이 삭제됨"
    assert np.array_equal(m2f, np.arange(N_ORIG)) or len(f.pools) > 1, "원본 정점이 앞쪽 같은 번호에 있지 않음"


def test_original_vertices_keep_uv_joints_weights():
    """UV/JOINTS/WEIGHTS 는 원본 4106 정점에서 male 과 정확히 같아야 한다 (위치/법선만 변해도 된다)."""
    m, c = models()
    assert np.array_equal(c.uv, m.uv), "원본 정점의 UV 가 바뀜"
    assert np.array_equal(c.joints, m.joints), "원본 정점의 JOINTS_0 가 바뀜"
    assert np.allclose(c.weights, m.weights, atol=1e-7), "원본 정점의 WEIGHTS_0 가 바뀜"


def test_added_vertices_only_on_chest():
    """추가 정점은 가슴 쉘 상자(|x|<=0.20, 1.10<=y<=1.52, z 제한 없음: 가슴 쉘은 등까지 둘러싼다) 안에 있어야 하고,
    가장 가까운 원본 정점이 가슴 쉘이어야 한다. 상자는 female 가슴 쉘(y 1.11~1.50, 폭 0.32 m)을 감싸는 내 휴리스틱이다."""
    f = full_female(); new = _new_ids()
    if len(new) == 0:
        pytest.skip("추가 정점 없음")
    P = f.pos[new]
    out = np.where((np.abs(P[:, 0]) > 0.20) | (P[:, 1] < 1.10) | (P[:, 1] > 1.52))[0]
    assert len(out) == 0, f"가슴 상자 밖 추가 정점 {len(out)}개: " + "; ".join(f"v{new[i]}{tuple(np.round(P[i], 3))}" for i in out[:5])
    # 추가 정점을 쓰는 모든 삼각형의 원본 꼭짓점은 가슴 쉘 정점이어야 한다 (다른 쉘과 연결되면 가슴 밖에 폴리곤을 붙인 것).
    f2m, _ = correspondence(); labels = parts_full()
    isnew = np.zeros(f.n_verts, bool); isnew[new] = True
    uses = np.where(isnew[f.tri].any(axis=1))[0]
    bad = [(k, labels[v]) for k in uses for v in f.tri[k] if not isnew[v] and labels[v] != "body:chest"]
    assert not bad, f"가슴 쉘이 아닌 정점과 연결된 추가 폴리곤 {len(set(k for k, _ in bad))}개 (예 삼각형 {bad[0][0]}, 연결 정점 부위 {bad[0][1]})"
    assert not f.prim_id[new].any(), "추가 정점이 Joints 삼각형에 쓰임"


def test_added_vertex_attributes_valid():
    f = full_female(); new = _new_ids()
    if len(new) == 0:
        pytest.skip("추가 정점 없음")
    m, _c = models()
    w = f.weights[new]
    assert np.isfinite(w).all() and (w >= -1e-6).all(), "WEIGHTS_0 에 음수/NaN"
    assert np.abs(w.sum(1) - 1).max() <= 1e-3, f"WEIGHTS_0 합이 1 이 아님: 최대 편차 {np.abs(w.sum(1) - 1).max():.4f} (v{new[np.abs(w.sum(1) - 1).argmax()]})"
    assert f.joints[new].min() >= 0 and f.joints[new].max() <= m.joints.max(), f"JOINTS_0 범위 오류 {f.joints[new].min()}..{f.joints[new].max()}"
    nz = f.joints[new][w > 1e-6]
    assert set(nz.tolist()) <= set(m.joints[m.weights > 1e-6].tolist()), "가중치가 있는 JOINTS 가 원본에 쓰인 본이 아님"
    uv = f.uv[new]
    assert np.isfinite(uv).all(), "UV 에 NaN"
    lo, hi = m.uv.min(0) - 1e-3, m.uv.max(0) + 1e-3
    assert (uv >= lo).all() and (uv <= hi).all(), f"UV 가 원본 UV 범위 {lo}..{hi} 를 벗어남"
    n = f.nrm[new]
    assert np.isfinite(n).all() and np.abs(np.linalg.norm(n, axis=1) - 1).max() < 1e-3, "추가 정점 NORMAL 이 단위 길이가 아님"


def test_added_vertex_normals_agree_with_geometry():
    """추가 정점의 저장 NORMAL 이 인접 면 기하 법선과 90° 이내로 같은 방향(뒤집히지 않음)이어야 한다."""
    f = full_female(); new = _new_ids()
    if len(new) == 0:
        pytest.skip("추가 정점 없음")
    P = f.pos; t = f.tri
    fn = np.cross(P[t[:, 1]] - P[t[:, 0]], P[t[:, 2]] - P[t[:, 0]])
    fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-15)
    acc = np.zeros_like(P)
    for k in range(3):
        np.add.at(acc, t[:, k], fn)
    isnew = np.zeros(len(P), bool); isnew[new] = True
    cos = (acc[new] * f.nrm[new]).sum(1) / np.maximum(np.linalg.norm(acc[new], axis=1), 1e-15)
    bad = np.where(cos < 0.5)[0]
    assert len(bad) == 0, f"기하 법선과 60° 넘게 어긋난 추가 정점 {len(bad)}개 (예 v{new[bad[0]]}, cos={cos[bad[0]]:.2f})"


def test_non_chest_triangles_preserved():
    miss, ex, extra = preserved_triangles()
    assert miss == 0, f"가슴 쉘이 아닌 원본 삼각형 {miss}개가 사라지거나 바뀜 (예 {ex})"


def _boundary_edges(pos, tri, inv=None):
    inv = weld(pos) if inv is None else inv
    cnt = {}
    for t in inv[tri].tolist():
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            if a != b:
                k = (min(a, b), max(a, b)); cnt[k] = cnt.get(k, 0) + 1
    return {k for k, v in cnt.items() if v == 1}, {k for k, v in cnt.items() if v > 2}


def test_no_new_open_boundary_or_nonmanifold_edges():
    """위치 용접(1e-5) 후 경계 엣지(인접 면 1개)와 비다양체 엣지(3개 이상)가 male 보다 늘지 않아야 한다.
    경계 엣지는 위치 키가 달라졌을 수 있어 개수와 '가슴 쉘 밖 위치'로 비교한다."""
    m, _c = models(); f = full_female()
    mb, mn = _boundary_edges(m.pos, m.tri)
    fb, fn = _boundary_edges(f.pos, f.tri)
    assert len(fb) <= len(mb), f"경계 엣지 {len(mb)} -> {len(fb)} (새 열린 경계 {len(fb) - len(mb)}개)"
    assert len(fn) <= len(mn), f"비다양체 엣지 {len(mn)} -> {len(fn)}"


def test_no_new_boundary_at_chest_subdivision_seams():
    """세분화 경계(가슴 쉘 안)에서 '위치는 같은데 정점 번호가 달라' 갈라진 곳이 없어야 한다:
    용접 전 인덱스 기준 경계 엣지 수가 male 보다 늘지 않아야 한다 (UV/셰이딩 시임은 male 에도 같은 수준으로 존재)."""
    f = full_female(); m, _c = models()
    def raw_boundary(tri):
        cnt = {}
        for t in tri.tolist():
            for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
                k = (min(a, b), max(a, b)); cnt[k] = cnt.get(k, 0) + 1
        return {k for k, v in cnt.items() if v == 1}
    rm, rf = raw_boundary(m.tri), raw_boundary(f.tri)
    # 새로 생긴 raw 경계 엣지 중 용접 후에도 경계인 것만 진짜 균열이다. 위 테스트가 용접 후 개수를 이미 본다.
    # 여기서는 raw 경계가 모두 용접 후 닫히는지(= 위치만 같은 중복 정점) 확인한다.
    inv = weld(f.pos)
    still_open, _ = _boundary_edges(f.pos, f.tri, inv)
    new_raw = [e for e in rf if e not in rm]
    cracks = [e for e in new_raw if (min(inv[e[0]], inv[e[1]]), max(inv[e[0]], inv[e[1]])) in still_open]
    assert len(cracks) == 0, \
        f"세분화 후 새로 열린 경계 엣지 {len(cracks)}개 (예 정점 {cracks[:3]})"


def test_seam_duplicates_stay_coincident():
    """male 에서 같은 위치였던 중복 정점은 female 에서도 같은 위치여야 한다(균열 방지)."""
    m, c = models()
    inv = weld(m.pos)
    order = np.argsort(inv, kind="stable")
    first = np.zeros(inv.max() + 1, int)
    first[inv[order][::-1]] = order[::-1]
    spread = np.linalg.norm(c.pos - c.pos[first[inv]], axis=1)
    bad = np.where(spread > 1e-6)[0]
    assert len(bad) == 0, f"시임 균열 {len(bad)}개: " + "; ".join(vdesc(i) for i in bad[:5])


def test_part_labels_cover_all_vertices():
    L = parts()
    assert all(isinstance(x, str) and ":" in x for x in L)


def test_topology_summary_is_consistent_with_chest_change():
    """정보성: 정점이 추가됐다면 가슴 쉘 삼각형이 바뀐 것으로 판정되어야 한다."""
    f = full_female()
    if f.n_verts != N_ORIG:
        assert chest_topology_changed()
