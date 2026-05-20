# Full Analysis Pipeline

This folder contains the complete toolkit for analysing multi-experiment, multi-cell-line Ca²⁺ trigger imaging data.

For a quick-start example on one experiment, see [`../demo/`](../demo/) first.

---

## Folder structure

```
pipeline/
├── preprocessing/                Helper scripts for image preparation
│   ├── export_lif_to_sequences.ijm             Fiji macro: .lif → TIFF stacks
│   └── run_cellprofiler_batch.sh               Batch-run CellProfiler on many experiments
│
├── cellprofiler/                 CellProfiler pipelines
│   ├── calcium_imaging_pipeline_NPC.cpproj    NPC / neural progenitor cells
│   ├── calcium_imaging_pipeline_Fib.cpproj    Fibroblasts
│   └── quality_control_pipeline.cpproj        QC overlays
│
└── analysis/                     Python analysis package
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

## Step 1 — Preprocessing: export .lif to TIFF stacks

Converts a Leica `.lif` file into per-experiment folders of per-channel TIFF sequences, ready for CellProfiler.

### Experiment folder naming convention

Give each experiment folder a name in this format:

```
YYYYMMDD_<reporter1>_<reporter2>_CaTrigger_<CellLine>
```

Examples:
```
20250819_mt_er_CaTrigger_NCRM1
20250924_mt_cyt_CaTrigger_MDCi237B
```

- `mt` = mitochondrial Ca²⁺ reporter (channel 1)
- `er` or `cyt` = ER or cytosolic Ca²⁺ reporter (channel 2)
- Channel 3 is always the Hoechst nuclear stain
- The cell line name at the end is used to group experiments in the Python analysis

This naming is a convention, not enforced by the scripts — but keeping it consistent makes the config file much easier to write later.

### Option A — Automated (Fiji macro)

```bash
/ImageJ.app/Contents/MacOS/ImageJ-macosx --headless \
  -macro pipeline/preprocessing/export_lif_to_sequences.ijm \
  "input=/path/to/file.lif output=/path/to/tiff_root channels=3 prefix=Ex"
```

### Option B — Manual (Fiji GUI)

1. Open Fiji and drag your `.lif` file onto the toolbar — Bio-Formats will prompt you to choose a series (one series = one experiment/field of view)
2. Open each series as a hyperstack
3. Use **Image → Color → Split Channels** to split the hyperstack into one window per channel, then for each channel window use **File → Save As → Image Sequence** to export the individual TIFFs
4. Organise the exported folders to match the structure below

Output structure either way:
```
tiff_root/
├── 20250819_mt_er_CaTrigger_NCRM1/
│   ├── C1-stack_Ex1/           ← mitochondrial channel
│   │   ├── C1-stack0000.tif
│   │   ├── C1-stack0001.tif
│   │   └── ...
│   ├── C2-stack_Ex1/           ← ER/cytosolic channel
│   │   ├── C2-stack0000.tif
│   │   └── ...
│   └── C3-stack_Ex1/           ← Hoechst channel
│       ├── C3-stack0000.tif
│       └── ...
└── 20250820_mt_er_CaTrigger_NCRM1/ ...
```

**Requirements:** Fiji / ImageJ with Bio-Formats (included in Fiji by default).

---

## Step 2 — CellProfiler: segmentation and tracking

### Pipelines

Two pipelines are provided for different cell types:

| Pipeline | Cell type | ROI strategy |
|---|---|---|
| `calcium_imaging_pipeline_NPC.cpproj` | iPSC-derived neural progenitors | Nucleus expansion (CellDisk / CytoRing) |
| `calcium_imaging_pipeline_Fib.cpproj` | Fibroblasts | Reporter-channel segmentation + RelateObjects |

Both produce the same CSV output format and are compatible with the Python analysis.
Use `quality_control_pipeline.cpproj` to generate overlay images for inspecting segmentation results.

**Requirements:** CellProfiler ≥ 4.2.

### Option A — Automated (batch script)

```bash
chmod +x pipeline/preprocessing/run_cellprofiler_batch.sh

./pipeline/preprocessing/run_cellprofiler_batch.sh \
  --base "/path/to/tiff_root" \
  --pipeline "pipeline/cellprofiler/calcium_imaging_pipeline_NPC.cpproj" \
  --out "/path/to/cellprofiler_outputs"
```

The batch script runs experiments sequentially, skips folders that already have outputs, and accepts a `--glob` pattern to select a subset (e.g. `"*_mt_er_*"`).

### Option B — Manual (CellProfiler GUI)

1. Open CellProfiler and load the appropriate pipeline from `pipeline/cellprofiler/`
2. Set **Default Input Folder** to your experiment's TIFF folder (e.g. `tiff_root/20250819_mt_er_CaTrigger_NCRM1/`)
3. Set **Default Output Folder** to where you want the CSV results saved (e.g. `cellprofiler_outputs/20250819_mt_er_CaTrigger_NCRM1/`)
4. Click **Analyze Images**

Repeat for each experiment. The output folder name should match the experiment name — the Python analysis uses it to label results.

---

## Step 3 — Python analysis: traces, normalisation, and plots

### Installation

```bash
cd pipeline/analysis/
pip install -e .
```

### Option A — Config-driven CLI (recommended for multiple experiments)

```bash
python pipeline/analysis/run_analysis.py \
  --config pipeline/analysis/configs/config_example.yaml \
  --outdir results/
```

All settings live in a YAML file — no Python editing needed for standard use.

### Option B — Manual (single experiment, edit the script directly)

If you just want to analyse one experiment without setting up the config system, copy `demo/analyse.py` to your working directory and edit the parameters at the top:

```python
EXPERIMENT_DIR   = Path("/path/to/your/cellprofiler_outputs/experiment_folder")
FRAME_INTERVAL_S = 5.0   # seconds between frames
BASELINE_FRAMES  = 5     # frames before the stimulus
ROI_CSV          = "MyExpt_CellDisk.csv"   # or CytoRing / CellOutline
```

Then run:
```bash
python analyse.py
```

This produces the same normalised trace CSVs and plots without any installation or config file.

### Configuration (for Option A)
Copy `configs/config_example.yaml` and edit.

> **Note on the `MyExpt_` prefix:** The CSV filenames in the config (`MyExpt_CellDisk.csv`, `MyExpt_Nuclei.csv`, etc.) must match the **Output filename** prefix set in CellProfiler's ExportToSpreadsheet module. If you used a different prefix, update the `files:` section of your config to match.

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

Per experiment (saved into each CellProfiler output folder):
- `<exp>__FF0_mt.csv` — normalised mitochondrial traces (rows = frames, columns = TrackIDs)
- `<exp>__FF0_other.csv` — normalised other-channel traces

Figures saved to `--outdir`:
- `cross_cell_lines_mt.png` / `cross_cell_lines_other.png` — mean ± SD per cell line
- `single_experiment.png` (in single-experiment mode)
- `photobleach_fit.png` (in photobleach-fit mode)
