"""female.glb 품질 지표 계산 (순수 numpy). 모든 함수는 male/female Model 을 읽기만 한다."""
import functools
import math

import numpy as np

from glb_io import FEMALE, MALE, Model

# --------------------------------------------------------------------------- 로딩/용접
@functools.lru_cache(None)
def full_female():
    return Model(FEMALE)


@functools.lru_cache(None)
def correspondence():
    """(f2m, m2f): female 정점 -> male 정점 번호(없으면 -1), male 정점 -> female 정점 번호.
    female 이 공유 정점 풀 1개면 앞쪽 N_male 개가 male 과 같은 번호, 풀이 male 처럼 여러 개면 풀마다 앞쪽이 대응한다."""
    m = Model(MALE); f = full_female()
    f2m = np.full(f.n_verts, -1)
    if len(f.pools) == 1:
        f2m[:m.n_verts] = np.arange(m.n_verts)
    elif len(f.pools) == len(m.pools):
        for (mb, me), (fb, fe) in zip(m.pools, f.pools):
            f2m[fb:fb + (me - mb)] = np.arange(mb, me)
    else:
        raise AssertionError("female 정점 풀 구성을 male 과 대응시킬 수 없음")
    m2f = np.full(m.n_verts, -1)
    ok = f2m >= 0
    m2f[f2m[ok]] = np.where(ok)[0]
    assert (m2f >= 0).all(), "male 정점 중 female 에 대응이 없는 것이 있음 (정점이 삭제됨)"
    return f2m, m2f


@functools.lru_cache(None)
def models():
    """(male, female_core). female_core = female 의 앞쪽 4106 정점을 male 순서로 정렬한 뷰(삼각형은 male 의 것을 사용).
    modeler 가 정점/삼각형을 추가해도 '원본 정점의 변형'을 기존 방식으로 측정할 수 있게 한다.
    추가 정점/세분화 삼각형을 포함한 실제 female 은 full_female() 로 얻는다."""
    m = Model(MALE)
    f = full_female()
    _, m2f = correspondence()
    c = object.__new__(Model)
    c.gltf, c.buf = f.gltf, f.buf
    c.pos, c.nrm, c.uv, c.joints, c.weights = f.pos[m2f], f.nrm[m2f], f.uv[m2f], f.joints[m2f], f.weights[m2f]
    c.tri, c.tri_mat, c.prim_id, c.pools, c.prims = m.tri, m.tri_mat, m.prim_id, m.pools, m.prims
    return m, c


def weld(pos, tol=1e-5):
    """같은 위치(UV/셰이딩 시임으로 중복된) 정점을 하나로 묶는 인덱스. male 위치 기준으로 사용."""
    key = np.round(pos / tol).astype(np.int64)
    _, inv = np.unique(key, axis=0, return_inverse=True)
    return inv.ravel()


def _components(tri, inv):
    par = list(range(inv.max() + 1))

    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x

    for a, b, c in inv[tri]:
        for u, v in ((a, b), (b, c)):
            ru, rv = find(u), find(v)
            if ru != rv:
                par[ru] = rv
    return np.array([find(i) for i in range(inv.max() + 1)])


def _label(prim, c, mn, mx, n):
    """male 정점 기준 연결 성분 -> 사람이 읽는 부위 이름 (Body 쉘 / Joints 링)."""
    x = abs(c[0]); y = c[1]; side = "" if x < 0.02 else ("_L" if c[0] > 0 else "_R")
    if prim == 0:  # Body 쉘
        if y > 1.7: return "head"
        if x > 0.5 and y < 1.13: return "hand" + side
        if y > 1.3 and x < 0.02: return "chest"
        if x > 0.2 and y > 1.3: return "upper_arm" + side
        if x > 0.3 and y > 1.05: return "forearm" + side
        if y > 1.05 and x < 0.02: return "abdomen"
        if y > 0.85 and x < 0.02: return "pelvis"
        if y > 0.6: return "thigh" + side
        if y > 0.25: return "shin" + side
        return "foot" + side
    if y > 1.55: return "neck"
    if y > 1.4: return "shoulder" + side
    if y > 1.15: return "elbow" + side
    if y > 1.09 and x > 0.3: return "wrist" + side
    if y > 0.95 and x < 0.02: return "waist_band"
    if y > 0.7: return "hip_joint" + side
    if y > 0.35: return "knee" + side
    return "ankle" + side


@functools.lru_cache(None)
def parts():
    """정점별 부위 라벨(문자열 배열). 'body:thigh_L' / 'joint:knee_R' 형식."""
    m, _ = models()
    inv = weld(m.pos)
    root = _components(m.tri, inv)  # inv 인덱스 -> 성분 루트
    comp = root[inv]
    labels = np.empty(m.n_verts, dtype=object)
    for pid in (0, 1):
        for r in set(comp[m.prim_id == pid]):
            sel = (comp == r) & (m.prim_id == pid)
            P = m.pos[sel]
            name = _label(pid, P.mean(0), P.min(0), P.max(0), sel.sum())
            labels[sel] = ("body:" if pid == 0 else "joint:") + name
    return labels


def group_of(label):
    """부위 라벨 -> 보고용 큰 그룹 (좌우 병합)."""
    n = label.split(":")[1]
    return n.replace("_L", "").replace("_R", "")


# --------------------------------------------------------------------------- 그래프
@functools.lru_cache(None)
def welded_edges():
    m, _ = models()
    inv = weld(m.pos)
    e = np.vstack([m.tri[:, [0, 1]], m.tri[:, [1, 2]], m.tri[:, [2, 0]]])
    e = inv[e]
    e = e[e[:, 0] != e[:, 1]]
    e = np.unique(np.sort(e, axis=1), axis=0)
    return inv, e


def welded_positions(model):
    inv, _ = welded_edges()
    n = inv.max() + 1
    out = np.zeros((n, 3))
    out[inv] = model.pos
    return out, inv


# --------------------------------------------------------------------------- 지오메트리
def _seg_closest(p, a, b):
    ab = b - a
    t = np.clip(((p - a) * ab).sum(-1) / np.maximum((ab * ab).sum(-1), 1e-30), 0, 1)
    return a + t[..., None] * ab


def tri_point_dist(P, T):
    """점 P(n,3) 와 삼각형 T(m,3,3) 의 최근접점. 반환: (거리 (n,m), 최근접점 (n,m,3))."""
    a = T[:, 0][None]; b = T[:, 1][None]; c = T[:, 2][None]; p = P[:, None]
    nrm = np.cross(b - a, c - a)
    nn = np.maximum((nrm * nrm).sum(-1), 1e-30)
    proj = p - (((p - a) * nrm).sum(-1) / nn)[..., None] * nrm
    # 질량중심 좌표로 투영점이 삼각형 내부인지 판정
    u = (np.cross(c - b, proj - b) * nrm).sum(-1) / nn
    v = (np.cross(a - c, proj - c) * nrm).sum(-1) / nn
    w = 1 - u - v
    inside = (u >= 0) & (v >= 0) & (w >= 0)
    best = np.where(inside[..., None], proj, np.nan)
    cand = [_seg_closest(p, a, b), _seg_closest(p, b, c), _seg_closest(p, c, a)]
    d = np.where(inside, np.linalg.norm(p - proj, axis=-1), np.inf)
    for q in cand:
        dq = np.linalg.norm(p - q, axis=-1)
        better = dq < d
        d = np.where(better, dq, d)
        best = np.where(better[..., None], q, best)
    return d, best


def signed_depth(P, T):
    """점 P 가 삼각형 집합 T(닫힌 쉘 가정)에 대해 얼마나 안쪽인가. 양수 = 내부(관통), 음수 = 외부(거리).
    최근접 삼각형의 법선(권선순서 기준)으로 부호를 정한다."""
    d, q = tri_point_dist(P, T)
    k = d.argmin(1)
    i = np.arange(len(P))
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    s = np.einsum("ij,ij->i", P - q[i, k], n[k])
    return np.where(s < 0, d[i, k], -d[i, k])


# --------------------------------------------------------------------------- 단면 / 이음매
def part_tris(model, label):
    L = parts()
    idx = np.where(L == label)[0]
    lo, hi = idx.min(), idx.max()
    mask = np.isin(model.tri[:, 0], idx)
    return model.pos[model.tri[mask]]


def section_points(T, n, d):
    """삼각형 집합 T(m,3,3) 와 평면 n·x=d 의 교차점들 (m 개 삼각형의 모서리 교점)."""
    s = T @ n - d
    pts = []
    for i, j in ((0, 1), (1, 2), (2, 0)):
        a, b = s[:, i], s[:, j]
        hit = (a * b) < 0
        t = a[hit] / (a[hit] - b[hit])
        pts.append(T[hit, i] + t[:, None] * (T[hit, j] - T[hit, i]))
    return np.vstack(pts) if pts else np.zeros((0, 3))


def _basis(n):
    a = np.array([1.0, 0, 0]) if abs(n[0]) < 0.9 else np.array([0, 1.0, 0])
    u = np.cross(n, a); u /= np.linalg.norm(u)
    return u, np.cross(n, u)


def hull(pts2):
    p = sorted(map(tuple, pts2))
    def half(seq):
        h = []
        for q in seq:
            while len(h) >= 2 and (h[-1][0]-h[-2][0])*(q[1]-h[-2][1]) - (h[-1][1]-h[-2][1])*(q[0]-h[-2][0]) <= 0:
                h.pop()
            h.append(q)
        return h[:-1]
    return np.array(half(p) + half(p[::-1]))


def hull_area_perimeter(pts2):
    if len(pts2) < 3:
        return 0.0, 0.0
    h = hull(pts2)
    x, y = h[:, 0], h[:, 1]
    area = 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))
    per = np.linalg.norm(h - np.roll(h, -1, axis=0), axis=1).sum()
    return area, per


def section_stats(T, n, d):
    """평면 단면의 (중심3D, 등가반지름, 둘레, 평면 u/v 폭). 단면이 비면 None."""
    P = section_points(T, n, d)
    if len(P) < 3:
        return None
    u, v = _basis(n)
    q = np.c_[P @ u, P @ v]
    area, per = hull_area_perimeter(q)
    return {"center": P.mean(0), "r_eq": math.sqrt(area / math.pi), "perimeter": per,
            "w_u": float(np.ptp(q[:, 0])), "w_v": float(np.ptp(q[:, 1]))}


# 이음매 정의: (관절 링, 맞닿는 Body 쉘). male 에서 40 mm 안쪽으로 근접한 쌍만 사용한다.
def seam_pairs(max_dist=0.04):
    m, _ = models()
    L = parts()
    names = sorted(set(L))
    out = []
    for J in (n for n in names if n.startswith("joint:")):
        for B in (n for n in names if n.startswith("body:")):
            if np.linalg.norm(m.pos[L == J][:, None] - m.pos[L == B][None], axis=2).min() <= max_dist:
                out.append((J, B))
    return out


def seam_drift(J, B):
    """male 에서 B 표면 25 mm 이내였던 J 정점들의 B 표면까지 '비부호 거리' 변화 (female - male) [m].
    (부호 있는 깊이는 열린 쉘에서 부호가 뒤집혀 잡음이 크므로 쓰지 않는다.)
    gap_growth: 가장 크게 멀어진 양(틈이 벌어지는 방향), closing: 가장 크게 가까워진 양(관통이 깊어지는 방향)."""
    m, f = models()
    L = parts()
    idx = np.where(L == J)[0]
    dm, _ = tri_point_dist(m.pos[idx], part_tris(m, B))
    df, _ = tri_point_dist(f.pos[idx], part_tris(f, B))
    dm = dm.min(1); df = df.min(1)
    near = dm < 0.025
    if not near.any():
        return None
    delta = (df - dm)[near]
    ids = idx[near]
    return {"seam": f"{J}|{B}", "n": int(near.sum()),
            "max_gap_growth": float(max(0.0, delta.max())), "max_closing": float(max(0.0, -delta.min())),
            "gap_vertex": int(ids[delta.argmax()]), "closing_vertex": int(ids[delta.argmin()])}


# --------------------------------------------------------------------------- 변형 매끄러움
SCALE = 0.925  # make_female.py 의 전체 균일 스케일 (README 에 명시)


def edge_strain():
    """용접 모서리별 (female 길이 / (SCALE * male 길이)). 1.0 = 순수 균일 스케일."""
    m, f = models()
    M, _ = welded_positions(m)
    F, _ = welded_positions(f)
    _, E = welded_edges()
    em = np.linalg.norm(M[E[:, 0]] - M[E[:, 1]], axis=1)
    ef = np.linalg.norm(F[E[:, 0]] - F[E[:, 1]], axis=1)
    return E, ef / (SCALE * em), M, F


def umbrella_delta():
    """정점별 '이웃 평균 대비 법선 방향 돌출량'의 male→female 변화 [m]. +: 새로 생긴 돌출, -: 새로 생긴 함몰."""
    m, f = models()
    inv, E = welded_edges()
    M, _ = welded_positions(m)
    F, _ = welded_positions(f)
    n = len(M)
    nb = [[] for _ in range(n)]
    for a, b in E:
        nb[a].append(b); nb[b].append(a)

    def lap(X):
        return np.array([X[i] - X[nb[i]].mean(0) for i in range(n)])

    def vnormals(X):
        t = inv[f.tri]
        fn = np.cross(X[t[:, 1]] - X[t[:, 0]], X[t[:, 2]] - X[t[:, 0]])
        vn = np.zeros_like(X)
        for k in range(3):
            np.add.at(vn, t[:, k], fn)
        return vn / np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-12)

    nm, nf = vnormals(M), vnormals(F)
    return (lap(F) * nf).sum(1) - SCALE * (lap(M) * nm).sum(1), M, F


def label_of_welded():
    inv, _ = welded_edges()
    lab = np.empty(inv.max() + 1, dtype=object)
    lab[inv] = parts()
    return lab


def members(welded_index):
    inv, _ = welded_edges()
    return np.where(inv == welded_index)[0]


def chest_groove(model):
    """가슴 쉘 전면 같은 행(male 의 높이로 행을 정의)에서 [좌우 최대 돌출 z] - [중앙(|x|<1cm) z]. 양수 = 중앙이 움푹 들어감.
    반환 (깊이[m], 행의 male 높이, 돌출 정점 인덱스)."""
    m, _ = models()
    L = parts()
    sel = np.where((L == "body:chest") & (m.pos[:, 2] > 0.03))[0]
    best = (0.0, None, None)
    for y in sorted(set(np.round(m.pos[sel, 1], 3))):
        row = sel[np.abs(m.pos[sel, 1] - y) < 4e-3]
        c = row[np.abs(m.pos[row, 0]) < 0.01]
        o = row[np.abs(m.pos[row, 0]) >= 0.03]
        if len(c) and len(o):
            k = o[model.pos[o, 2].argmax()]
            g = float(model.pos[k, 2] - model.pos[c, 2].max())
            if g > best[0]:
                best = (g, float(y), int(k))
    return best


# --------------------------------------------------------------------------- 메시 교차
TRI_NEW = 100000  # female 에서 새로 생긴/바뀐 삼각형 식별자 오프셋


def strict_intersections(T):
    """정확한 삼각형 쌍 교차(엣지-삼각형 내부 교차, 공유 정점/엣지/동일 평면 제외). verify.py 와 동일 판정 기준을 독립 구현."""
    mins = T.min(1); maxs = T.max(1)
    pairs = set()
    for i in range(len(T)):
        a = T[i]
        ids = np.where((np.arange(len(T)) > i) & np.all(maxs >= mins[i] - 1e-8, 1) & np.all(mins <= maxs[i] + 1e-8, 1))[0]
        if not len(ids):
            continue
        bs = T[ids]
        hit = np.zeros(len(ids), bool)
        for rev in (False, True):
            A = bs if rev else np.broadcast_to(a, bs.shape)
            B = np.broadcast_to(a, bs.shape) if rev else bs
            e1 = B[:, 1] - B[:, 0]; e2 = B[:, 2] - B[:, 0]
            for k in range(3):
                o = A[:, k]; d = A[:, (k + 1) % 3] - o
                h = np.cross(d, e2); det = (e1 * h).sum(1)
                ok = np.abs(det) > 1e-10
                inv = np.zeros(len(ids)); inv[ok] = 1 / det[ok]
                s = o - B[:, 0]; u = inv * (s * h).sum(1)
                q = np.cross(s, e1); v = inv * (d * q).sum(1); t = inv * (e2 * q).sum(1)
                hit |= ok & (u > 1e-6) & (v > 1e-6) & (u + v < 1 - 1e-6) & (t > 1e-6) & (t < 1 - 1e-6)
        pairs.update((i, int(ids[k])) for k in np.where(hit)[0])
    return pairs


@functools.lru_cache(None)
def female_tri_ids():
    """female 삼각형별 식별자: male 과 정점 구성이 같으면 male 삼각형 번호, 아니면 TRI_NEW + female 삼각형 번호."""
    m = models()[0]; f = full_female()
    f2m, _ = correspondence()
    mset = {tuple(sorted(t)): i for i, t in enumerate(m.tri.tolist())}
    ids = np.empty(len(f.tri), int)
    for k, t in enumerate(f.tri.tolist()):
        g = f2m[t]
        ids[k] = mset.get(tuple(sorted(g.tolist())), -1) if (g >= 0).all() else -1
        if ids[k] < 0:
            ids[k] = TRI_NEW + k
    return ids


@functools.lru_cache(None)
def intersection_sets():
    """(male 교차쌍, female 교차쌍). female 은 세분화된 실제 메시(full_female)로 계산한다.
    삼각형 식별자: male 삼각형과 정점 구성이 같으면 male 삼각형 번호, 아니면 TRI_NEW+female 삼각형 번호.
    (가슴 세분화로 삼각형이 바뀌어도 가슴 밖 쌍은 male 과 1:1 비교된다.)"""
    m = models()[0]; f = full_female()
    ids = female_tri_ids()
    a = strict_intersections(m.pos[m.tri])
    b = {tuple(sorted((int(ids[i]), int(ids[j])))) for i, j in strict_intersections(f.pos[f.tri])}
    return a, b



def tri_label(tri_id):
    """삼각형 식별자 -> 부위 라벨 (male 번호 또는 TRI_NEW+female 번호)."""
    if tri_id >= TRI_NEW:
        return tri_labels_full()[tri_id - TRI_NEW]
    return parts()[models()[0].tri[tri_id, 0]]


def pair_key(p):
    a, b = sorted((tri_label(p[0]), tri_label(p[1])))
    return f"{a} x {b}"


# --------------------------------------------------------------------------- 비율
def height(model):
    return float(np.ptp(model.pos[:, 1]))


def _source(model):
    """측정용 (pos, tri, 정점라벨). core female 이면 세분화된 실제 메시(full_female)를 쓴다."""
    m, c = models()
    if model is c:
        f = full_female()
        return f.pos, f.tri, parts_full()
    return model.pos, model.tri, parts()


def torso_triangles(model):
    """몸통 둘레 측정용: 가슴/복부/골반 쉘 + 허리 밴드 + 고관절 링 (팔·다리·머리·목 제외). 가슴 추가 폴리곤 포함."""
    pos, tri, L = _source(model)
    keep = np.array([n in ("body:chest", "body:abdomen", "body:pelvis", "joint:waist_band")
                     or n.startswith("joint:hip_joint") for n in L])
    return pos[tri[keep[tri[:, 0]]]]


def girth_profile(model, ys):
    """높이 ys 마다 몸통 단면 컨벡스헐 (둘레, 폭 x, 깊이 z)."""
    T = torso_triangles(model)
    out = []
    for y in ys:
        P = section_points(T, np.array([0, 1.0, 0]), y)
        if len(P) < 3:
            out.append((np.nan,) * 3); continue
        q = P[:, [0, 2]]
        _, per = hull_area_perimeter(q)
        out.append((per, float(np.ptp(q[:, 0])), float(np.ptp(q[:, 1]))))
    return np.array(out)


def torso_measures(model):
    """허리/엉덩이/가슴 둘레와 폭. 키(H) 대비 위치로 구간을 정의한다 (Winter 2009 Fig 4.1 의 높이 비율 사용)."""
    H = height(model)
    ys = np.linspace(0.40 * H, 0.80 * H, 161)
    g = girth_profile(model, ys)
    def zone(lo, hi, fn):
        s = (ys >= lo * H) & (ys <= hi * H)
        k = fn(g[s, 0]); return float(g[s, 0][k]), float(ys[s][k] / H), float(g[s, 1][k]), float(g[s, 2][k])
    waist = zone(0.58, 0.70, np.nanargmin)   # 허리: 몸통 최소 둘레
    hip = zone(0.44, 0.56, np.nanargmax)     # 엉덩이: 대퇴골 대전자 높이(0.53H) 부근 최대 둘레
    bust = zone(0.68, 0.76, np.nanargmax)    # 가슴: 유두 높이(0.72H) 부근
    return {"waist": waist, "hip": hip, "bust": bust, "whr": waist[0] / hip[0], "waist_bust": waist[0] / bust[0]}


def x_extent(model, label_prefix):
    L = parts()
    sel = np.array([l.startswith(label_prefix) for l in L])
    return float(np.ptp(model.pos[sel, 0]))


def proportions(model):
    """키 대비 주요 비율. 점/링 중심은 male 에서 정의한 부위 라벨로 구한다 (female 도 동일 라벨 = 위상 동일)."""
    L = parts()
    H = height(model)
    def c(lbl, side=""): return model.pos[L == lbl].mean(0)
    head = model.pos[L == "body:head"]
    out = {"H": H, "head_height": float(np.ptp(head[:, 1])), "head_width": float(np.ptp(head[:, 0])),
           "head_depth": float(np.ptp(head[:, 2]))}
    out["heads_tall"] = H / out["head_height"]
    sh = model.pos[np.array([l.startswith("joint:shoulder") for l in L])]
    out["shoulder_width"] = float(np.ptp(sh[:, 0]))          # 어깨 링 바깥-바깥(삼각근 폭에 해당)
    pel = model.pos[np.array([l in ("body:pelvis",) or l.startswith("joint:hip_joint") for l in L])]
    out["hip_width"] = float(np.ptp(pel[:, 0]))
    th = model.pos[np.array([l.startswith("body:thigh") for l in L])]
    out["thigh_outer_width"] = float(np.ptp(th[:, 0]))
    out["shoulder_hip_ratio"] = out["shoulder_width"] / out["hip_width"]
    out["shoulder_hip_ratio_thigh"] = out["shoulder_width"] / out["thigh_outer_width"]
    # 관절 중심 간 분절 길이 (좌측)
    seg = lambda a, b: float(np.linalg.norm(c(a) - c(b)))
    out["upper_arm_len"] = seg("joint:shoulder_L", "joint:elbow_L") if False else float(np.linalg.norm(model.pos[L == "joint:shoulder_L"].mean(0) - model.pos[L == "joint:elbow_L"].mean(0)))
    out["forearm_len"] = float(np.linalg.norm(model.pos[L == "joint:elbow_L"].mean(0) - model.pos[L == "joint:wrist_L"].mean(0)))
    hand = model.pos[L == "body:hand_L"]
    wr = model.pos[L == "joint:wrist_L"].mean(0)
    out["hand_len"] = float(np.linalg.norm(hand - wr, axis=1).max())
    out["thigh_len"] = float(np.linalg.norm(model.pos[L == "joint:hip_joint_L"].mean(0) - model.pos[L == "joint:knee_L"].mean(0)))
    out["shin_len"] = float(np.linalg.norm(model.pos[L == "joint:knee_L"].mean(0) - model.pos[L == "joint:ankle_L"].mean(0)))
    out["hip_joint_height"] = float(model.pos[L == "joint:hip_joint_L"].mean(0)[1])
    out["knee_height"] = float(model.pos[L == "joint:knee_L"].mean(0)[1])
    out["shoulder_height"] = float(model.pos[L == "joint:shoulder_L"].mean(0)[1])
    out["chin_height"] = float(head[:, 1].min())
    chest = model.pos[L == "body:chest"]
    out["chest_top"] = float(chest[:, 1].max())
    out["neck_exposed"] = out["chin_height"] - out["chest_top"]  # <0 이면 머리 밑면이 가슴 윗면보다 낮음(겹침)
    foot = model.pos[np.array([l.startswith("body:foot") for l in L])]
    out["foot_length"] = float(np.ptp(foot[:, 2]))
    return out


# --------------------------------------------------------------------------- 좌우 대칭
def mirror_map(model):
    """x 부호를 뒤집은 위치의 최근접 정점(같은 프리미티브) 인덱스와 그 거리(m)."""
    P = model.pos.copy(); Q = P * np.array([-1, 1, 1])
    idx = np.zeros(len(P), int); dist = np.zeros(len(P))
    for pid in (0, 1):
        s = np.where(model.prim_id == pid)[0]
        d = np.linalg.norm(Q[s][:, None] - P[s][None], axis=2)
        k = d.argmin(1); idx[s] = s[k]; dist[s] = d.min(1)
    return idx, dist


def asymmetry(model, mmap):
    """mmap(= male 기준 좌우 대응)을 이용해 model 의 좌우 불일치 거리 [m]."""
    P = model.pos
    return np.linalg.norm(P * np.array([-1, 1, 1]) - P[mmap], axis=1)


# --------------------------------------------------------------------------- 보고 보조
def vdesc(i):
    """원본(비용접) 정점 인덱스 -> 'idx label male(x,y,z)->female(x,y,z)' 설명 문자열."""
    m, f = models()
    fmt = lambda v: "(" + ",".join(f"{float(x):.3f}" for x in v) + ")"
    return f"v{i} {parts()[i]} male{fmt(m.pos[i])}->fem{fmt(f.pos[i])}"


def tri_dev_from_normals(model):
    """삼각형별: 저장된 정점 NORMAL 과 기하 면 법선 사이 최대 각도(도)."""
    t = model.tri; P = model.pos
    fn = np.cross(P[t[:, 1]] - P[t[:, 0]], P[t[:, 2]] - P[t[:, 0]])
    fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-15)
    out = np.zeros(len(t))
    for k in range(3):
        out = np.maximum(out, np.degrees(np.arccos(np.clip((model.nrm[t[:, k]] * fn).sum(1), -1, 1))))
    return out


def face_normal_rotation(m, f):
    """삼각형별 male->female 면 법선 회전각(도)."""
    n0 = np.cross(m.pos[m.tri[:, 1]] - m.pos[m.tri[:, 0]], m.pos[m.tri[:, 2]] - m.pos[m.tri[:, 0]])
    n1 = np.cross(f.pos[f.tri[:, 1]] - f.pos[f.tri[:, 0]], f.pos[f.tri[:, 2]] - f.pos[f.tri[:, 0]])
    c = (n0 * n1).sum(1) / (np.linalg.norm(n0, axis=1) * np.linalg.norm(n1, axis=1))
    return np.degrees(np.arccos(np.clip(c, -1, 1)))


# --------------------------------------------------------------------------- 실제(세분화된) female 라벨
@functools.lru_cache(None)
def parts_full():
    """full_female 정점별 부위 라벨. 원본 정점은 male 라벨을 따르고, 추가 정점은 'body:chest' 로 둔다(위치 검사는 test_02)."""
    f2m, _ = correspondence()
    lab = np.empty(len(f2m), dtype=object)
    old = f2m >= 0
    lab[old] = parts()[f2m[old]]
    lab[~old] = "body:chest"
    return lab


@functools.lru_cache(None)
def tri_labels_full():
    f = full_female(); L = parts_full()
    lab = L[f.tri[:, 0]].copy()
    chest_any = (L[f.tri] == "body:chest").any(axis=1)
    lab[chest_any] = "body:chest"
    return lab


def male_tri_keys(mask=None):
    m = models()[0]
    t = m.tri if mask is None else m.tri[mask]
    return {tuple(sorted(x)) for x in t.tolist()}


def preserved_triangles():
    """male 의 '가슴 쉘이 아닌' 삼각형이 female 에 (male 정점 번호 기준으로) 그대로 있는지.
    반환: (missing 개수, missing 예시, female 에서 원본 정점만으로 이뤄졌지만 male 에 없는 삼각형 수)."""
    m = models()[0]; f = full_female(); f2m, _ = correspondence(); L = parts()
    nonchest = L[m.tri[:, 0]] != "body:chest"
    want = male_tri_keys(nonchest)
    have = set()
    extra = 0
    allm = male_tri_keys()
    for t in f.tri.tolist():
        g = f2m[t]
        if (g >= 0).all():
            k = tuple(sorted(g.tolist()))
            have.add(k)
            if k not in allm:
                extra += 1
    miss = sorted(want - have)
    return len(miss), miss[:5], extra


def chest_topology_changed():
    """가슴 쉘 삼각형이 male 과 달라졌는가 (세분화/추가)."""
    m = models()[0]; L = parts()
    chest = L[m.tri[:, 0]] == "body:chest"
    have = set()
    f = full_female(); f2m, _ = correspondence()
    for t in f.tri.tolist():
        g = f2m[t]
        if (g >= 0).all():
            have.add(tuple(sorted(g.tolist())))
    return not male_tri_keys(chest) <= have or full_female().n_verts != m.n_verts


# --------------------------------------------------------------------------- 가슴과 이웃 쉘의 새 교차 (해상도 무관)
def chest_partner_sets(classes=("body:upper_arm", "joint:waist_band", "body:abdomen")):
    """가슴 쉘과 교차하는 '가슴이 아닌 쪽' 삼각형 집합. 가슴 삼각형은 세분화로 개수가 달라지지만
    상대 쪽(upper_arm/abdomen/waist_band)은 male 과 1:1 이므로 집합 차이로 '새로 교차하는 면'을 센다.
    반환 {클래스: (male 집합, female 집합)}"""
    a, b = intersection_sets()
    out = {c: (set(), set()) for c in classes}
    for k, pairs in enumerate((a, b)):
        for p in pairs:
            la, lb = tri_label(p[0]), tri_label(p[1])
            for me, other, tid in ((la, lb, p[1]), (lb, la, p[0])):
                if me == "body:chest":
                    for c in classes:
                        if other.startswith(c):
                            out[c][k].add(tid)
    return out


def abdomen_poke():
    """배 쉘 정점이 가슴 쉘 앞면 높이장보다 얼마나 앞(+z)으로 튀어나왔는가 [m] (male 은 음수 = 가슴 속에 있음).
    가슴 높이장이 덮는 (x,y) 안의 배 쉘 정점만 본다. 반환 (female 최대, male 최대, female 최악 정점 인덱스(full))."""
    import bust_metrics as bm
    res = []
    for which in ("male", "female"):
        if which == "male":
            m = models()[0]; pos, tri, L = m.pos, m.tri, parts(); tl = L[tri[:, 0]]
        else:
            f = full_female(); pos, tri, L = f.pos, f.tri, parts_full(); tl = tri_labels_full()
        Tc = pos[tri[tl == "body:chest"]]
        xs = np.arange(-0.22, 0.2201, bm.STEP); ys = np.arange(0.55 * height(models()[0]) * SCALE, 1.62 * SCALE, bm.STEP)
        Z = bm.heightfield(Tc, xs, ys)
        idx = np.where(L == "body:abdomen")[0]
        worst, wi = -1.0, -1
        for i in idx:
            z = bm.sample(Z, xs, ys, pos[i, 0], pos[i, 1])
            if np.isfinite(z) and pos[i, 2] - z > worst:
                worst, wi = pos[i, 2] - z, int(i)
        res.append((worst, wi))
    return res[1][0], res[0][0], res[1][1]


# --------------------------------------------------------------------------- 비율 v2: 엉덩이 폭 (줄자/캘리퍼 정의에 가깝게)
def hip_breadth(model, zone=(0.44, 0.56)):
    """서 있는 자세의 엉덩이 폭 근사: zone(키 비율, 기본 0.44H~0.56H: 둔부 최대 돌출~대전자 0.530H) 수평 단면에서
    골반 쉘+고관절 링+허벅지 쉘이 차지하는 x 폭의 최대값 [m]. 반환 (폭, 그 높이/H).
    zone 선택에 따라 값이 달라진다: 대전자 높이만(0.50~0.56H) 보면 female 폭이 더 좁게 나온다(보고서 참조)."""
    pos, tri, L = _source(model)
    keep = np.array([n == "body:pelvis" or n.startswith("joint:hip_joint") or n.startswith("body:thigh") for n in L])
    T = pos[tri[keep[tri[:, 0]]]]
    H = height(model)
    best = (0.0, None)
    for y in np.linspace(zone[0] * H, zone[1] * H, 49):
        P = section_points(T, np.array([0, 1.0, 0]), y)
        if len(P):
            w = float(np.ptp(P[:, 0]))
            if w > best[0]:
                best = (w, float(y / H))
    return best


def shoulder_breadth(model):
    """어깨 링(Joints) 바깥-바깥 x 폭 [m]. 이 마네킹에서 삼각근 폭과 견봉 폭 사이의 근사."""
    return proportions(model)["shoulder_width"]
