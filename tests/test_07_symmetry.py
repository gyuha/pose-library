"""(g) 좌우 대칭. male 자체의 비대칭(원본 모델 오차)을 기준선으로 삼아, female 이 그보다 나빠지지 않았는지 본다."""
import numpy as np

from qa_metrics import asymmetry, mirror_map, models, vdesc


def test_mirror_correspondence_exists():
    m, _ = models()
    _, dist = mirror_map(m)
    assert dist.max() < 0.005, "male 에 x 거울 대응 정점이 없는 정점이 있음 (QA 전제 위반)"


def test_female_is_as_symmetric_as_male():
    m, f = models()
    mm, _ = mirror_map(m)
    am, af = asymmetry(m, mm), asymmetry(f, mm)
    assert af.max() <= am.max() + 2e-4, f"female 최대 비대칭 {af.max() * 1000:.2f} mm > male {am.max() * 1000:.2f} mm: {vdesc(int(af.argmax()))}"


def test_midline_vertices_stay_on_midline():
    m, f = models()
    mid = np.abs(m.pos[:, 0]) < 1e-6
    assert np.abs(f.pos[mid, 0]).max() < 1e-6, "정중선 정점이 x=0 에서 벗어남"
