"""run_analysis.py

Entry point for the refactored Ca-trigger analysis.

Usage
-----
python run_analysis.py --config config.yaml --outdir results

Supported modes (set in YAML)
----------------------------
- single_experiment
- cross_cell_lines
- photobleach_fit

This file is intentionally thin: it just loads config, calls analysis_core, and calls figures.py.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict

import yaml

from ca_trigger.analysis_core import (
    AnalysisSettings,
    ColumnNames,
    ExperimentFiles,
    ExportSettings,
    PhotobleachSettings,
    run_experiment,
    run_cell_line,
    run_photobleach_fit,
)
from ca_trigger.figures import plot_single_experiment, plot_cell_lines, plot_photobleach_fit

def _expand_paths(config: dict) -> dict:
    """
    Expands {base_dir} placeholders and ~ in all experiment paths.

    Example:
      base_dir: "/Users/me/Experiments/cellprofiler_outputs"
      "{base_dir}/2025_exp1" -> "/Users/me/Experiments/cellprofiler_outputs/2025_exp1"
    """
    base_dir = config.get("base_dir", "")
    if base_dir:
        base_dir = str(Path(base_dir).expanduser())

    expanded = dict(config)  # shallow copy
    if "cell_lines" not in expanded:
        return expanded

    new_cell_lines = {}
    for cell_line, paths in expanded["cell_lines"].items():
        new_paths = []
        for p in paths:
            p2 = p
            if base_dir:
                p2 = p2.replace("{base_dir}", base_dir)
            p2 = str(Path(p2).expanduser())
            new_paths.append(p2)
        new_cell_lines[cell_line] = new_paths

    expanded["cell_lines"] = new_cell_lines
    expanded["base_dir"] = base_dir
    return expanded

def _build_settings(cfg: Dict[str, Any]) -> tuple[ExperimentFiles, ColumnNames, ExportSettings, AnalysisSettings]:
    files = ExperimentFiles(**cfg.get("files", {}))
    cols = ColumnNames(**cfg.get("columns", {}))
    exports = ExportSettings(**cfg.get("exports", {}))

    analysis_cfg = cfg.get("analysis", {}).copy()

    # nested photobleach settings
    pb_cfg = analysis_cfg.pop("photobleach", {}) or {}
    photobleach = PhotobleachSettings(**pb_cfg)

    settings = AnalysisSettings(photobleach=photobleach, **analysis_cfg)

    return files, cols, exports, settings


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="Path to YAML config")
    ap.add_argument("--outdir", default="results", help="Where to save figures")
    args = ap.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text())
    cfg = _expand_paths(cfg)

    files, cols, exports, settings = _build_settings(cfg)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    mode = cfg.get("mode", "cross_cell_lines")
    ylim = tuple(cfg.get("ylim", [])) or None

    if mode == "single_experiment":
        exp = cfg["single_experiment"]
        res = run_experiment(exp["path"], exp.get("name", "Exp1"), files, cols, settings, exports)
        if res is None:
            raise SystemExit("No valid tracks.")
        fig = plot_single_experiment(res, title=exp.get("name", "Experiment"), ylim=ylim)
        fig.savefig(outdir / "single_experiment.png", dpi=200)

    elif mode == "cross_cell_lines":
        results = []
        for cl_name, paths in cfg["cell_lines"].items():
            r = run_cell_line(cl_name, paths, files, cols, settings, exports)
            if r is not None:
                results.append(r)
        if not results:
            raise SystemExit("No valid cell lines.")
        fig_mt, fig_other = plot_cell_lines(results, title=cfg.get("title", "Cross cell-line comparison"), ylim=ylim)
        fig_mt.savefig(outdir / "cross_cell_lines_mt.png", dpi=200)
        fig_other.savefig(outdir / "cross_cell_lines_other.png", dpi=200)

    elif mode == "photobleach_fit":
        runs = cfg["photobleach_runs"]
        model = cfg.get("photobleach_model", "exp_offset")
        pb = run_photobleach_fit(runs, files, cols, settings, exports, model=model)
        fig = plot_photobleach_fit(pb, title=cfg.get("title", "Photobleach fit"))
        fig.savefig(outdir / "photobleach_fit.png", dpi=200)

        # also save fitted parameters as YAML
        (outdir / "photobleach_fit_params.yaml").write_text(yaml.safe_dump(pb, sort_keys=False))

    else:
        raise SystemExit(f"Unknown mode: {mode}")


if __name__ == "__main__":
    main()
