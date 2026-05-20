"""analysis_core.py

Refactored core analysis for Ca-trigger time-lapse experiments exported from CellProfiler.

This keeps the *features* of the original monolithic script, but separates:
  1) configuration (YAML)  -> run_analysis.py
  2) analysis logic        -> this file
  3) plotting              -> figures.py

Supported features (mirrors original script)
-------------------------------------------
- single experiment processing:
    * attach TrackID from nuclei to ROI table
    * attach positivity flags for mt + other channel
    * select tracks positive in BOTH (or EITHER) channels at any time
    * build TrackID x frame matrices (mt + other)
    * F/F0 normalisation (baseline frames configurable)
    * export plot-input matrices used for plotting
- cross-cell-line aggregation:
    * run multiple experiments per cell line
    * mean ± SD across experiments
    * optional export of per-cell long tables (for stats)
- photobleach fitting mode:
    * fit mt and other channel bleaching curves (linear or exp+offset)
    * optionally apply correction to traces

Notes
-----
- ROI choice is configurable. For NPC experiments you can set:
    roi_csv: MyExpt_CytoRing.csv  (CytoRing)  OR
    roi_csv: MyExpt_CellDisk.csv  (CellDisk)
  For Fib experiments typically:
    roi_csv: MyExpt_CellOutline.csv (CellOutline)

- ROI ↔ nuclei linking:
    * NPC-style exports usually share ObjectNumber with nuclei -> merge on (ImageNumber,ObjectNumber)
    * Fib-style ROI exports typically include Parent_Nuclei -> merge on (ImageNumber,Parent_Nuclei)
  This is handled by roi_link_strategy (auto/by_objectnumber/by_parent_nuclei).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Literal, Any

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit


TrackRule = Literal["both_channels_any_time", "either_channel_any_time"]
RoiLinkStrategy = Literal["auto", "by_objectnumber", "by_parent_nuclei"]
BleachModel = Literal["linear", "exp_offset"]


@dataclass
class ExperimentFiles:
    nuclei_csv: str = "MyExpt_Nuclei.csv"
    roi_csv: str = "MyExpt_CytoRing.csv"  # can be CellDisk / CellOutline
    pos_mt_csv: str = "MyExpt_PositiveCells_mt.csv"
    pos_other_csv: str = "MyExpt_PositiveCells_other.csv"
    image_csv: str = "MyExpt_Image.csv"   # optional


@dataclass
class ColumnNames:
    image_number: str = "ImageNumber"
    object_number: str = "ObjectNumber"
    track_id_col_prefix: str = "TrackObjects_Label"
    parent_nuclei: str = "Parent_Nuclei"
    mt_mean: str = "Intensity_MeanIntensity_BGS_mt"
    other_mean: str = "Intensity_MeanIntensity_BGS_other"


@dataclass
class ExportSettings:
    export_plot_inputs: bool = True
    export_into_experiment_folder: bool = True
    export_dirname: str = "_exports_plot_inputs"
    export_root: Optional[str] = None

    export_cell_line_tables: bool = False
    export_cell_line_dir: Optional[str] = None  # required if export_cell_line_tables=True


@dataclass
class PhotobleachSettings:
    enabled: bool = False
    model: BleachModel = "exp_offset"
    # If you already know parameters, you can set them here and skip fitting.
    # For exp_offset: [a, k, c] for c + a*exp(-k*t)
    # For linear: [a, b] for a + b*t
    mt_params: Optional[List[float]] = None
    other_params: Optional[List[float]] = None


@dataclass
class AnalysisSettings:
    frame_interval_s: float = 5.0
    baseline_frames: int = 5
    track_rule: TrackRule = "both_channels_any_time"
    roi_link_strategy: RoiLinkStrategy = "auto"
    photobleach: PhotobleachSettings = field(default_factory=PhotobleachSettings)


# ---------------------------
# Utilities
# ---------------------------

def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _find_track_column(df_nuc: pd.DataFrame) -> str:
    track_cols = [c for c in df_nuc.columns if c.startswith("TrackObjects_Label")]
    if not track_cols:
        raise RuntimeError("No TrackObjects_Label* column found in nuclei table.")
    track_cols_sorted = sorted(track_cols, key=lambda s: (len(s), s))
    return track_cols_sorted[0]


def attach_positive_flag(
    df: pd.DataFrame,
    df_pos: pd.DataFrame,
    flag_name: str,
    image_col: str,
    obj_col: str,
) -> pd.DataFrame:
    """Add boolean column: row is positive if (ImageNumber,ObjectNumber) occurs in df_pos."""
    pos_pairs = set(zip(df_pos[image_col].astype(int), df_pos[obj_col].astype(int)))
    df[flag_name] = [
        (int(im), int(obj)) in pos_pairs
        for im, obj in zip(df[image_col].astype(int), df[obj_col].astype(int))
    ]
    return df


def normalize_ff0(pivot: pd.DataFrame, n_baseline_frames: int) -> Tuple[pd.DataFrame, pd.Series]:
    if pivot.shape[1] < n_baseline_frames:
        raise ValueError(f"Not enough frames for baseline: have {pivot.shape[1]}, need {n_baseline_frames}")
    f0 = pivot.iloc[:, :n_baseline_frames].mean(axis=1)
    ff0 = pivot.div(f0, axis=0)
    return ff0, f0


def summarize_across_cells(ff0: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    mean = ff0.mean(axis=0).to_numpy()
    std = ff0.std(axis=0).to_numpy()
    return mean, std


def pivots_to_long_df(
    ff0_mt: pd.DataFrame,
    ff0_other: pd.DataFrame,
    time_s: np.ndarray,
    cell_line: str,
    experiment: str,
) -> pd.DataFrame:
    """Convert F/F0 matrices to long format for downstream stats."""
    mt_long = ff0_mt.reset_index().melt(id_vars="TrackID", var_name="Frame", value_name="FF0_mt")
    other_long = ff0_other.reset_index().melt(id_vars="TrackID", var_name="Frame", value_name="FF0_other")
    merged = mt_long.merge(other_long, on=["TrackID", "Frame"], how="inner")
    frame_to_time = dict(zip(sorted(ff0_mt.columns.to_list()), time_s))
    merged["time_s"] = merged["Frame"].map(frame_to_time)
    merged["cell_line"] = cell_line
    merged["experiment"] = experiment
    return merged


def get_export_dir(base_path: Path, exp_name: str, exports: ExportSettings) -> Path:
    if exports.export_into_experiment_folder:
        return base_path / exports.export_dirname
    if not exports.export_root:
        raise ValueError("export_root must be set if export_into_experiment_folder=False")
    return Path(exports.export_root) / exp_name


def save_ff0_matrices(
    export_dir: Path,
    exp_name: str,
    ff0_mt: pd.DataFrame,
    ff0_other: pd.DataFrame,
    time_s: np.ndarray,
) -> None:
    """
    Save normalised intensity matrices with time embedded.

    Output format (for both mt and other):
      - rows: frames (ImageNumber)
      - columns: TrackIDs
      - extra column: time_s

    This makes each CSV self-contained (no separate time-axis CSV needed).
    """
    ensure_dir(export_dir)

    def _export_one(ff0: pd.DataFrame, out_path: Path) -> None:
        # ff0 is TrackID x Frame -> transpose to Frame x TrackID
        out = ff0.T.copy()

        # Ensure frames are a column (not index) so we can add time_s cleanly
        out.index.name = "Frame"
        out = out.reset_index()

        # Add time_s (aligned to the sorted frame order)
        # time_s was built from the same frames used in ff0 columns
        out.insert(1, "time_s", np.asarray(time_s, dtype=float))

        # Save
        out.to_csv(out_path, index=False)

    _export_one(ff0_mt, export_dir / f"{exp_name}__FF0_mt.csv")
    _export_one(ff0_other, export_dir / f"{exp_name}__FF0_other.csv")


# ---------------------------
# ROI ↔ nuclei linking
# ---------------------------

def _link_roi_to_nuclei_trackids(df_roi: pd.DataFrame, df_nuc: pd.DataFrame, cols: ColumnNames, strategy: RoiLinkStrategy) -> pd.DataFrame:
    track_col = _find_track_column(df_nuc)
    df_nuc_track = df_nuc[[cols.image_number, cols.object_number, track_col]].copy()
    df_nuc_track = df_nuc_track.rename(columns={track_col: "TrackID"})

    has_parent = cols.parent_nuclei in df_roi.columns

    if strategy == "auto":
        strategy = "by_parent_nuclei" if has_parent else "by_objectnumber"

    if strategy == "by_parent_nuclei":
        if not has_parent:
            raise RuntimeError("ROI table has no Parent_Nuclei column, but strategy=by_parent_nuclei")
        merged = df_roi.merge(
            df_nuc_track,
            left_on=[cols.image_number, cols.parent_nuclei],
            right_on=[cols.image_number, cols.object_number],
            how="left",
            suffixes=("", "_nuc"),
        )
        merged = merged.drop(columns=[f"{cols.object_number}_nuc"], errors="ignore")
    else:
        merged = df_roi.merge(df_nuc_track, on=[cols.image_number, cols.object_number], how="left")

    return merged


# ---------------------------
# Photobleach models
# ---------------------------

def _model_linear(t: np.ndarray, a: float, b: float) -> np.ndarray:
    return a + b * t


def _model_exp_offset(t: np.ndarray, a: float, k: float, c: float) -> np.ndarray:
    return c + a * np.exp(-k * t)


def fit_bleach_curve(time_s: np.ndarray, y: np.ndarray, model: BleachModel) -> Dict[str, Any]:
    """Fit a photobleach curve in F/F0 space."""
    t = np.asarray(time_s, dtype=float)
    y = np.asarray(y, dtype=float)

    if model == "linear":
        p0 = [float(y[0]), (float(y[-1]) - float(y[0])) / max(float(t[-1]), 1.0)]
        popt, _ = curve_fit(_model_linear, t, y, p0=p0, maxfev=10000)
        return {"model": "linear", "params": popt.tolist()}

    c0 = float(y[-1])
    a0 = float(max(y[0] - c0, 1e-6))
    k0 = 1e-3
    p0 = [a0, k0, c0]
    bounds = ([0.0, 0.0, 0.0], [np.inf, np.inf, np.inf])
    popt, _ = curve_fit(_model_exp_offset, t, y, p0=p0, bounds=bounds, maxfev=20000)
    return {"model": "exp_offset", "params": popt.tolist()}


def eval_bleach_curve(time_s: np.ndarray, fit: Dict[str, Any]) -> np.ndarray:
    t = np.asarray(time_s, dtype=float)
    if fit["model"] == "linear":
        a, b = fit["params"]
        return _model_linear(t, a, b)
    a, k, c = fit["params"]
    return _model_exp_offset(t, a, k, c)


def apply_bleach_correction(ff0: pd.DataFrame, time_s: np.ndarray, fit: Dict[str, Any]) -> pd.DataFrame:
    b = eval_bleach_curve(time_s, fit)
    b = np.clip(b, 1e-6, np.inf)
    return ff0.div(b, axis=1)


# ---------------------------
# Main: run one experiment
# ---------------------------

def run_experiment(base_path: str | Path, exp_name: str, files: ExperimentFiles, cols: ColumnNames, settings: AnalysisSettings, exports: ExportSettings) -> Optional[Dict]:
    base_path = Path(base_path)

    df_nuc = pd.read_csv(base_path / files.nuclei_csv)
    df_roi = pd.read_csv(base_path / files.roi_csv)
    df_pos_mt = pd.read_csv(base_path / files.pos_mt_csv)
    df_pos_other = pd.read_csv(base_path / files.pos_other_csv)

    df_all = _link_roi_to_nuclei_trackids(df_roi, df_nuc, cols, settings.roi_link_strategy)
    frac = df_all["TrackID"].notna().mean()
    print(f"[{exp_name}] ROI rows with TrackID: {frac:.3f}")

    df_all = attach_positive_flag(df_all, df_pos_mt, "IsPositive_mt", cols.image_number, cols.object_number)
    df_all = attach_positive_flag(df_all, df_pos_other, "IsPositive_other", cols.image_number, cols.object_number)

    mt_tracks = df_all.loc[df_all["IsPositive_mt"], "TrackID"].dropna().unique()
    other_tracks = df_all.loc[df_all["IsPositive_other"], "TrackID"].dropna().unique()

    if settings.track_rule == "both_channels_any_time":
        keep_tracks = np.intersect1d(mt_tracks, other_tracks)
    else:
        keep_tracks = np.union1d(mt_tracks, other_tracks)

    print(f"[{exp_name}] tracks mt={len(mt_tracks)} other={len(other_tracks)} keep={len(keep_tracks)} rule={settings.track_rule}")
    if len(keep_tracks) == 0:
        return None

    df_keep = df_all[df_all["TrackID"].isin(keep_tracks)].copy()

    for required in (cols.mt_mean, cols.other_mean):
        if required not in df_keep.columns:
            raise RuntimeError(f"[{exp_name}] Missing column '{required}' in ROI table ({files.roi_csv}).")

    pivot_mt = df_keep.pivot_table(index="TrackID", columns=cols.image_number, values=cols.mt_mean).sort_index(axis=1)
    pivot_other = df_keep.pivot_table(index="TrackID", columns=cols.image_number, values=cols.other_mean).sort_index(axis=1)
    pivot_other = pivot_other.reindex(columns=pivot_mt.columns)

    frames = pivot_mt.columns.to_numpy()
    time_s = (frames - frames.min()) * float(settings.frame_interval_s)

    ff0_mt, f0_mt = normalize_ff0(pivot_mt, settings.baseline_frames)
    ff0_other, f0_other = normalize_ff0(pivot_other, settings.baseline_frames)

    bleach_fits = None
    if settings.photobleach.enabled:
        # Fit or use provided params, then correct
        if settings.photobleach.mt_params is not None:
            fit_mt = {"model": settings.photobleach.model, "params": settings.photobleach.mt_params}
        else:
            fit_mt = fit_bleach_curve(time_s, ff0_mt.mean(axis=0).to_numpy(), settings.photobleach.model)

        if settings.photobleach.other_params is not None:
            fit_other = {"model": settings.photobleach.model, "params": settings.photobleach.other_params}
        else:
            fit_other = fit_bleach_curve(time_s, ff0_other.mean(axis=0).to_numpy(), settings.photobleach.model)

        ff0_mt = apply_bleach_correction(ff0_mt, time_s, fit_mt)
        ff0_other = apply_bleach_correction(ff0_other, time_s, fit_other)
        bleach_fits = {"mt": fit_mt, "other": fit_other}

    mt_mean, mt_std = summarize_across_cells(ff0_mt)
    other_mean, other_std = summarize_across_cells(ff0_other)

    if exports.export_plot_inputs:
        export_dir = get_export_dir(base_path, exp_name, exports)
        save_ff0_matrices(export_dir, exp_name, ff0_mt, ff0_other, time_s)

    return {
        "name": exp_name,
        "time_s": time_s,
        "frames": frames,
        "mt_mean": mt_mean,
        "mt_std": mt_std,
        "other_mean": other_mean,
        "other_std": other_std,
        "ff0_mt": ff0_mt,
        "ff0_other": ff0_other,
        "f0_mt": f0_mt,
        "f0_other": f0_other,
        "keep_tracks": keep_tracks,
        "bleach_fits": bleach_fits,
    }


def run_cell_line(cell_line_name: str, experiment_paths: List[str], files: ExperimentFiles, cols: ColumnNames, settings: AnalysisSettings, exports: ExportSettings) -> Optional[Dict]:
    results = []
    long_tables = []

    if exports.export_cell_line_tables:
        if not exports.export_cell_line_dir:
            raise ValueError("export_cell_line_dir must be set if export_cell_line_tables=True")
        ensure_dir(Path(exports.export_cell_line_dir))

    for i, p in enumerate(experiment_paths, start=1):
        exp_name = f"{cell_line_name}_rep{i}"
        res = run_experiment(p, exp_name, files, cols, settings, exports)
        if res is None:
            continue
        results.append(res)

        if exports.export_cell_line_tables:
            long_tables.append(
                pivots_to_long_df(res["ff0_mt"], res["ff0_other"], res["time_s"], cell_line=cell_line_name, experiment=exp_name)
            )

    if not results:
        return None

    time0 = results[0]["time_s"]
    for r in results[1:]:
        if len(r["time_s"]) != len(time0) or not np.allclose(r["time_s"], time0):
            raise RuntimeError(f"[{cell_line_name}] Experiments have different time axes. (Alignment not implemented)")

    mt_stack = np.vstack([r["mt_mean"] for r in results])
    other_stack = np.vstack([r["other_mean"] for r in results])

    out = {
        "cell_line": cell_line_name,
        "time_s": time0,
        "mt_mean": mt_stack.mean(axis=0),
        "mt_std": mt_stack.std(axis=0),
        "other_mean": other_stack.mean(axis=0),
        "other_std": other_stack.std(axis=0),
        "n_exp": len(results),
    }

    if exports.export_cell_line_tables and long_tables:
        all_long = pd.concat(long_tables, ignore_index=True)
        all_long.to_csv(Path(exports.export_cell_line_dir) / f"{cell_line_name}__ALLCELLS_long.csv", index=False)

    return out


def run_photobleach_fit(
    runs: Dict[str, Dict[str, str]],
    files: ExperimentFiles,
    cols: ColumnNames,
    settings: AnalysisSettings,
    exports: ExportSettings,
    model: BleachModel = "exp_offset",
) -> Dict[str, Any]:
    """Fit bleach curves from dedicated photobleach runs.

    runs format:
      {
        "mt_cyt": {"path": "...", "other_label": "cyt"},
        "mt_er":  {"path": "...", "other_label": "er"}
      }

    Returns:
      {
        "time_s": ...,
        "mt_avg": ...,
        "mt_fit": {...},
        "runs": {
           "mt_cyt": {"other_label":"cyt","other_avg":...,"other_fit":...},
           ...
        }
      }
    """
    # disable correction during fitting
    settings_no_corr = AnalysisSettings(
        frame_interval_s=settings.frame_interval_s,
        baseline_frames=settings.baseline_frames,
        track_rule=settings.track_rule,
        roi_link_strategy=settings.roi_link_strategy,
        photobleach=PhotobleachSettings(enabled=False),
    )

    res_by_run = {}
    for run_name, spec in runs.items():
        res = run_experiment(spec["path"], run_name, files, cols, settings_no_corr, exports)
        if res is None:
            raise RuntimeError(f"[photobleach_fit] No valid tracks in run '{run_name}'")
        res_by_run[run_name] = res

    time_s = next(iter(res_by_run.values()))["time_s"]

    mt_means = np.vstack([r["ff0_mt"].mean(axis=0).to_numpy() for r in res_by_run.values()])
    mt_avg = mt_means.mean(axis=0)
    mt_fit = fit_bleach_curve(time_s, mt_avg, model)

    out: Dict[str, Any] = {"time_s": time_s, "mt_avg": mt_avg, "mt_fit": mt_fit, "runs": {}}

    for run_name, spec in runs.items():
        other_label = spec.get("other_label", run_name)
        other_avg = res_by_run[run_name]["ff0_other"].mean(axis=0).to_numpy()
        out["runs"][run_name] = {
            "other_label": other_label,
            "other_avg": other_avg,
            "other_fit": fit_bleach_curve(time_s, other_avg, model),
        }

    return out
