# Full demo

This demo runs the full workflow on a small included example dataset:

TIFF input -> CellProfiler -> Python analysis

This demo dataset is stored with Git LFS. Install Git LFS before cloning, or run `git lfs pull` after cloning to download the TIFF files.

## Included example input
`demo/raw_inputs/20251001_mt_cyt_Ex_NCRM1/`

## Run
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
bash scripts/run_demo_full.sh
