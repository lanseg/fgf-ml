# Tools that either don't work well or not available from the distro repositories
deps/tilemaker:
	mkdir -p deps
	git clone https://github.com/systemed/tilemaker deps/tilemaker

deps/tilemaker/tilemaker: deps/tilemaker
	cd deps/tilemaker && $(MAKE)


# Geodata fetching and preparing
data/switzerland-latest.osm.pbf:
	mkdir -p data
	wget https://download.geofabrik.de/europe/switzerland-latest.osm.pbf -O data/switzerland-latest.osm.pbf

data/switzerland-latest.mbtiles: data/switzerland-latest.osm.pbf deps/tilemaker/tilemaker
	deps/tilemaker/tilemaker \
	  --store data/ \
	  --config configs/tilemaker-essential.json \
	  --process configs/tilemaker-essential.lua \
	  --input data/switzerland-latest.osm.pbf \
	  --output data/switzerland-latest.mbtiles

# Utility services
tileserver-up: data/switzerland-latest.mbtiles
	docker run -d --rm -v ./data:/data -p 8080:8080 --name tileserver maptiler/tileserver-gl:latest --file switzerland-latest.mbtiles

tileserver-down:
	docker stop tileserver || true

.PHONY: fetch_tiles
fetch_tiles: tileserver-down tileserver-up
	mkdir -p data/tiles
	python scripts/fetch_tiles.py