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
