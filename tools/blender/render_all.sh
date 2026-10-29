#!/usr/bin/env bash
# Renders every sprite source into $1 (default: tools/blender/out). Takes a few hours on a CPU.
# Usage: tools/blender/render_all.sh [out_dir] [wagon|bunker|silo|cbunker|csilo|b3|b1|e1 ...]
set -e
cd "$(dirname "$0")/../.."
BLENDER="${BLENDER:-/c/Program Files/Blender Foundation/Blender 5.2/blender.exe}"
OUT="${1:-tools/blender/out}"
shift || true
PARTS="${*:-bunker silo cbunker csilo e1 b3 b1 wagon}"
for part in $PARTS; do
  case "$part" in
    wagon) "$BLENDER" -b --factory-startup -P tools/blender/wagon_w1.py -- "$OUT/w1" ;;
    b3) "$BLENDER" -b --factory-startup -P tools/blender/station_b3.py -- "$OUT/b3" ;;
    b1) "$BLENDER" -b --factory-startup -P tools/blender/station_b1.py -- "$OUT/b1" ;;
    e1) "$BLENDER" -b --factory-startup -P tools/blender/station_e1.py -- "$OUT/e1" ;;
    bunker) "$BLENDER" -b --factory-startup -P tools/blender/station_bunker.py -- "$OUT/bunker" ;;
    silo) "$BLENDER" -b --factory-startup -P tools/blender/station_silo.py -- "$OUT/silo" ;;
    cbunker) "$BLENDER" -b --factory-startup -P tools/blender/connector_v2.py -- "$OUT/connector-bunker" bunker ;;
    csilo) "$BLENDER" -b --factory-startup -P tools/blender/connector_v2.py -- "$OUT/connector-silo" silo ;;
  esac
  echo "done: $part"
done
