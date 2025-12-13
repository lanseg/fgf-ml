data/switzerland-latest.osm.pbf:
	mkdir -p data
	wget https://download.geofabrik.de/europe/switzerland-latest.osm.pbf -O data/switzerland-latest.osm.pbf

data/switzerland-latest.mbtiles: data/switzerland-latest.osm.pbf
	docker run -it --rm -v ./data:/data ghcr.io/systemed/tilemaker:master \
	/data/switzerland-latest.osm.pbf \
	--store  /data \
	--output /data/switzerland-latest.mbtiles

tileserver-up: data/switzerland-latest.mbtiles
	docker run -d --rm -v ./data:/data -p 8080:8080 --name tileserver maptiler/tileserver-gl:latest --file switzerland-latest.mbtiles

tileserver-down:
	docker stop tileserver || true

.PHONY: fetch_tiles
fetch_tiles: tileserver-down tileserver-up
	mkdir -p data/tiles
	python scripts/fetch_tiles.py