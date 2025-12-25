N_PREFIX=$(PWD)/data/npm
TILESERVER_HOST=127.0.0.1
TILESERVER_PORT=8081
TILESERVER="http://$(TILESERVER_HOST):$(TILESERVER_PORT)"

# Tools that either don't work well or not available from the distro repositories
deps/tilemaker:
	mkdir -p deps
	git clone https://github.com/systemed/tilemaker deps/tilemaker

deps/tilemaker/tilemaker: deps/tilemaker
	cd deps/tilemaker && $(MAKE)

deps/tileserver-gl:
	mkdir -p deps
	git clone https://github.com/maptiler/tileserver-gl deps/tileserver-gl

# Geodata fetching and preparing
data/osm/switzerland-latest.osm.pbf:
	mkdir -p data/osm
	wget https://download.geofabrik.de/europe/switzerland-latest.osm.pbf -P data/osm

data/tiles/switzerland-latest.mbtiles: data/osm/switzerland-latest.osm.pbf deps/tilemaker/tilemaker
	mkdir -p data/tiles
	deps/tilemaker/tilemaker \
	  --store data/tiles \
	  --config configs/tilemaker-config.json \
	  --process configs/tilemaker-process.lua \
	  --input data/osm/switzerland-latest.osm.pbf \
	  --output data/osm/switzerland-latest.mbtiles

# Utility services
tileserver-up: data/tiles/switzerland-latest.mbtiles
	cd deps/tileserver-gl && n 22 exec npm i && \
	n exec 22 xvfb-run --server-args="-screen 0 1024x768x24" \
	  node . --config ../../configs/tileserver.json -b $(TILESERVER_HOST) -p $(TILESERVER_PORT) & \
	echo "$$!" > tileserver.pid

tileserver-down:
	pkill -P `cat tileserver.pid` || true
	if [ -f tileserver.pid ]; then rm tileserver.pid; fi

.PHONY: fetch_tiles
fetch_tiles: tileserver-down tileserver-up
	mkdir -p data/tiles
	python scripts/fetch_tiles.py