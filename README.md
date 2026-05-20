# Ca²⁺ Trigger Imaging Analysis Pipeline

Computational analysis tools for compartment-specific Ca²⁺ dynamics in live-cell time-lapse imaging experiments. The pipeline processes multi-channel fluorescence microscopy data through automated cell segmentation (CellProfiler) and Python-based signal extraction, normalisation, and plotting.

**Workflow overview:**
1. Acquire time-lapse images in 3 channels (e.g. mitochondrial reporter, cytosolic/ER reporter, Hoechst nuclear stain)
2. Run CellProfiler to segment nuclei, define ROIs, track cells, and filter for reporter-positive cells
3. Run the Python analysis to extract single-cell intensity traces, normalise to F/F₀, and generate plots

<img src="pipeline/pipeline_overview.png" width="900">

---

## Pipeline design principles

The pipelines are designed to:

- use **nuclei as stable reference objects** for segmentation and tracking across frames
- avoid unreliable full-cell segmentation based solely on reporter intensity
- define **standardised, reproducible ROIs** suitable for time-lapse analysis
- enable **single-cell Ca²⁺ trace extraction** across all frames
- restrict analysis to **reporter-positive cells** using objective intensity criteria

---

## NPC vs fibroblast pipeline

Two variants are provided because the two cell types require fundamentally different ROI strategies.

**NPC pipeline** — neural progenitor cells are small, compact, and densely packed. A nucleus-centred ROI (CellDisk, expanded by a fixed radius) provides a robust approximation of whole-cell signal.

**Fibroblast pipeline** — fibroblasts are substantially larger, display irregular and extended cytoplasmic morphology, and often show reporter signal far from the nucleus. The Fib pipeline therefore segments cellular regions directly from the reporter channel and then relates those objects to nuclei using `RelateObjects`. This distinction is critical for correct signal attribution.

---

## CellProfiler modules (execution order)

| Module | NPC | Fib | Purpose |
|---|:---:|:---:|---|
| **CorrectIlluminationCalculate** (mt channel) | ✔ | ✔ | Generates an illumination correction image for the mitochondrial channel, capturing large-scale intensity variations from uneven illumination |
| **CorrectIlluminationCalculate** (GECI channel) | ✔ | ✔ | Same for the cytosolic / ER reporter channel |
| **CorrectIlluminationApply** | ✔ | ✔ | Applies correction by dividing raw images by the illumination model |
| **RescaleIntensity** (Hoechst) | ✔ | ✔ | Normalises Hoechst intensity to stabilise nucleus segmentation across experiments |
| **IdentifyPrimaryObjects** (Nuclei) | ✔ | ✔ | Segments nuclei as stable reference objects for tracking and ROI association |
| **IdentifyPrimaryObjects** (CellBody) | ✖ | ✔ | *Fib only.* Segments cellular regions from the reporter channel to capture extended fibroblast morphology |
| **IdentifySecondaryObjects** (CellDisk) | ✔ | ✖ | *NPC only.* Expands each nucleus by a fixed radius to generate a standardised whole-cell ROI |
| **RelateObjects** (Nuclei ↔ CellBody) | ✖ | ✔ | *Fib only.* Associates reporter-defined cell bodies to their corresponding nuclei for per-cell tracking |
| **IdentifyTertiaryObjects** (CytoRing) | optional | ✔ | Subtracts the nuclear region from the CellDisk to create a perinuclear cytoplasmic ROI |
| **TrackObjects** (Nuclei) | ✔ | ✔ | Tracks nuclei across consecutive frames; all associated ROIs inherit the same TrackID |
| **MeasureObjectIntensity** | ✔ | ✔ | Quantifies mean fluorescence intensity within defined ROIs per cell per frame |
| **FilterObjects** (PositiveCells_mt) | ✔ | ✔ | Retains only cells above a mitochondrial reporter intensity threshold |
| **FilterObjects** (PositiveCells_other) | ✔ | ✔ | Same for the cytosolic / ER reporter channel |
| **OverlayOutlines** + **SaveImages** | ✔ | ✔ | Saves overlay images of segmentation results for visual quality control |
| **ExportToSpreadsheet** | ✔ | ✔ | Exports all measurements, TrackIDs, and metadata to CSV for downstream Python analysis |

---

## Where to start

### → [`demo/`](demo/)

A self-contained example with real data. Includes pre-computed CellProfiler outputs so you can run the Python analysis immediately with one command:

```bash
cd demo/
pip install numpy pandas matplotlib
python analyse.py
```

Start here to understand how the pipeline works before adapting it to your own data.

---

### → [`pipeline/`](pipeline/)

The full toolkit for multi-experiment, multi-cell-line analyses:

- **CellProfiler pipelines** — NPC and fibroblast variants, plus a quality control pipeline
- **Preprocessing scripts** — Fiji macro to export `.lif` files to TIFF stacks; batch script to run CellProfiler on many experiments at once
- **Python package** — installable, config-driven analysis supporting multiple cell lines, photobleaching correction, and flexible ROI strategies

---

## Repository structure

```
├── demo/                        Self-contained single-experiment example
│   ├── images/                  Raw TIFF stacks (Git LFS)
│   ├── cellprofiler_pipeline/   CellProfiler pipeline (NPC)
│   ├── cellprofiler_outputs/    Pre-computed CellProfiler CSV outputs
│   ├── analyse.py               Standalone Python analysis script
│   └── expected_outputs/        Reference output for comparison
│
└── pipeline/                    Full analysis toolkit
    ├── cellprofiler/            NPC, fibroblast, and QC pipelines
    ├── preprocessing/           Fiji macro + batch CellProfiler runner
    └── analysis/                Installable Python package
        ├── src/ca_trigger/      analysis_core.py, figures.py
        ├── run_analysis.py      Config-driven CLI entry point
        ├── configs/             Example YAML configurations
        └── pyproject.toml       pip-installable package
```

---

## Requirements

- **CellProfiler** ≥ 4.2 — [cellprofiler.org](https://cellprofiler.org)
- **Python** ≥ 3.10 — numpy, pandas, matplotlib, scipy, pyyaml
- **Fiji / ImageJ** — only needed for preprocessing `.lif` files (optional)
- **Git LFS** — the demo images are stored with Git Large File Storage; run `git lfs install && git lfs pull` after cloning to download them

---

## Contact

**Felicitas Windhagen**
For questions about pipeline usage or adaptation, please open an issue.
