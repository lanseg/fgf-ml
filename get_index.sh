#!/usr/bin/bash
set -euo pipefail
declare -A areas

# Lon/Lat
areas=(
    [adliswil_clamp]="8.516378,47.323814,8.52582,47.318083"
    [adliswil_main]="8.50676853608211,47.32310618106547,8.540886234658167,47.3016328575551"
    [zurich_center]="8.483505,47.360339,8.567791,47.399511"
    [zurich_eth]="8.567791,47.360339,8.483505,47.399511"
    [kanton_zurich]="8.2243,47.0394,9.0996,47.7394"
    [swiss]="5.4467010850356266,47.73248844856869,11.4152400783939,45.864502976445976"
    [regression_hongg]="8.476725,47.41367,8.486295,47.407731"
    [adliswil_home]="8.524897,47.315057,8.53097,47.311013"
)
requested_area="${1:-}"
if [[ -z "$requested_area" || ! -v areas[$requested_area] ]]; then
    echo "Available areas: ${!areas[@]}"
    exit 0
fi

bounds="${areas[$requested_area]}"
echo "Processing area: $requested_area, bounds: $bounds"

mkdir -p "./indices/$requested_area"
python index/main.py  \
    --tile_size_km 0.2   \
    --border_size_km 0.1 \
    --bounds $bounds \
    data/osm/switzerland-latest.duckdb \
    ./indices/$requested_area 2>&1 | tee "./indices/$requested_area.log"
