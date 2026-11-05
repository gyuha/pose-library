"""측정 코드 검증용 합성 가슴 표면 (부피/돌출을 해석적으로 아는 곡면)."""
import numpy as np


def wall(x, y):
    return 0.03 + 0.25 * (1.42 - y) - 1.2 * x ** 2


def bump(x, y, p=0.07, cx=0.095, cy=1.265, rx=0.058, up=0.07, low=0.055, cone=False):
    """한쪽(|x| 기준) 유방 초과 높이. 위쪽 반경 up, 아래쪽 반경 low 인 물방울."""
    r_x = (np.abs(x) - cx) / rx
    r_y = np.where(y >= cy, (y - cy) / up, (cy - y) / low)
    rho = np.sqrt(r_x ** 2 + r_y ** 2)
    if cone:
        return p * np.clip(1 - rho, 0, None)
    return p * np.clip(1 - rho ** 2, 0, None) ** 1.5


def surface_triangles(**kw):
    """3 mm 격자 삼각형 메시 (m,3,3)."""
    xs = np.arange(-0.2, 0.2001, 0.003); ys = np.arange(1.0, 1.5001, 0.003)
    X, Y = np.meshgrid(xs, ys)
    Z = wall(X, Y) + (bump(X, Y, **kw) if kw.get("p", 1) else 0)
    P = np.stack([X, Y, Z], -1)
    a, b, c, d = P[:-1, :-1], P[:-1, 1:], P[1:, 1:], P[1:, :-1]
    return np.concatenate([np.stack([a, b, c], 2).reshape(-1, 3, 3), np.stack([a, c, d], 2).reshape(-1, 3, 3)])


def true_volume_cm3(**kw):
    xs = np.arange(0.0005, 0.2, 0.001); ys = np.arange(1.0005, 1.5, 0.001)
    X, Y = np.meshgrid(xs, ys)
    return float(bump(X, Y, **kw).sum() * 1e-6 * 1e6)
