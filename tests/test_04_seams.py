"""(d) Body-Joints 분절 이음매. Joints 링은 설계상 Body 쉘 속에 일부 박힌 플러그이므로 '절대 관통'이 아니라
male 대비 거리 변화(틈이 벌어짐 / 더 깊이 박힘)를 측정한다.
기준: 틈 증가 3 mm, 관통 증가 10 mm (전신 1.76 m 기준, 렌더에서 눈에 띄는 최소 단차)."""
import pytest

from qa_metrics import seam_drift, seam_pairs

PAIRS = seam_pairs()


@pytest.mark.parametrize("J,B", PAIRS, ids=[f"{j.split(':')[1]}|{b.split(':')[1]}" for j, b in PAIRS])
def test_seam_does_not_open_or_sink(J, B):
    r = seam_drift(J, B)
    if r is None:
        pytest.skip("male 에서 접촉(25 mm 이내) 정점 없음")
    assert r["max_gap_growth"] <= 0.003, f"{r['seam']} 틈 {r['max_gap_growth'] * 1000:.1f} mm 증가 (정점 v{r['gap_vertex']})"
    assert r["max_closing"] <= 0.010, f"{r['seam']} 관통 {r['max_closing'] * 1000:.1f} mm 증가 (정점 v{r['closing_vertex']})"
