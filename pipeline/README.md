# Full Analysis Pipeline

This folder contains the complete toolkit for analysing multi-experiment, multi-cell-line Ca²⁺ trigger imaging data.

For a quick-start example on one experiment, see [`../demo/`](../demo/) first.

---

## Folder structure

```
pipeline/
├── cellprofiler/                 CellProfiler pipelines
│   ├── Ca2_Trigger_pipeline_NPC.cpproj    NPC / neural progenitor cells
│   ├── Ca2_Trigger_pipeline_Fib.cpproj    Fibroblasts
│   └── Quality_Control_Pipeline.cpproj   QC overlays
│
├── preprocessing/                Optional helper scripts
│   ├── export_lif_to_sequences.ijm        Fiji macro: .lif → TIFF stacks
│   └── run_cellprofiler_batch.sh          Batch-run CellProfiler on many experiments
│
└── python/                       Python analysis package
    ├── src/ca_trigger/
    │   ├── analysis_core.py               Core analysis logic
    │   └── figures.py                     Plotting functions
    ├── run_analysis.py                    Entry point (config-driven CLI)
    ├── configs/
    │   └── config_example.yaml            Annotated example configuration
    ├── pyproject.toml                     Package definition (pip installable)
    └── requirements.txt                   Dependencies
```

---

## CellProfiler pipelines

Two analysis pipelines are provided for different cell types:

| Pipeline | Cell type | ROI strategy |
|---|---|---|
| `Ca2_Trigger_pipeline_NPC.cpproj` | iPSC-derived neural progenitors | Nucleus expansion (CellDisk / CytoRing) |
| `Ca2_Trigger_pipeline_Fib.cpproj` | Fibroblasts | Reporter-channel segmentation + RelateObjects |

Both pipelines produce the same CSV output format and are compatible with the Python analysis.

The `Quality_Control_Pipeline.cpproj` saves overlay images for inspecting segmentation results.

### CellProfiler requirements
- CellProfiler ≥ 4.2
- Input: TIFF stacks with channels named so that the NamesAndTypes module can assign them

---

## Preprocessing scripts

### Fiji macro — export .lif to TIFF stacks

Converts a Leica `.lif` file into per-experiment folders of per-channel TIFF sequences.

```bash
/ImageJ.app/Contents/MacOS/ImageJ-macosx --headless \
  -macro pipeline/preprocessing/export_lif_to_sequences.ijm \
  "input=/path/to/file.lif output=/path/to/tiff_root channels=3 prefix=Ex"
```

Output structure:
```
tiff_root/
├── Ex1/
│   ├── C1-stack_Ex1/
│   ├── C2-stack_Ex1/
│   └── C3-stack_Ex1/
└── Ex2/ ...
```

### Batch CellProfiler runner

Runs a CellProfiler pipeline on all matching experiment folders:

```bash
chmod +x pipeline/preprocessing/run_cellprofiler_batch.sh

./pipeline/preprocessing/run_cellprofiler_batch.sh \
  --base "/path/to/tiff_root" \
  --pipeline "pipeline/cellprofiler/Ca2_Trigger_pipeline_NPC.cpproj" \
  --out "/path/to/cellprofiler_outputs"
```

---

## Python analysis

### Installation

```bash
cd pipeline/python/
pip install -e .
```

This installs the `ca_trigger` package and all dependencies.

### Running the analysis

```bash
python pipeline/python/run_analysis.py \
  --config pipeline/python/configs/config_example.yaml \
  --outdir results/
```

### Configuration

All analysis settings live in a YAML file — no Python editing needed for standard use.
Copy `configs/config_example.yaml` and edit:

```yaml
base_dir: "/path/to/your/cellprofiler_outputs"

cell_lines:
  NCRM1:
    - "{base_dir}/20250819_mt_er_CaTrigger_NCRM1"
    - "{base_dir}/20250820_mt_er_CaTrigger_NCRM1"
  MDCi237B:
    - "{base_dir}/20250924_mt_er_CaTrigger_MDCi237B"

analysis:
  frame_interval_s: 5.0
  baseline_frames: 5
  track_rule: both_channels_any_time    # or: either_channel_any_time
  roi_link_strategy: auto               # auto / by_objectnumber / by_parent_nuclei

  photobleach:
    enabled: false    # set true to apply exponential bleaching correction
```

### Key configurable options

| Option | Values | Effect |
|---|---|---|
| `roi_csv` | `MyExpt_CellDisk.csv`, `MyExpt_CytoRing.csv`, `MyExpt_CellOutline.csv` | Which ROI type to use |
| `track_rule` | `both_channels_any_time` / `either_channel_any_time` | Which cells to include |
| `baseline_frames` | integer | How many pre-stimulus frames define F₀ |
| `photobleach.enabled` | `true` / `false` | Apply bleaching correction after F/F₀ |

### Outputs

For each experiment:
- `<exp>__FF0_mt.csv` — normalised mitochondrial traces (rows = frames, columns = TrackIDs)
- `<exp>__FF0_other.csv` — normalised other-channel traces

Figures saved to `--outdir`:
- `cross_cell_lines_mt.png` / `cross_cell_lines_other.png` — mean ± SD per cell line
- `single_experiment.png` (in single-experiment mode)
- `photobleach_fit.png` (in photobleach-fit mode)

---

## Python requirements

- Python ≥ 3.10
- numpy, pandas, matplotlib, scipy, pyyaml

Install with: `pip install -e pipeline/python/`
