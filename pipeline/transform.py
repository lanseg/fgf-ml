import numpy as np
from shapely import bounds
from shapely import Geometry
from shapely.affinity import affine_transform
from collections import namedtuple

TransformConfig = namedtuple("TransformConfig", ["dx", "dy", "a", "kx", "ky", "mx", "my"])


def mtotr(m):
    return [m[0, 0], m[0, 1], m[1, 0], m[1, 1], m[0, 2], m[1, 2]]


def translate(dx, dy):
    return np.matrix([[1, 0, dx], [0, 1, dy], [0, 0, 1]])


def rotate(t):
    return np.matrix([[np.cos(t), -np.sin(t), 0], [np.sin(t), np.cos(t), 0], [0, 0, 1]])


def scale(kx, ky):
    return np.matrix([[kx, 0, 0], [0, ky, 0], [0, 0, 1]])


def mirror(kx, ky):
    kx = -1 if kx < 0 else 1
    ky = -1 if ky < 0 else 1
    return np.matrix([[kx, 0, 0], [0, ky, 0], [0, 0, 1]])


def apply(g: Geometry, tc: list[np.matrix]):
    if not tc:
        return g
    cg = g.centroid.xy
    m = translate(cg[0][0], cg[1][0])
    for tm in tc:
        m *= tm
    m *= translate(-cg[0][0], -cg[1][0])
    return affine_transform(g, mtotr(m))


def fit(g: Geometry, target: tuple[float, float, float, float]) -> Geometry:
    src = bounds(g)
    m = (
        translate(target[0], target[1])
        * scale(
            (target[2] - target[0]) / (src[2] - src[0]),
            (target[3] - target[1]) / (src[3] - src[1]),
        )
        * translate(-src[0], -src[1])
    )
    return affine_transform(g, mtotr(m))


def variants(g: Geometry) -> list[Geometry]:
    angles = [np.pi / 20, np.pi / 10, -np.pi / 10, np.pi / 2, -np.pi / 2]
    scales = [(0.75, 0.75), (0.75, 1), (1, 0.75), (1.25, 1), (1, 1.25)]
    reflects = [(-1, 1), (1, -1), (-1, -1)]
    result = []
    for r in reflects:
        for s in scales:
            for a in angles:
                result.append(apply(g, [rotate(a), scale(s[0], s[1]), mirror(r[0], r[1])]))
    return result
