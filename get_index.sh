#!/usr/bin/bash
set -euo pipefail
declare -A areas

areas=(
    [adliswil_clamp]="47.323814,8.516378,47.318083,8.52582"
    [adliswil_main]="47.32310618106547,8.50676853608211,47.3016328575551,8.540886234658167"
    [zurich_center]="47.360339,8.483505,47.399511,8.567791"
    [zurich_eth]="47.360339,8.567791,47.399511,8.483505"
    [kanton_zurich]="47.0394,8.2243,47.7394,9.0996"
    [swiss]="47.73248844856869,5.4467010850356266,45.864502976445976,11.4152400783939"
)
requested_area="${1:-}"
if [[ -z "$requested_area" || ! -v areas[$requested_area] ]]; then
    echo "Available areas: ${!areas[@]}"
    exit 0
fi

bounds="${areas[$requested_area]}"
echo "Processing area: $requested_area, bounds: $bounds"

python pipeline/main.py  \
    --tile_size_km 0.5   \
    --border_size_km 0.2 \
    --bounds $bounds \
    data/osm/switzerland-latest.duckdb \
    ./indices/$requested_area.faiss 2>&1 | tee "indices/$requested_area.log"
