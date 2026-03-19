# ML-Tiles
My experiment, "Finding place in the world by description or a freeform sketch".

Computational geometry methods, like finding an affine transformation that gives best Jaccard metric
for each tile are precise but slow - with some basic parallelization it takes several minutes to do
a full search for a city like Zurich and several hours for a region like canton Zurich.

The best way to make my project scale and still be suitable for a local run was to create an index,
so my script could quickly generate a list of search candidates and reduce number of tiles to check
from billions to thousands (which is an acceptable amount for the Affine/Jaccard search).

# Current status

I implemented a feature vector generation and the indexing, now I'm going to try vectorizing the user input and searching for the candidates in the database.

# Workflow

## Preparing the source data

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

## Building the vector index

The main idea is to generate multiple versions of each tile: deformed and distorted in many different ways (because sketches are expected to be imprecise), with only portion of the geometries (because I can't expect an user to draw all buildings in the area), etc.

So, for each tile there are several hundred vectors that represent different variants of the tile.

### Distortion and transformation

*TODO: Add note on making the polygons wobbly, shaky and somewhat similar to a man made drawing*

### Subset selection

*TODO: Add numbers and the reason for the subset selection*

1. Build a Delaunnay triangulation from the building centroids, the centroids are vertices and the triangle edges are the graph edges.
2. For each building/geometry take itself and the adjacent nodes.

### Vectorizing the geometries

1. Normalize the tile, scale it to fit into the square [-1, -1, 1, 1]. That's probably not needed at the current state, but any feature vector generation will be done for the normalized tile anyway.
2. Calculating Hu moments: Rasterize the tile and calculate the image moments.
3. Write those vectors with the tile id's into a faiss index.