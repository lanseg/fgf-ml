# MLNOTES
1. Get OSM data for Switzerland from https://download.geofabrik.de/europe/switzerland.html
2. TileMaker     from https://github.com/systemed/tilemaker
3. TileServer-gl from https://github.com/maptiler/tileserver-gl
4. docker run --rm -it -v ./data:/data -p 8080:8080 maptiler/tileserver-gl:latest --file switzerland-latest.mbtiles

