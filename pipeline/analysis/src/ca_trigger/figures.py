"""figures.py

Plotting utilities for Ca-trigger analysis.

- plot_single_experiment: mt + other for one experiment (mean ± SD across cells)
- plot_cell_lines:        mt comparison and other comparison across cell lines (mean ± SD across experiments)
- plot_photobleach_fit:   shows bleaching data and fitted curves

This file only consumes dictionaries produced by analysis_core.py.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Any

import matplotlib.pyplot as plt
import numpy as np

from ca_trigger.analysis_core import eval_bleach_curve


def plot_single_experiment(res: Dict, title: str, ylim: Optional[Tuple[float, float]] = None) -> plt.Figure:
    fig = plt.figure()
    t = res["time_s"]
    plt.plot(t, res["mt_mean"], label="mt")
    plt.fill_between(t, res["mt_mean"] - res["mt_std"], res["mt_mean"] + res["mt_std"], alpha=0.2)

    plt.plot(t, res["other_mean"], label="other")
    plt.fill_between(t, res["other_mean"] - res["other_std"], res["other_mean"] + res["other_std"], alpha=0.2)

    plt.title(title)
    plt.xlabel("Time (s)")
    plt.ylabel("F/F0")
    if ylim:
        plt.ylim(*ylim)
    plt.legend()
    plt.tight_layout()
    return fig


def plot_cell_lines(cell_line_results: List[Dict], title: str, ylim: Optional[Tuple[float, float]] = None) -> Tuple[plt.Figure, plt.Figure]:
    # mt
    fig_mt = plt.figure()
    for r in cell_line_results:
        t = r["time_s"]
        plt.plot(t, r["mt_mean"], label=f'{r["cell_line"]} (n={r["n_exp"]})')
        plt.fill_between(t, r["mt_mean"] - r["mt_std"], r["mt_mean"] + r["mt_std"], alpha=0.2)
    plt.title(title + " — mt")
    plt.xlabel("Time (s)")
    plt.ylabel("F/F0")
    if ylim:
        plt.ylim(*ylim)
    plt.legend()
    plt.tight_layout()

    # other
    fig_other = plt.figure()
    for r in cell_line_results:
        t = r["time_s"]
        plt.plot(t, r["other_mean"], label=f'{r["cell_line"]} (n={r["n_exp"]})')
        plt.fill_between(t, r["other_mean"] - r["other_std"], r["other_mean"] + r["other_std"], alpha=0.2)
    plt.title(title + " — other")
    plt.xlabel("Time (s)")
    plt.ylabel("F/F0")
    if ylim:
        plt.ylim(*ylim)
    plt.legend()
    plt.tight_layout()

    return fig_mt, fig_other


def plot_photobleach_fit(pb: Dict[str, Any], title: str = "Photobleach fit") -> plt.Figure:
    """Plot mt average bleaching and the other channel for each run, with fitted curves."""
    fig = plt.figure()
    t = pb["time_s"]

    # mt
    plt.plot(t, pb["mt_avg"], label="mt (avg data)")
    mt_curve = eval_bleach_curve(t, pb["mt_fit"])
    plt.plot(t, mt_curve, linestyle="--", label=f'mt fit ({pb["mt_fit"]["model"]})')

    # others
    for run_name, info in pb["runs"].items():
        lbl = info["other_label"]
        plt.plot(t, info["other_avg"], label=f"{lbl} (data)")
        curve = eval_bleach_curve(t, info["other_fit"])
        plt.plot(t, curve, linestyle="--", label=f"{lbl} fit ({info['other_fit']['model']})")

    plt.title(title)
    plt.xlabel("Time (s)")
    plt.ylabel("F/F0")
    plt.legend()
    plt.tight_layout()
    return fig
