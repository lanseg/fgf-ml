# Approach stauts

What works well:
* Generating ML-suitable tiles: high contrast, no text labels or POI icons, separate layers in separate images (buildings, transportation, water)
* Feeding hundreds thousands of tiles to the embedding generation with checkpoints, can work on CPU or GPU (CUDA)
* Fast lookup if the searched tile is not very different from an actual tile (e.g. when you have a piece of a real map and you need to find it's place)

What doesn't work (and I'm working on it now):
* Tile lookup when the searched tile contains only part of the features (e.g. only one building of multiple)
* User-drawn tile lookup (when the sketch is too distorted).

# The workflow

### Generating index:
1. Download protobuf data from the OpenStreetMap
2. TileMaker: filter only the relevant information and generate tile data from it
3. TileServer-gl: provide ML-suitable raster tiles for individual layers, e.g. buildings, roads, water and combined.
4. PyTorch, Transformers: generate embedding vectors from the images.
5. Faiss: store the embedding vectors.

### Searching within index:
1. PyTorch, Transformers: generate embedding vectors from the user input.
2. Faiss: find the most similar indices

# Running

1. ```make fetch_tiles``` to generate the tiles for the area of interest
2. ```cd scripts  && uv venv && uv sync``` to get fetch the dependencies and create a venv
3. ```source scripts/.venv/bin/activate``` to activate venv
4. ```python scripts/calc_embeddings``` to generate the index (region of interest is hardcoded)

I tried to organize scripts with a Makefile and python dependencies into the pyproject.toml, but there are still some binary dependencies: lua, libboost, rapidjson, etc. For Debian/Ubuntu based distros it could be done with this command (taken from ):
```bash
$ sudo apt install build-essential libboost-dev libboost-filesystem-dev libboost-program-options-dev libboost-system-dev lua5.1 liblua5.1-0-dev libshp-dev libsqlite3-dev rapidjson-dev
```
Source: [Tileserver native dependencies](https://maptiler-tileserver.readthedocs.io/en/latest/installation.html#npm)


1. ```make fetch_tiles``` to download the OSM data and generate PNGs for tiles.
2. ```python scripts/calc_embeddings.py``` to generate the index.
3. ```python scripts/find_tile.py``` to search in the index.

# Troubleshooting

* Nodejs shold be not very new because of the dependencies. To circumvent this, I had to install "n" package and explicitly define the node version:
```bash
$ npm install -g n
$ n exec 22 npm install -g tileserver-gl
```

* It wanted unicode library version 70, but mine was 75, so I had to download it manually and add to LD_LIBRARY_PATH.

```bash
$ wget https://github.com/unicode-org/icu/releases/download/release-70-1/icu4c-70_1-Ubuntu-20.04-x64.tgz
$ tar -xvf icu4c-70_1-Ubuntu-20.04-x64.tgz
$ LD_LIBRARY_PATH=$LD_LIBRARY_PATH:`pwd`/deps/icu/icu/usr/local/lib/ n exec 22 xvfb-run --server-args="-screen 0 1024x768x24" tileserver-gl --config data/config.json -b 127.0.0.1 -p 8081
```

# Other docs:
* [OSM Switzerland](https://download.geofabrik.de/europe/switzerland.html) - I used this as the main data source for my experiments.
* [TileMaker](https://github.com/systemed/tilemaker) - many distros already have it.
* [TileServer native dependencies](https://maptiler-tileserver.readthedocs.io/en/latest/installation.html#npm) - most distros don't have it, but you can find it on npm.

export N_PREFIX=`pwd`/data/npm
n 22 npm i
