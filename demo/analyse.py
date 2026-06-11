"""
Ca2+ imaging analysis - demo script
=====================================
Processes CellProfiler CSV outputs from one imaging experiment into
normalised single-cell Ca2+ traces (F/F0), then saves a CSV and plot.

Run from the demo/ folder:
    python analyse.py

Input:  cellprofiler_outputs/<experiment>/   (CSV files produced by CellProfiler)
Output: outputs/                             (FF0_mt.csv, FF0_other.csv, traces.png)

Steps
-----
1. Load the CellProfiler output tables
2. Attach TrackIDs: link each ROI row to the tracked nucleus it belongs to
3. Filter for reporter-positive cells (positive in both channels at any time)
4. Build an intensity matrix  (rows = cells, columns = frames)
5. Normalise to F/F0  (divide by mean of the first few baseline frames)
6. Save the normalised traces as CSV and plot mean +/- SD
"""

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# ---------------------------------------------------------------------------
# Parameters — edit these to match your experiment
# ---------------------------------------------------------------------------

EXPERIMENT_DIR = Path("cellprofiler_outputs/20251001_mt_cyt_Ex_NCRM1")

FRAME_INTERVAL_S = 5.0   # seconds between frames
BASELINE_FRAMES  = 5     # how many initial frames to use for F0

# Which CellProfiler ROI table to use:
#   NPC experiments  -> "MyExpt_CellDisk.csv"  or  "MyExpt_CytoRing.csv"
#   Fibroblasts      -> "MyExpt_CellOutline.csv"
# The "MyExpt_" prefix must match the Output filename prefix set in
# CellProfiler's ExportToSpreadsheet module. If you changed it there,
# update all four CSV names below to match.
ROI_CSV       = "MyExpt_CellDisk.csv"
NUCLEI_CSV    = "MyExpt_Nuclei.csv"
POS_MT_CSV    = "MyExpt_PositiveCells_mt.csv"
POS_OTHER_CSV = "MyExpt_PositiveCells_other.csv"

# Column names in the ROI table that hold mean fluorescence intensity
MT_COL    = "Intensity_MeanIntensity_BGS_mt"
OTHER_COL = "Intensity_MeanIntensity_BGS_other"

OUTPUT_DIR = Path("outputs")

# ---------------------------------------------------------------------------
# Step 1 — Load CellProfiler tables
# ---------------------------------------------------------------------------

def load_tables(exp_dir: Path):
    nuclei    = pd.read_csv(exp_dir / NUCLEI_CSV)
    roi       = pd.read_csv(exp_dir / ROI_CSV)
    pos_mt    = pd.read_csv(exp_dir / POS_MT_CSV)
    pos_other = pd.read_csv(exp_dir / POS_OTHER_CSV)
    return nuclei, roi, pos_mt, pos_other


# ---------------------------------------------------------------------------
# Step 2 — Attach TrackIDs to ROI rows
# ---------------------------------------------------------------------------
# CellProfiler assigns each nucleus a TrackID (TrackObjects_Label) that stays
# constant across frames. We copy that ID onto each ROI row so we can later
# group measurements by cell rather than by frame.

def attach_track_ids(roi: pd.DataFrame, nuclei: pd.DataFrame) -> pd.DataFrame:
    track_cols = [c for c in nuclei.columns if c.startswith("TrackObjects_Label")]
    if not track_cols:
        raise RuntimeError("No TrackObjects_Label column found in Nuclei table.")
    track_col = sorted(track_cols, key=lambda s: (len(s), s))[0]

    nuc_tracks = nuclei[["ImageNumber", "ObjectNumber", track_col]].rename(
        columns={track_col: "TrackID"}
    )

    if "Parent_Nuclei" in roi.columns:
        # Fibroblast pipeline: ROI links to nucleus via Parent_Nuclei
        roi = roi.merge(
            nuc_tracks,
            left_on=["ImageNumber", "Parent_Nuclei"],
            right_on=["ImageNumber", "ObjectNumber"],
            how="left",
            suffixes=("", "_nuc"),
        ).drop(columns=["ObjectNumber_nuc"], errors="ignore")
    else:
        # NPC pipeline: ROI and nucleus share the same ObjectNumber
        roi = roi.merge(nuc_tracks, on=["ImageNumber", "ObjectNumber"], how="left")

    linked = roi["TrackID"].notna().mean()
    print(f"  ROI rows with a TrackID: {linked:.1%}")
    return roi


# ---------------------------------------------------------------------------
# Step 3 — Filter for reporter-positive cells
# ---------------------------------------------------------------------------
# Keep only TrackIDs that were flagged as positive in BOTH channels at any
# point during the recording. This removes cells without a functional reporter.

def get_positive_tracks(roi: pd.DataFrame,
                        pos_mt: pd.DataFrame,
                        pos_other: pd.DataFrame) -> set:
    def positive_set(pos_df: pd.DataFrame) -> set:
        pairs = set(zip(pos_df["ImageNumber"].astype(int),
                        pos_df["ObjectNumber"].astype(int)))
        mask = [
            (int(im), int(ob)) in pairs
            for im, ob in zip(roi["ImageNumber"].astype(int),
                              roi["ObjectNumber"].astype(int))
        ]
        return set(roi.loc[mask, "TrackID"].dropna())

    mt_tracks    = positive_set(pos_mt)
    other_tracks = positive_set(pos_other)
    keep         = mt_tracks & other_tracks   # positive in BOTH channels

    print(f"  Positive tracks — mt: {len(mt_tracks)}, "
          f"other: {len(other_tracks)}, kept (both): {len(keep)}")
    return keep


# ---------------------------------------------------------------------------
# Step 4 — Build intensity matrix  (cells x frames)
# ---------------------------------------------------------------------------

def build_matrix(roi: pd.DataFrame, track_ids: set, col: str) -> pd.DataFrame:
    subset = roi[roi["TrackID"].isin(track_ids)]
    return (subset
            .pivot_table(index="TrackID", columns="ImageNumber", values=col)
            .sort_index(axis=1))


# ---------------------------------------------------------------------------
# Step 5 — Normalise to F/F0
# ---------------------------------------------------------------------------
# F0 = mean intensity over the first BASELINE_FRAMES frames (before stimulus).
# Each cell's trace is divided by its own F0, so 1.0 = baseline level.

def normalise_ff0(matrix: pd.DataFrame) -> pd.DataFrame:
    if matrix.shape[1] < BASELINE_FRAMES:
        raise ValueError(
            f"Only {matrix.shape[1]} frames available, need {BASELINE_FRAMES} for baseline."
        )
    f0 = matrix.iloc[:, :BASELINE_FRAMES].mean(axis=1)
    return matrix.div(f0, axis=0)


# ---------------------------------------------------------------------------
# Step 6 — Save outputs
# ---------------------------------------------------------------------------

def save_csv(ff0: pd.DataFrame, time_s: np.ndarray, path: Path) -> None:
    """Save F/F0 matrix as CSV: rows = frames, columns = TrackIDs, plus time_s."""
    out = ff0.T.reset_index()                   # transpose: frames as rows
    out.insert(1, "time_s", time_s.tolist())     # add time column
    out.to_csv(path, index=False)


def save_plot(ff0_mt: pd.DataFrame, ff0_other: pd.DataFrame,
              time_s: np.ndarray, path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))

    for ax, ff0, label, color in [
        (axes[0], ff0_mt,    "Mitochondria", "tab:orange"),
        (axes[1], ff0_other, "Cytosol",      "tab:blue"),
    ]:
        n = len(ff0)
        # Plot each cell as a thin semi-transparent line
        for _, trace in ff0.iterrows():
            ax.plot(time_s, trace.to_numpy(), color=color, linewidth=0.6, alpha=0.3)
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("F / F₀")
        ax.set_title(f"{label}  (n = {n} cells)")
        ax.axhline(1.0, color="gray", linewidth=0.8, linestyle="--")

    fig.suptitle(EXPERIMENT_DIR.name)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"Loading data from: {EXPERIMENT_DIR}")

    nuclei, roi, pos_mt, pos_other = load_tables(EXPERIMENT_DIR)

    print("Attaching TrackIDs...")
    roi = attach_track_ids(roi, nuclei)

    print("Filtering positive cells...")
    keep = get_positive_tracks(roi, pos_mt, pos_other)
    if not keep:
        raise SystemExit("No positive cells found — check your CellProfiler outputs.")

    df = roi[roi["TrackID"].isin(keep)]

    print("Building intensity matrices...")
    mat_mt    = build_matrix(df, keep, MT_COL)
    mat_other = build_matrix(df, keep, OTHER_COL)

    frames = mat_mt.columns.to_numpy()
    time_s = (frames - frames.min()) * FRAME_INTERVAL_S

    print("Normalising to F/F0...")
    ff0_mt    = normalise_ff0(mat_mt)
    ff0_other = normalise_ff0(mat_other)

    print(f"Saving outputs to: {OUTPUT_DIR}/")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    save_csv(ff0_mt,    time_s, OUTPUT_DIR / "FF0_mt.csv")
    save_csv(ff0_other, time_s, OUTPUT_DIR / "FF0_other.csv")
    save_plot(ff0_mt, ff0_other, time_s, OUTPUT_DIR / "traces.png")

    print("Done.")
    print(f"  FF0_mt.csv, FF0_other.csv, traces.png -> {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
