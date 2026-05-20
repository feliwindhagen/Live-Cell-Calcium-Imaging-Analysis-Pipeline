#!/usr/bin/env bash
set -euo pipefail

CP_BIN="${CP_BIN:-}"
PYTHON_BIN="${PYTHON_BIN:-python}"
PIPELINE="${PIPELINE:-pipelines/projects/Ca2_Trigger_pipeline_NPC.cpproj}"

RAW_BASE="demo/raw_inputs"
CP_OUT="demo/cellprofiler_outputs"
PY_OUT="demo/demo_outputs"
CONFIG="configs/config_demo.yaml"

mkdir -p "$CP_OUT"
mkdir -p "$PY_OUT"

echo "=== Running CellProfiler on demo data ==="
./scripts/run_cellprofiler_batch.sh \
  --base "$RAW_BASE" \
  --pipeline "$PIPELINE" \
  --out "$CP_OUT" \
  --glob "*"

echo "=== Running Python analysis ==="
PYTHONPATH=./src/ca_trigger $PYTHON_BIN cli/run_analysis.py \
  --config "$CONFIG" \
  --outdir "$PY_OUT"

echo "=== Done ==="
echo "CellProfiler outputs: $CP_OUT"
echo "Python outputs: $PY_OUT"
