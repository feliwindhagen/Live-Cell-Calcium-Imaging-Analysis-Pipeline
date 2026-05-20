#!/usr/bin/env bash
set -euo pipefail

CP_BIN="${CP_BIN:-}"
PYTHON_BIN="${PYTHON_BIN:-python}"
PIPELINE="${PIPELINE:-pipeline/cellprofiler/calcium_imaging_pipeline_NPC.cpproj}"

RAW_BASE="demo/images"
CP_OUT="demo/cellprofiler_outputs"
PY_OUT="demo/outputs"
CONFIG="pipeline/analysis/configs/config_demo.yaml"

mkdir -p "$CP_OUT"
mkdir -p "$PY_OUT"

echo "=== Running CellProfiler on demo data ==="
./pipeline/preprocessing/run_cellprofiler_batch.sh \
  --base "$RAW_BASE" \
  --pipeline "$PIPELINE" \
  --out "$CP_OUT" \
  --glob "*"

echo "=== Running Python analysis ==="
$PYTHON_BIN pipeline/analysis/run_analysis.py \
  --config "$CONFIG" \
  --outdir "$PY_OUT"

echo "=== Done ==="
echo "CellProfiler outputs: $CP_OUT"
echo "Python outputs: $PY_OUT"
