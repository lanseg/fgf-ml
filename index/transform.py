from collections import namedtuple
from collections.abc import Generator

import numpy as np
import numpy.typing as npt
from shapely import Geometry, GeometryCollection, bounds
from shapely.affinity import affine_transform

TransformConfig = namedtuple("TransformConfig", ["dx", "dy", "a", "kx", "ky", "mx", "my"])


def mtotr(m):
    return [m[0, 0], m[0, 1], m[1, 0], m[1, 1], m[0, 2], m[1, 2]]


def translate(dx, dy):
    return np.array([[1, 0, dx], [0, 1, dy], [0, 0, 1]])


def rotate(t):
    return np.array([[np.cos(t), -np.sin(t), 0], [np.sin(t), np.cos(t), 0], [0, 0, 1]])


def scale(kx, ky):
    return np.array([[kx, 0, 0], [0, ky, 0], [0, 0, 1]])


def mirror(kx, ky):
    kx = -1 if kx < 0 else 1
    ky = -1 if ky < 0 else 1
    return np.array([[kx, 0, 0], [0, ky, 0], [0, 0, 1]])


def apply(g: Geometry, tc: list[npt.NDArray[np.float64]]) -> Geometry:
    if not tc:
        return g
    cg = g.centroid.xy
    m = translate(cg[0][0], cg[1][0])
    for tm in tc:
        m = m @ tm
    m = m @ translate(-cg[0][0], -cg[1][0])
    return affine_transform(g, mtotr(m))


def fit(
    g: Geometry, target: tuple[float, float, float, float], keep_aspect: bool = False
) -> Geometry:
    src = bounds(g)
    kx = (target[2] - target[0]) / (src[2] - src[0])
    ky = (target[3] - target[1]) / (src[3] - src[1])
    if keep_aspect:
        k = min(kx, ky)
        kx = k
        ky = k
    m = translate(target[0], target[1]) @ scale(kx, ky) @ translate(-src[0], -src[1])
    return affine_transform(g, mtotr(m))


def normalize(g: Geometry) -> Geometry:
    return fit(g, (0, 0, 1, 1))
