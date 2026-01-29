import numpy as np
from collections.abc import Generator
from shapely import Geometry
from shapely.geometry import (
    GeometryCollection,
    Polygon,
    LinearRing,
)

from scipy.ndimage import gaussian_filter1d
from noise import pnoise1



def diagBbox(points):
    return np.hypot(
        points[:, 0].max() - points[:, 0].min(), points[:, 1].max() - points[:, 1].min()
    )


def resample(ring: LinearRing, n_points: int = 200) -> np.ndarray:
    """Return an (N,2) array of points uniformly sampled along the ring."""
    distances = np.linspace(0, ring.length, n_points, endpoint=False)
    xs, ys = ring.xy
    coords = np.column_stack([xs, ys])
    line = LinearRing(coords)
    sampled = np.array([line.interpolate(d).coords[0] for d in distances])
    return sampled


def jitter(points: np.ndarray, scale: float = 0.005, rng: np.random.Generator = None) -> np.ndarray:
    """Randomly shift each point."""
    if rng is None:
        rng = np.random.default_rng()
    jitter = rng.normal(scale=scale * diagBbox(points), size=points.shape)
    return points + jitter


def wobble(
    points: np.ndarray, amplitude: float = 0.003, frequency: float = 2.0, seed: int = 0
) -> np.ndarray:
    """
    Add a smooth sinusoidal/perlin displacement orthogonal to the edge direction.
    `amplitude` is a fraction of the bbox diagonal (like jitter).
    `frequency` controls how many wiggles appear per unit length.
    """
    rng = np.random.default_rng(seed)
    diag = diagBbox(points)

    result = points.copy()
    n = len(points)
    for i in range(n):
        edge = points[(i + 1) % n] - points[i]
        length = np.linalg.norm(edge)
        if length == 0:
            continue
        # unit normal (rotate edge 90° CCW)
        normal = np.array([-edge[1], edge[0]]) / length

        # generate a perlin value for this segment
        t = rng.random() * 10_000  # random offset
        noise_val = pnoise1(t, repeat=1024)  # returns [-1,1]
        offset = amplitude * diag * noise_val

        # displace both end points orthogonally (smoothness comes from the fact
        # neighboring segments share points)
        result[i] += normal * offset
        result[(i + 1) % n] += normal * offset
    return result


def smooth(points: np.ndarray, sigma: float = 1.0) -> np.ndarray:
    """Apply a 1‑D Gaussian filter separately to x and y coordinates."""
    xs = gaussian_filter1d(points[:, 0], sigma=sigma, mode="wrap")
    ys = gaussian_filter1d(points[:, 1], sigma=sigma, mode="wrap")
    return np.column_stack([xs, ys])


def distort(
    poly: Polygon,
    n_resample: int = 50,
    jitter_scale: float = 0.008,
    wobble_amp: float = 0.003,
    wobble_freq: float = 2.0,
    smooth_sigma: float = 0.8,
    rng: np.random.Generator = None,
) -> Polygon:
    """
    Transform `poly` into a sketch‑like version.
    Returns a new Shapely Polygon (may be slightly self‑intersecting;
    we clean it with a small buffer(0) trick).
    """
    if rng is None:
        rng = np.random.default_rng()
    pts = resample(poly.exterior, n_resample)
    pts = jitter(pts, scale=jitter_scale, rng=rng)
    pts = wobble(
        pts, amplitude=wobble_amp, frequency=wobble_freq, seed=int(rng.integers(0, 1_000_000))
    )
    pts = smooth(pts, sigma=smooth_sigma)
    hand_poly = Polygon(pts).buffer(0)
    return hand_poly


def variants(geoms: list[Geometry]) -> Generator[Geometry]:
    for g in geoms:
        if isinstance(g, Polygon):
            yield distort(g)
        else:
            yield GeometryCollection([g])
