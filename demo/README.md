# Demo — Ca²⁺ Imaging Analysis

A complete worked example of the pipeline on one real experiment.
Follow the steps below to go from raw microscopy images all the way to normalised Ca²⁺ traces.

---

## What's in here

| Path | Contents |
|---|---|
| `images/` | Raw TIFF stacks — 3 channels, 61 frames (stored via Git LFS) |
| `cellprofiler_pipeline/` | CellProfiler project for this demo (NPC pipeline) |
| `cellprofiler_outputs/` | Pre-computed CellProfiler CSV outputs — included so you can skip Step 2 if needed |
| `analyse.py` | Standalone Python analysis script |
| `expected_outputs/traces.png` | Reference output — compare yours to check everything worked |

---

## Step 1 — Install Python dependencies

```bash
pip install numpy pandas matplotlib
```

---

## Step 2 — Run CellProfiler (segmentation and tracking)

Open **CellProfiler** (≥ 4.2) and load the pipeline:

```
demo/cellprofiler_pipeline/calcium_imaging_pipeline_NPC.cpproj
```

In CellProfiler, set:
- **Default Input Folder** → `demo/images/20251001_mt_cyt_Ex_NCRM1/`
- **Default Output Folder** → `demo/cellprofiler_outputs/20251001_mt_cyt_Ex_NCRM1/`

Then click **Analyze Images**.

CellProfiler will:
1. Correct uneven illumination across the field of view
2. Detect and segment nuclei in the Hoechst channel
3. Expand each nucleus to create a whole-cell ROI (CellDisk)
4. Track cells across all 61 frames
5. Measure mean fluorescence intensity per ROI per frame
6. Identify which cells are positive for the mitochondrial and cytosolic reporters
7. Export all measurements as CSV files

> **Note:** Pre-computed outputs are already in `cellprofiler_outputs/` so you can skip this step and go straight to Step 3 if you just want to try the Python analysis.

---

## Step 3 — Run the Python analysis

```bash
cd demo/
python analyse.py
```

The script reads the CellProfiler CSV outputs and:
1. Links each ROI measurement to its tracked cell (TrackID)
2. Keeps only cells that were reporter-positive in both channels
3. Builds an intensity matrix: rows = cells, columns = frames
4. Normalises each trace to F/F₀ (divides by the mean of the first 5 baseline frames)
5. Saves normalised traces as CSV and plots mean ± SD

Outputs appear in `demo/outputs/`:
- `FF0_mt.csv` — normalised mitochondrial Ca²⁺ traces
- `FF0_other.csv` — normalised cytosolic Ca²⁺ traces
- `traces.png` — mean ± SD plot for both channels

Compare your `traces.png` to `expected_outputs/traces.png` to confirm it worked correctly.

---

## Adapting to your own data

Edit the parameters at the top of `analyse.py`:

```python
EXPERIMENT_DIR   = Path("cellprofiler_outputs/your_experiment_folder")
FRAME_INTERVAL_S = 5.0    # seconds between frames
BASELINE_FRAMES  = 5      # frames before stimulus
ROI_CSV          = "MyExpt_CellDisk.csv"   # or CytoRing / CellOutline
```

For multiple experiments, multiple cell lines, photobleaching correction, or fibroblast data, see the full pipeline in [`../pipeline/`](../pipeline/).
