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

```bash
# Build an index for canton Zurich (approximately, includes neighbouring cantons too)
python pipeline/main.py  \
    --tile_size_km 1 \
    --bounds 47.0394,8.2243,47.7394,9.0996 \
    data/osm/switzerland-latest.duckdb \
    ./indices/kanton_zurich.faiss
```

## Performing the search
Geojson is used only for ease of testing, so I could select some buildings on a WKT editor and see
if the finder will be able to find the tile.

```bash
python pipeline/find.py \
    ./indices/kanton_zurich.faiss \
    "SOME_GEOJSON"
```

You will get a list of candidate tiles and the GEOMETRYCOLLECTION with all of them in WKT format for
debugging and validation.

# Implementation details

The main idea is to generate augmented versions for each tile: deformed and distorted in many different ways (because sketches are expected to be imprecise), with only portion of the geometries (because I can't expect an user to draw all buildings in the area), etc.

The whole process looks like this:
1. Stream OSM data as square tiles with fixed side
2. Slice each tile by object type: buildings, ways, etc.
3. Augmentation (generate extra tiles, while preserving the original one):
    1. Merge buildings that share the walls (unary_union)
    1. Apply distortion: make tiles wobbly and more man-made looking
    1. Generate various subsets of the tile
4. Vectorize the tile (scale to [-1, -1, 1, 1] and calculate Hu moments)
5. Save tile vector to the FAISS index and tile coordinates to a list
