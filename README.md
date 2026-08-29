# ML-Tiles
My prototype/experiment, "Finding place in the world by description or a freeform sketch".

Computational geometry methods, like finding an affine transformation that gives best Jaccard metric
for each tile are precise but slow - with some basic parallelization it takes several minutes to do
a full search for a city like Zurich and several hours for a region like canton Zurich.

The best way to make my project scale and still be suitable for a local run was to create an index,
so my script could quickly generate a list of search candidates and reduce number of tiles to check
from billions to thousands (which is an acceptable amount for the Affine/Jaccard search).

# Current status

It can build FAISS index for a given area and then search for a given vector drawing in this index.
* I split index into multiple files so it can fit into memory
* I use GeoJSON in the search query only for ease of experimentation, so I can draw in a GIS tool
and paste the drawing in the search query.

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
python index/main.py  \
    --tile_size_km 1 \
    --bounds 47.0394,8.2243,47.7394,9.0996 \
    data/osm/switzerland-latest.duckdb \
    ./indices/kanton_zurich
```

There is a convenience script with some of the locations with their bounds: [get_index.sh](get_index.sh)

## Performing the search
Geojson is used only for ease of testing, so I could select some buildings on a WKT editor and see
if the finder will be able to find the tile.

```bash
python index/find.py \
    ./indices/kanton_zurich \
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
4. Generate embedding vectors using some pytorch model
5. Save tile vector to the FAISS index and tile coordinates to a list

## Approach history

1. Computational geometry only: apply affine transformations to the query drawing, place it on a
tile and calculate intersection-to-union ratio, make it as close to 1 as possible using
scipy.optimize. Quite precise and robust, but takes almost an hour for a city like Zurich. *I'm going
to use to refine the results I got from the index.*
2. Indexing using custom feature vectors based on image invariants - unpredictable quality and too
much of fine-tuning and picking the right set of metrics.


