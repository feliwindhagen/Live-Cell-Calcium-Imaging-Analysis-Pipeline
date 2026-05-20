#!/usr/bin/env bash
set -euo pipefail

###############################################################################
# run_cellprofiler_batch.sh
#
# Batch-run CellProfiler on multiple experiments, one after another.
#
# This script is agnostic to cell type (NPC / Fib). You select the pipeline
# file explicitly via --pipeline.
#
# Default behavior is conservative and GitHub-friendly:
#   - experiments are run sequentially
#   - output folders have stable names (no timestamps)
#   - existing outputs are skipped
#
# Typical experiment folder naming expected:
#   YYYYMMDD_mt_er_CaTrigger_<CELL_LINE>[_rep]
#   YYYYMMDD_mt_cyt_CaTrigger_<CELL_LINE>[_rep]
#
###############################################################################

usage() {
  cat <<'EOF'
Usage:
  run_cellprofiler_batch.sh --base <input_root> --pipeline <pipeline.cpproj|cppipe> --out <output_root> [options]

Required arguments:
  --base        Folder containing experiment subfolders (inputs)
  --pipeline    CellProfiler pipeline (.cpproj or .cppipe)
  --out         Output root folder (one subfolder per experiment)

Optional arguments:
  --glob        Which subfolders count as experiments
                (default: "*_CaTrigger_*")
  --cp          Path to CellProfiler executable (auto-detected by default)
  --skip        Skip experiments if output folder already exists (yes|no, default: yes)
  --dry-run     Print commands without running CellProfiler
  -h, --help    Show this help message

Examples:
  NPC ER:
    ./pipeline/preprocessing/run_cellprofiler_batch.sh \
      --base "/data/cellprofiler_inputs" \
      --pipeline "pipeline/cellprofiler/calcium_imaging_pipeline_NPC.cpproj" \
      --out "/data/cellprofiler_outputs" \
      --glob "*_mt_er_CaTrigger_*"

  Fib:
    ./pipeline/preprocessing/run_cellprofiler_batch.sh \
      --base "/data/cellprofiler_inputs" \
      --pipeline "pipeline/cellprofiler/calcium_imaging_pipeline_Fib.cpproj" \
      --out "/data/cellprofiler_outputs"
EOF
}

# ------------------------
# Defaults (safe + robust)
# ------------------------
EXPERIMENT_GLOB="*_CaTrigger_*"
SKIP_IF_EXISTS="yes"
DRY_RUN="no"
CP_BIN=""

BASE=""
PIPELINE=""
OUT_ROOT=""

# ------------------------
# Parse arguments
# ------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --base) BASE="$2"; shift 2;;
    --pipeline) PIPELINE="$2"; shift 2;;
    --out) OUT_ROOT="$2"; shift 2;;
    --glob) EXPERIMENT_GLOB="$2"; shift 2;;
    --cp) CP_BIN="$2"; shift 2;;
    --skip) SKIP_IF_EXISTS="$2"; shift 2;;
    --dry-run) DRY_RUN="yes"; shift 1;;
    -h|--help) usage; exit 0;;
    *) echo "ERROR: Unknown argument: $1" >&2; usage; exit 2;;
  esac
done

# ------------------------
# Validate inputs
# ------------------------
[[ -n "$BASE" && -n "$PIPELINE" && -n "$OUT_ROOT" ]] || {
  echo "ERROR: --base, --pipeline, and --out are required." >&2
  usage
  exit 2
}

[[ -d "$BASE" ]] || { echo "ERROR: Input base folder not found: $BASE" >&2; exit 1; }
[[ -f "$PIPELINE" ]] || { echo "ERROR: Pipeline not found: $PIPELINE" >&2; exit 1; }
mkdir -p "$OUT_ROOT"

# ------------------------
# Find CellProfiler binary
# ------------------------
if [[ -z "$CP_BIN" ]]; then
  if [[ -x "/Applications/CellProfiler.app/Contents/MacOS/cp" ]]; then
    CP_BIN="/Applications/CellProfiler.app/Contents/MacOS/cp"
  elif command -v cellprofiler >/dev/null 2>&1; then
    CP_BIN="$(command -v cellprofiler)"
  else
    echo "ERROR: Could not find CellProfiler executable." >&2
    echo "Provide it explicitly via --cp" >&2
    exit 1
  fi
fi

[[ -x "$CP_BIN" ]] || { echo "ERROR: CellProfiler binary not executable: $CP_BIN" >&2; exit 1; }

# ------------------------
# Find experiments
# ------------------------
shopt -s nullglob
EXPERIMENTS=( "$BASE"/$EXPERIMENT_GLOB )

if [[ ${#EXPERIMENTS[@]} -eq 0 ]]; then
  echo "ERROR: No experiment folders found matching:"
  echo "  $BASE/$EXPERIMENT_GLOB"
  exit 1
fi

echo "CellProfiler executable : $CP_BIN"
echo "Pipeline               : $PIPELINE"
echo "Input base              : $BASE"
echo "Output base             : $OUT_ROOT"
echo "Experiment glob         : $EXPERIMENT_GLOB"
echo "Experiments found       : ${#EXPERIMENTS[@]}"
echo

# ------------------------
# Run experiments (SEQUENTIAL)
# ------------------------
i=1
for EXP_PATH in "${EXPERIMENTS[@]}"; do
  [[ -d "$EXP_PATH" ]] || continue

  EXP_NAME="$(basename "$EXP_PATH")"
  OUT_DIR="$OUT_ROOT/$EXP_NAME"

  echo "[$i/${#EXPERIMENTS[@]}] Running experiment: $EXP_NAME"
  echo "  INPUT : $EXP_PATH"
  echo "  OUTPUT: $OUT_DIR"

  if [[ "$SKIP_IF_EXISTS" == "yes" && -d "$OUT_DIR" ]]; then
    echo "  SKIP: Output already exists"
    echo
    ((i++))
    continue
  fi

  if [[ "$DRY_RUN" == "yes" ]]; then
    echo "  (dry-run)"
    echo "  $CP_BIN -c -r -p \"$PIPELINE\" -i \"$EXP_PATH\" -o \"$OUT_DIR\""
    echo
    ((i++))
    continue
  fi

  mkdir -p "$OUT_DIR"
  "$CP_BIN" -c -r -p "$PIPELINE" -i "$EXP_PATH" -o "$OUT_DIR"

  echo "  DONE"
  echo
  ((i++))
done

echo "All experiments finished."
