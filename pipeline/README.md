# Pipeline experiment

Here I'm trying to build a pipeline that takes an OSM file, slices it into tiles, transforms in many
ways and generates embedding vectors from it.

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