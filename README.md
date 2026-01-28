# ML-Tiles
Generate raster tiles for machine learning, sliced by layer if needed. Part of my bigger experiment
I use to study ML and GIS, "Finding place in the world by description or a freeform sketch".

Computational geometry methods, like finding an affine transformation that gives best Jaccard metric
for each tile are precise but slow - with some basic parallelization it takes several minutes to do
a full search for a city like Zurich and several hours for a region like canton Zurich.

The best way to make my project scale and still be suitable for a local run was to create an index,
so my script could quickly generate a list of search candidates and reduce number of tiles to check
from billions to thousands (which is an acceptable amount for the Affine/Jaccard search).

# Pipeline experiment

Here I'm trying to build a pipeline that takes an OSM file, slices it into tiles, transforms in many
ways and generates embedding vectors from it.

# Current status

So, streaming a database as a sequence of x/y/zoom tiles and distortion works ok, so I'm exploring
various ways of generating feature vectors for a set of gemetries:
1. Image moments or fourier descriptors. Not so robust, but invariant to some of the affine
transformations and I will need to generate less transformations.
2. Graph neural networks: should be better, but not as simple as image moments and requires more
research.


# Workflow
1. Convert osm.pbf to GeoParquet file
```bash
pip install quackosm[cli] # In your venv

quackosm data/osm/liechtenstein-latest.osm.pbf --output data/osm/liechtenstein-latest.parquet
quackosm data/osm/switzerland-latest.osm.pbf --output data/osm/switzerland-latest.parquet
```

2. Import files in the duckdb
```bash

duckdb data/osm/switzerland-latest.duckdb
INSTALL spatial; LOAD spatial;
CREATE TABLE osm AS SELECT * FROM read_parquet('data/osm/switzerland-latest.parquet');
CREATE INDEX idx_geometry ON osm USING RTREE (geometry);
SELECT feature_id, geometry FROM osm;

duckdb data/osm/liechtenstein-latest.duckdb
INSTALL spatial; LOAD spatial;
CREATE TABLE osm AS SELECT * FROM read_parquet('data/osm/liechtenstein-latest.parquet');
CREATE INDEX idx_geometry ON osm USING RTREE(geometry);
SELECT feature_id, geometry FROM osm;
```

3. Checking the database
```bash

duckdb data/osm/switzerland-latest.duckdb
INSTALL spatial; LOAD spatial;

-- Point at Zurich HB main building
SELECT * from osm WHERE ST_Contains(geometry, ST_Point( 8.54035340748125, 47.37793858438198));
```

4. Checking tile generation with the script (area around Zurich HB)
```bash
python ./pipeline/tilesource.py \
  --tile_size_km 1 \
  --bounds 47.38045731812224,8.535970015573549,47.37542289788745,8.544161611386535 \
  ./data/osm/switzerland-latest.duckdb ./tmp/dumptiles
```