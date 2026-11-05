"""(c) 변형의 국소 매끄러움. 모든 기준은 'male 대비 변화량'이라 원본 모델 고유의 각진 형상은 걸러진다.

기준값(휴리스틱, 근거):
 - 모서리 신축비: 균일 스케일(0.925)을 1.0 으로 정규화. 면 구조를 유지하는 모프에서 국소 ±50% 초과 신축은 면이 눈에 띄게 찌그러진다.
 - 이웃 평균 대비 법선 방향 돌출 변화: 15 mm. 전신 1.76 m 기준 모델에서 15 mm 이상의 한 정점 단위 변화는 실루엣/음영에서 '뾰족함/패임'으로 보인다.
 - 가슴 중앙 홈 깊이: 20 mm.
 - 저장 NORMAL 과 기하 면 법선의 각도: male 에서 정합했던 삼각형이 female 에서 15° 넘게 틀어지면 음영이 어긋난다.
"""
import collections

import numpy as np

from qa_metrics import (chest_groove, edge_strain, face_normal_rotation, group_of, label_of_welded, members, models,
                        parts, tri_dev_from_normals, umbrella_delta, vdesc)


def _summary(items):
    c = collections.Counter(group_of(l) for l in items)
    return ", ".join(f"{k}:{v}" for k, v in c.most_common())


def test_edge_stretch_is_bounded():
    E, ratio, M, F = edge_strain()
    lab = label_of_welded()
    bad = np.where((ratio < 0.65) | (ratio > 1.50))[0]
    worst = np.argsort(np.abs(np.log(ratio)))[::-1][:4]
    detail = "; ".join(f"{lab[E[k, 0]]} ratio={ratio[k]:.2f} male({M[E[k, 0]][0]:.3f},{M[E[k, 0]][1]:.3f},{M[E[k, 0]][2]:.3f})" for k in worst)
    assert len(bad) == 0, f"신축비 [0.65,1.50] 밖 모서리 {len(bad)}개 ({_summary(lab[E[bad, 0]])}). 최악: {detail}"


def test_no_new_spike_or_dent():
    dn, M, F = umbrella_delta()
    lab = label_of_welded()
    bad = np.where(np.abs(dn) > 0.015)[0]
    top = bad[np.argsort(-np.abs(dn[bad]))][:8]
    detail = "; ".join(f"{dn[i] * 1000:+.0f}mm {lab[i]} {vdesc(members(i)[0])}" for i in top)
    assert len(bad) == 0, f"|돌출변화|>15mm 정점 {len(bad)}개 ({_summary(lab[bad])}). 상위: {detail}"


def test_chest_has_no_central_groove():
    depth, y, k = chest_groove(models()[1])
    mdepth, _, _ = chest_groove(models()[0])
    assert depth <= 0.02, (f"가슴 중앙 홈 깊이 {depth * 1000:.0f} mm (male {mdepth * 1000:.0f} mm), male 높이 y={y}, "
                           f"돌출 정점 {vdesc(k) if k is not None else '-'}")


def test_stored_normals_stay_consistent_with_geometry():
    m, f = models()
    dm, df = tri_dev_from_normals(m), tri_dev_from_normals(f)
    bad = np.where((dm < 5) & (df > 15))[0]
    top = bad[np.argsort(-df[bad])][:5]
    detail = "; ".join(f"{df[t]:.0f}° {parts()[f.tri[t, 0]]} {vdesc(f.tri[t, 0])}" for t in top)
    assert len(bad) == 0, f"male 에서 정합(<5°)이던 삼각형 {len(bad)}개가 female 에서 >15° 어긋남 ({_summary(parts()[f.tri[bad, 0]])}). 상위: {detail}"


def test_face_orientation_change_is_moderate():
    m, f = models()
    rot = face_normal_rotation(m, f)
    bad = np.where(rot > 30)[0]
    top = bad[np.argsort(-rot[bad])][:6]
    detail = "; ".join(f"{rot[t]:.0f}° {vdesc(f.tri[t, 0])}" for t in top)
    assert len(bad) == 0, f"면 법선이 male 대비 30° 초과 회전한 삼각형 {len(bad)}개 ({_summary(parts()[f.tri[bad, 0]])}). 상위: {detail}"
