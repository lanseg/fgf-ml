# MLNOTES
1. Get OSM data for Switzerland from https://download.geofabrik.de/europe/switzerland.html
2. TileMaker     from https://github.com/systemed/tilemaker
3. TileServer-gl from https://github.com/maptiler/tileserver-gl
4. docker run --rm -it -v ./data:/data -p 8080:8080 maptiler/tileserver-gl:latest --file switzerland-latest.mbtiles

# The workflow
1. Download protobuf data from the OpenStreetMap
2. Filter only the relevant information generate tile data from it
3. Serve tile data separated by different layers, e.g. buildings, roads, water
4. Generate tiles

sudo apt install build-essential libboost-dev libboost-filesystem-dev libboost-program-options-dev libboost-system-dev libshp-dev libsqlite3-dev rapidjson-dev