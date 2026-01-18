# ML-Tiles
Generate raster tiles for machine learning, sliced by layer if needed. Part of my bigger experiment
I use to study ML and GIS, "Finding place in the world by description or a freeform sketch".

Computational geometry methods, like finding an affine transformation that gives best Jaccard metric
for each tile are precise but slow - with some basic parallelization it takes several minutes to do
a full search for a city like Zurich and several hours for a region like canton Zurich.

The best way to make my project scale and still be suitable for a local run was to create an index,
so my script could quickly generate a list of search candidates and reduce number of tiles to check
from billions to thousands (which is an acceptable amount for the Affine/Jaccard search).

# Approaches

1. Feature vectors from tile raster images using existing models (dinov2-base), see [scripts/README.md](scripts/readme.MD)
2. Custom feature vectors based on OSM geometries, see
[pipeline/README.md](pipeline/README.md)
