# Geodata fetching and preparing
data/osm/switzerland-latest.osm.pbf:
	mkdir -p data/osm
	wget https://download.geofabrik.de/europe/switzerland-latest.osm.pbf -P data/osm

data/osm/liechtenstein-latest.osm.pbf:
	mkdir -p data/osm
	wget https://download.geofabrik.de/europe/liechtenstein-latest.osm.pbf -P data/osm

data/osm/liechtenstein-latest.parquet: data/osm/liechtenstein-latest.osm.pbf
	quackosm data/osm/liechtenstein-latest.osm.pbf --output data/osm/liechtenstein-latest.parquet

data/osm/switzerland-latest.parquet: data/osm/switzerland-latest.osm.pbf
	quackosm data/osm/switzerland-latest.osm.pbf --output data/osm/switzerland-latest.parquet

data/osm/switzerland-latest.duckdb: data/osm/switzerland-latest.parquet
	duckdb data/osm/switzerland-latest.duckdb -c " \
	INSTALL spatial; LOAD spatial; \
	CREATE TABLE osm AS SELECT * FROM read_parquet('data/osm/switzerland-latest.parquet'); \
	CREATE INDEX idx_geometry ON osm USING RTREE (geometry); \
	"

data/osm/liechtenstein-latest.duckdb: data/osm/liechtenstein-latest.parquet
	duckdb data/osm/liechtenstein-latest.duckdb -c " \
	INSTALL spatial; LOAD spatial; \
	CREATE TABLE osm AS SELECT * FROM read_parquet('data/osm/liechtenstein-latest.parquet'); \
	CREATE INDEX idx_geometry ON osm USING RTREE (geometry); \
	"