# Compartmentalised Ca²⁺ Imaging Analysis Pipeline

This repository contains the computational analysis tools developed for a Master’s thesis investigating compartment-specific calcium (Ca²⁺) dynamics in human iPSC-derived neural progenitor cells (NPCs). The pipeline enables reproducible, single-cell extraction of mitochondrial, ER, and cytosolic Ca²⁺ signals from live-cell time-lapse imaging experiments.

The workflow combines:
- automated image segmentation and tracking using **CellProfiler**
- quantitative fluorescence extraction
- post-processing, normalisation, and quality control in **Python**

The pipeline is designed to be robust to heterogeneous reporter expression, clustered NPC morphology, and time-lapse–specific challenges such as photobleaching and cell movement.

---

## CellProfiler Analysis Pipelines

This repository contains automated CellProfiler pipelines for segmentation, tracking, and fluorescence quantification in live-cell Ca²⁺ imaging experiments. Two related but distinct pipelines are provided:

- **NPC pipeline** – optimised for iPSC-derived neural progenitor cells
- **Fib pipeline** – adapted for fibroblasts with larger size and extended cytoplasmic morphology

Both pipelines follow the same overall analysis logic but differ in how cellular regions of interest (ROIs) are defined and related to nuclei.

---

## Conceptual Overview of the Pipeline

<img src="figures/pipeline_concept_7steps.png" width="900">

**Figure 1. Conceptual overview of the CellProfiler analysis workflow.**  
The figure summarises the logical flow of the pipeline: background correction, nucleus detection, ROI definition, tracking, identification of reporter-positive cells, and visual quality control.  
Note that this illustration represents a **conceptual summary**; the actual CellProfiler pipelines consist of multiple modules described in detail below.

---

## General Design Principles

The pipelines are designed to:

- use **nuclei as stable reference objects** for segmentation and tracking
- avoid unreliable full-cell segmentation based solely on reporter intensity
- define **standardised, reproducible ROIs** suitable for time-lapse analysis
- enable **single-cell Ca²⁺ trace extraction** across frames
- restrict analysis to **reporter-positive cells** using objective intensity criteria

All measurements are exported as tabular data for downstream analysis in Python.

---

## NPC vs Fib Pipeline: Key Conceptual Difference

Neural progenitor cells (NPCs) are small, compact, and densely packed. For these cells, a nucleus-centred ROI provides a robust approximation of whole-cell signal.

Fibroblasts, in contrast:
- are substantially larger,
- display irregular and extended cytoplasmic morphology,
- often exhibit reporter signal far from the nucleus.

Therefore, the Fib pipeline does **not** rely on nucleus expansion alone. Instead, it explicitly segments cellular regions in a reporter channel and then **relates those objects to nuclei**. This distinction is critical for correct signal attribution.

---

## Full CellProfiler Module Documentation (Execution Order)

The table below lists **all CellProfiler modules in execution order**, with explicit comparison between the NPC and Fib pipelines.

| Module | NPC Pipeline | Fibroblast Pipeline | Purpose and Rationale |
|------|-------------|--------------|-----------------------|
| **CorrectIlluminationCalculate (Illum_mt)** | ✔ | ✔ | Generates an illumination correction image for the mitochondrial channel, capturing large-scale intensity variations caused by uneven illumination or optical artefacts. |
| **CorrectIlluminationCalculate (Illum_GECI)** | ✔ | ✔ | Computes a channel-specific illumination correction for the cytosolic or ER GECI channel to preserve compartment-specific signal structure. |
| **CorrectIlluminationApply** | ✔ | ✔ | Applies illumination correction by dividing raw images by the calculated illumination model, normalising background intensity across the field of view. |
| **RescaleIntensity (Hoechst)** | ✔ | ✔ | Normalises Hoechst intensity to enhance nucleus–background contrast and stabilise segmentation across experiments. |
| **IdentifyPrimaryObjects (Nuclei)** | ✔ | ✔ | Segments nuclei using intensity thresholding and empirically defined size constraints. Nuclei serve as stable reference objects for tracking and ROI association. |
| **IdentifyPrimaryObjects (CellBody / Reporter Channel)** | ✖ | ✔ | **Fib pipeline only.** Segments cellular regions directly from a reporter channel to capture extended fibroblast morphology that cannot be approximated by nucleus expansion. |
| **IdentifySecondaryObjects (CellDisk)** | ✔ | ✖ | **NPC pipeline only.** Expands each nucleus by a fixed radius to generate a standardised whole-cell ROI (“CellDisk”), suitable for compact NPC morphology. |
| **RelateObjects (Nuclei ↔ CellBody)** | ✖ | ✔ | **Fib pipeline only.** Relates reporter-defined cellular objects to their corresponding nuclei, enabling per-cell tracking and quantification. |
| **IdentifyTertiaryObjects (CytoRing)** | optional | ✔ | Subtracts the nuclear region from the CellDisk to create a perinuclear cytoplasmic ROI (“CytoRing”). Used mainly in the NPC pipeline; less central for fibroblasts. |
| **TrackObjects (Nuclei)** | ✔ | ✔ | Tracks nuclei across consecutive frames to generate persistent TrackIDs. Associated cellular ROIs inherit tracking via nucleus linkage. |
| **MeasureObjectIntensity** | ✔ | ✔ | Quantifies mean fluorescence intensity within defined ROIs for each tracked cell and time point. |
| **FilterObjects (PositiveCells_mt)** | ✔ | ✔ | Removes cells with mitochondrial reporter intensities below a defined threshold, retaining reporter-positive cells only. |
| **FilterObjects (PositiveCells_other)** | ✔ | ✔ | Applies equivalent intensity-based filtering for cytosolic or ER reporter channels. |
| **OverlayOutlines** | ✔ | ✔ | Overlays outlines of nuclei and cellular ROIs onto the original images for visual quality control. |
| **SaveImages (QC overlays)** | ✔ | ✔ | Saves overlay images for segmentation and filtering validation. |
| **ExportToSpreadsheet** | ✔ | ✔ | Exports all quantified measurements, object identifiers, tracking information, and metadata to CSV files for downstream analysis. |

---

## Summary of Pipeline Strategies

**NPC pipeline**
- Single primary object: nuclei
- Whole-cell ROIs generated by nucleus expansion
- Optimised for small, densely packed cells

**Fib pipeline**
- Two primary object classes: nuclei and reporter-defined cell bodies
- Explicit nucleus–cell association using `RelateObjects`
- Required to capture extended cytoplasmic signal

---

## Pipeline Outputs

Each pipeline produces:
- CSV files containing object-level intensity measurements
- tracking identifiers (TrackID)
- frame numbers and metadata
- reporter-positive cell classifications
- optional QC images with ROI overlays

These outputs are designed to be consumed directly by the Python analysis scripts included in this repository.

---

## Adapting the Pipelines to New Cell Types

- Use the **NPC strategy** for compact, nucleus-centred cells
- Use the **Fib strategy** when cytoplasmic extent cannot be approximated by nucleus expansion
- Preserve nucleus-based tracking whenever possible to maintain temporal stability

---

## Preprocessing and batch execution (Fiji + CellProfiler)

This repository provides optional helper scripts to standardize preprocessing
and batch execution of CellProfiler pipelines. These scripts are recommended
but not strictly required — experiments can also be prepared manually if
preferred.

Two alternative workflows are supported:

- **Automated preprocessing and batch execution** (recommended)
- **Manual preparation and naming**

Both workflows produce CellProfiler outputs compatible with the Python analysis
pipeline described below.

---

### Option A: Automated preprocessing (recommended)

#### Export `.lif` files to per-experiment TIFF sequences (Fiji)

Multi-series `.lif` files can be converted into individual experiment folders
using the provided Fiji macro.

Each series in the `.lif` file is exported as one experiment folder containing
per-channel TIFF sequences.

Script location:

    scripts/export_lif_to_sequences.ijm

##### Requirements
- Fiji / ImageJ
- Bio-Formats (included in Fiji)

##### Headless usage (recommended)

    /ImageJ.app/Contents/MacOS/ImageJ-macosx \
      --headless \
      -macro scripts/export_lif_to_sequences.ijm \
      "input=/path/to/file.lif output=/path/to/output_root channels=3 prefix=Ex"

##### Parameters
- `input`   – path to the `.lif` file
- `output`  – directory where experiment folders will be created
- `channels` – number of channels to export (default: 3)
- `prefix`  – prefix for experiment folders (default: Ex)

##### Output structure

    output_root/
    ├── Ex1/
    │   ├── C1-stack_Ex1/
    │   ├── C2-stack_Ex1/
    │   └── C3-stack_Ex1/
    ├── Ex2/
    │   └── ...
    └── ...

Each `Ex*` folder corresponds to one experiment and can be passed directly to
CellProfiler.

---

#### Batch execution of CellProfiler pipelines

Prepared experiment folders can be processed sequentially using the batch
runner script.

Script location:

    scripts/run_cellprofiler_batch.sh

##### Requirements
- CellProfiler installed
- A CellProfiler pipeline (`.cpproj` or `.cppipe`)

##### Basic usage

    chmod +x scripts/run_cellprofiler_batch.sh

    ./scripts/run_cellprofiler_batch.sh \
      --base "/path/to/experiment_folders" \
      --pipeline "pipelines/projects/Ca2_Trigger_pipeline.cpproj" \
      --out "/path/to/cellprofiler_outputs"

##### Selecting which experiments to run

Experiments are selected using a glob pattern applied to subfolders of `--base`.

Common examples:

    *_CaTrigger_*              # all CaTrigger experiments
    *_mt_er_CaTrigger_*        # ER experiments only
    *_mt_cyt_CaTrigger_*       # cytosolic experiments only
    *_CaTrigger_NCRM1*         # single cell line

Example:

    ./scripts/run_cellprofiler_batch.sh \
      --base "/path/to/experiment_folders" \
      --pipeline "pipelines/projects/Ca2_Trigger_pipeline_Fib.cpproj" \
      --out "/path/to/cellprofiler_outputs" \
      --glob "*_CaTrigger_MDCi237*"

##### Notes
- Experiments are run **sequentially**, one at a time
- Output folder names are **stable** (no timestamps by default)
- Existing outputs are skipped automatically
- The script is agnostic to cell type (NPC or fibroblast)

---

### Option B: Manual preparation (no scripts)

Experiments can also be prepared manually without using the Fiji or batch
scripts.

#### Manual experiment folder requirements

Each experiment must be stored in a **single folder** containing image files
that CellProfiler can load and assign to channels via the `NamesAndTypes`
module.

Valid example structure:

    20250819_mt_er_CaTrigger_NCRM1/
    ├── C1-stack/
    │   ├── C1-0000.tif
    │   └── C1-0001.tif
    ├── C2-stack/
    │   └── ...
    └── C3-stack/
        └── ...

#### Important requirements
- One folder corresponds to one experiment
- Channel identity must be recoverable from file or folder names
- Naming must match the `NamesAndTypes` rules in the CellProfiler pipeline

Once prepared, experiments can be processed either manually in CellProfiler or
via the batch script.

---

### Downstream compatibility

All CellProfiler outputs generated using either workflow are compatible with
the Python analysis pipeline, which expects:

- one output folder per experiment
- standard CellProfiler CSV outputs (`MyExpt_*.csv`)

---

## Python analysis workflow (from CellProfiler outputs to final Ca²⁺ traces)

This repository provides a modular Python analysis pipeline that processes **CellProfiler CSV outputs** from live-cell Ca²⁺ imaging experiments and converts them into **single-cell and population-level Ca²⁺ traces**, with optional photobleaching correction and standardized plotting.

The analysis is fully **config-driven** and does **not require modifying Python code** for standard use cases.

---

### Overview

**Input:**  
CellProfiler CSV files exported per experiment folder (one folder per imaging run).

**Output:**  
- Normalized single-cell Ca²⁺ traces (F/F₀)  
- Mean ± SD traces per experiment  
- Mean ± SD traces per cell line (across replicates)  
- Optional photobleaching fits  
- Publication-ready plots  

---

## 1. Required inputs

For each experiment, the analysis expects a folder containing CellProfiler CSV outputs generated by one of the provided pipelines (NPC or Fibroblast).

At minimum, the following CSV files must be present:

- `MyExpt_Nuclei.csv`  
- ROI table (one of):
  - `MyExpt_CellDisk.csv` (NPCs)
  - `MyExpt_CellOutline.csv` (Fibroblasts)
- `MyExpt_PositiveCells_mt.csv`
- `MyExpt_PositiveCells_other.csv`

Optionally:
- `MyExpt_Image.csv` (used only for metadata, not required)

Each experiment must be stored in its **own folder**, for example:

    cellprofiler_outputs/
    └── 20250819_mt_er_CaTrigger_NCRM1/
        ├── MyExpt_Nuclei.csv
        ├── MyExpt_CytoRing.csv
        ├── MyExpt_PositiveCells_mt.csv
        ├── MyExpt_PositiveCells_other.csv
        └── ...

---

## 2. Configuration (no code editing required)

All analysis settings are controlled via a YAML configuration file located in `configs/`.

Example (`config_mt_er.yaml`):

    base_dir: "/Users/yourname/Experiments/cellprofiler_outputs"

    cell_lines:
      NCRM1:
        - "{base_dir}/20250819_mt_er_CaTrigger_NCRM1"
        - "{base_dir}/20250820_mt_er_CaTrigger_NCRM1"
      MDCi237B:
        - "{base_dir}/20250924_mt_er_CaTrigger_MDCi237B"

    analysis:
      frame_interval_s: 5.0
      baseline_frames: 5
      track_rule: both_channels_any_time
      roi_link_strategy: auto

    roi:
      roi_csv: MyExpt_CytoRing.csv

    photobleach:
      enabled: false

### Key configurable options

- **ROI choice**
  - NPCs: `MyExpt_CytoRing.csv` or `MyExpt_CellDisk.csv`
  - Fibroblasts: `MyExpt_CellOutline.csv`
- **Track selection rule**
  - `both_channels_any_time`: retain cells positive in both channels at any time
  - `either_channel_any_time`: retain cells positive in at least one channel
- **Baseline normalization**
  - `baseline_frames`: number of initial frames used to compute F₀
- **Photobleaching correction**
  - Optional exponential or linear fit applied after F/F₀ normalization

Multiple configurations (e.g. ER vs cytosol) can coexist and be run independently.

---

## 3. Running the analysis

From the repository root:

    python cli/run_analysis.py --config configs/config_mt_er.yaml --outdir results_mt_er

No preprocessing steps are required beyond running the CellProfiler pipeline.

---

## 4. What the analysis does (step-by-step)

For each experiment:

1. **Load CellProfiler tables**  
   Nuclei, ROI, and positivity tables are read from CSV files.

2. **Link ROIs to tracked nuclei**  
   - NPC pipelines: ROIs are linked via `(ImageNumber, ObjectNumber)`  
   - Fibroblast pipelines: ROIs are linked via `Parent_Nuclei`  
   - This is handled automatically via `roi_link_strategy: auto`.

3. **Attach TrackIDs**  
   Each ROI inherits the nucleus `TrackID` assigned by CellProfiler.

4. **Apply positivity filtering**  
   Cells are retained based on mitochondrial and/or “other” channel positivity, according to the configured rule.

5. **Build single-cell intensity matrices**  
   For each retained cell:
   - rows = TrackIDs  
   - columns = frames  
   - values = mean ROI intensity per frame  

6. **Normalize to F/F₀**  
   Intensities are normalized per cell using the mean of the first `baseline_frames`.

7. **Optional photobleach correction**  
   If enabled, bleaching curves are fitted and applied to the normalized traces.

8. **Aggregate results**  
   - Mean ± SD across cells (per experiment)  
   - Mean ± SD across experiments (per cell line)  

---

## 5. Outputs

### Per experiment

Saved into the output directory:

- `<experiment>__FF0_mt.csv`  
- `<experiment>__FF0_other.csv`  

Each file contains:
- rows = single cells (TrackID)
- columns = time points (frames)
- values = F/F₀

Time information is stored explicitly in:

- `<experiment>__time_s.csv`

---

### Per cell line (optional)

If enabled, long-format tables are exported for statistical analysis:

    <cell_line>__ALLCELLS_long.csv

Columns include:
- `TrackID`
- `time_s`
- `FF0_mt`
- `FF0_other`
- `cell_line`
- `experiment`

---

### Figures

The pipeline generates:
- single-experiment Ca²⁺ traces (mt + other)
- cross-cell-line comparisons
- optional photobleaching fit plots

Plotting is handled separately in `figures.py` and consumes the analysis outputs directly.

---

## 6. Typical user workflow (summary)

1. Preprocessing of files in Fiji (naming + splitting to image series)
2. Run CellProfiler pipeline  
3. Verify segmentation using overlay images  
4. Export CellProfiler CSVs  
5. Create or modify a YAML configuration file  
6. Run `run_analysis.py`  
7. Inspect plots and exported CSVs  

No Python code modification is required for standard analyses.

--

## Requirements

- CellProfiler ≥ 4.2
- Python ≥ 3.10
- Python packages: `numpy`, `pandas`, `matplotlib`

---

## Contact

Author: **Felicitas Windhagen**  
For questions regarding pipeline usage or adaptation, please open an issue or contact the author.
