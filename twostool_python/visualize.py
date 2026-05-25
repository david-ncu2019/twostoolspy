"""Figure generation for 2S-TOOL stress-strain analysis.

Saves figures in all formats listed in config.FIGURE_FORMATS (default: PNG + TIFF).
PNG is prioritized for quick preview; TIFF at 600 dpi for publication.

Uses matplotlib OO API (not pyplot state machine) and Agg backend for headless
operation. All figures use reversed x-axis (right = more compaction).
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

from .config import FIGURE_DPI, FIGURE_FORMATS, FIGURE_WIDTH_MM, FIGURE_HEIGHT_MM, FIGURE_FONT_SIZE


def _figure_size() -> tuple[float, float]:
    """Return figure size in inches from config mm values."""
    return (FIGURE_WIDTH_MM / 25.4, FIGURE_HEIGHT_MM / 25.4)


def _journal_style(ax: plt.Axes) -> None:
    """Apply journal figure style rules."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="x", rotation=70)
    for label in ax.get_xticklabels():
        label.set_ha("center")


def _config_legend(ax: plt.Axes, **kwargs) -> None:
    """Add legend with journal defaults: no frame, upper right,
    and 2 columns when 4+ elements."""
    handles, labels = ax.get_legend_handles_labels()
    ncol = 2 if len(handles) > 3 else 1
    ax.legend(
        handles, labels,
        loc="upper right",
        frameon=False,
        ncol=ncol,
        fontsize=FIGURE_FONT_SIZE,
        **kwargs,
    )


def _save_figure(fig, stem: Path) -> None:
    """Save a matplotlib figure in all configured formats.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
    stem : Path
        Output path without extension.
    """
    for fmt in FIGURE_FORMATS:
        if fmt == "tiff":
            fig.savefig(
                str(stem) + ".tif", dpi=FIGURE_DPI, format="tiff",
                pil_kwargs={"compression": "tiff_lzw"},
            )
        else:
            fig.savefig(
                str(stem) + "." + fmt, dpi=FIGURE_DPI, format=fmt,
            )


def plot_skv_figure(
    x1: np.ndarray,
    y1: np.ndarray,
    x_est: np.ndarray,
    y_est: np.ndarray,
    skv: float,
    out_stem: str | Path,
) -> None:
    """Figure 2: Full stress-strain cloud with S_kv envelope line.

    Parameters
    ----------
    x1, y1 : np.ndarray
        Full displacement (m) and GWL depth (m) data.
    x_est, y_est : np.ndarray
        Two-point envelope line endpoints.
    skv : float
        Anelastic storage coefficient.
    out_stem : str or Path
        Output path without extension.
    """
    fig, ax = plt.subplots(figsize=_figure_size(), dpi=100)
    ax.invert_xaxis()
    _journal_style(ax)

    ax.plot(x1, y1, "k", linewidth=0.5, label="Observed")
    ax.plot(x_est, y_est, "k--", linewidth=1.5, label=r"Fitted $s_{kv}$")

    ax.set_xlabel("Ground displacement (m)")
    ax.set_ylabel("Groundwater depth (m)")

    # S_kv text box
    text_str = f"$s_{{kv}}$ = {skv:10.3e}"
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    ax.text(
        xlim[1] - 0.05 * (xlim[1] - xlim[0]),
        ylim[0] + 0.10 * (ylim[1] - ylim[0]),
        text_str,
        bbox={"boxstyle": "square", "facecolor": "white", "edgecolor": "black"},
    )

    _config_legend(ax)
    fig.tight_layout()
    _save_figure(fig, Path(out_stem))
    plt.close(fig)


def plot_peaks_figure(
    x1: np.ndarray,
    y1: np.ndarray,
    x_est: np.ndarray,
    y_est: np.ndarray,
    skv: float,
    imax_ini2: np.ndarray,
    imin_ini2: np.ndarray,
    imax_final: np.ndarray,
    imin_final: np.ndarray,
    out_stem: str | Path,
) -> None:
    """Figure 2 v2: Stress-strain cloud with peak/trough markers.

    Shows which peaks survived the x-criterion (transparent markers) and which
    also survived the y-criterion (filled markers).

    Parameters
    ----------
    out_stem : str or Path
        Output path without extension.
    """
    fig, ax = plt.subplots(figsize=_figure_size(), dpi=100)
    ax.invert_xaxis()
    _journal_style(ax)

    ax.plot(x1, y1, "k", linewidth=0.5, label="Observed")
    ax.plot(x_est, y_est, "k--", linewidth=1.5, label=r"Fitted $s_{kv}$")

    # Peaks/troughs after x-criterion only (transparent)
    ax.scatter(
        x1[imax_ini2], y1[imax_ini2],
        marker="d", edgecolors="blue", facecolors="none", alpha=0.3, s=30,
        label=r"Peaks ($\Delta$x)",
    )
    ax.scatter(
        x1[imin_ini2], y1[imin_ini2],
        marker="d", edgecolors="red", facecolors="none", alpha=0.3, s=30,
        label=r"Troughs ($\Delta$x)",
    )

    # Peaks/troughs after x and y criteria (filled)
    ax.scatter(
        x1[imax_final], y1[imax_final],
        marker="d", edgecolors="blue", facecolors="blue", alpha=1.0, s=30,
        label=r"Peaks ($\Delta$x,$\Delta$y)",
    )
    ax.scatter(
        x1[imin_final], y1[imin_final],
        marker="d", edgecolors="red", facecolors="red", alpha=1.0, s=30,
        label=r"Troughs ($\Delta$x,$\Delta$y)",
    )

    ax.set_xlabel("Ground displacement (m)")
    ax.set_ylabel("Groundwater depth (m)")

    # S_kv text box
    text_str = f"$s_{{kv}}$ = {skv:10.3e}"
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    ax.text(
        xlim[1] - 0.05 * (xlim[1] - xlim[0]),
        ylim[0] + 0.10 * (ylim[1] - ylim[0]),
        text_str,
        bbox={"boxstyle": "square", "facecolor": "white", "edgecolor": "black"},
    )

    _config_legend(ax)
    fig.tight_layout()
    _save_figure(fig, Path(out_stem))
    plt.close(fig)


def plot_ske_figure(
    x1: np.ndarray,
    y1: np.ndarray,
    tramoselasticos: np.ndarray,
    AjusTramElas: np.ndarray,
    xdemax_final: np.ndarray,
    max_final: np.ndarray,
    ske_stats: dict,
    out_stem: str | Path,
) -> None:
    """Figure 3: Elastic loops colour-coded with accepted/rejected S_ke fits.

    Parameters
    ----------
    out_stem : str or Path
        Output path without extension.
    """
    fig, ax = plt.subplots(figsize=_figure_size(), dpi=100)
    ax.invert_xaxis()
    _journal_style(ax)

    ax.plot(x1, y1, color="0.5", linewidth=0.1)

    ax.scatter(xdemax_final, max_final, marker="d", edgecolors="blue",
               facecolors="none", alpha=0.3, s=30)

    ax.set_xlabel("Ground displacement (m)")
    ax.set_ylabel("Groundwater depth (m)")

    colors = plt.cm.tab10(np.linspace(0, 1, max(len(tramoselasticos), 1)))
    has_accepted = False
    has_rejected = False
    accepted_handle = None
    rejected_handle = None

    for i in range(len(tramoselasticos)):
        start, end = tramoselasticos[i]
        color = colors[i % 10]

        ax.plot(x1[start:end + 1], y1[start:end + 1],
                color=color, linewidth=1.5)

        if not np.isnan(AjusTramElas[i, 0]):
            if AjusTramElas[i, 9] == 1:
                linecolor = "black"
                lw = 1.5
                if not has_accepted:
                    accepted_handle = plt.Line2D(
                        [0], [0], color="black", linestyle="--", linewidth=1.5)
                    has_accepted = True
            else:
                linecolor = "red"
                lw = 1.5
                if not has_rejected:
                    rejected_handle = plt.Line2D(
                        [0], [0], color="red", linestyle="--", linewidth=1.5)
                    has_rejected = True

            ax.plot(AjusTramElas[i, 2:4], AjusTramElas[i, 4:6],
                    linestyle="--", color=linecolor, linewidth=lw)

    handles = []
    labels = []
    if has_accepted:
        handles.append(accepted_handle)
        labels.append(r"Accepted $s_{ke}$")
    if has_rejected:
        handles.append(rejected_handle)
        labels.append("Discarded")
    if handles:
        ncol = 2 if len(handles) > 3 else 1
        ax.legend(handles, labels, loc="upper right", frameon=False,
                  ncol=ncol, fontsize=FIGURE_FONT_SIZE)

    ske_mean = ske_stats.get("ske_mean")
    ske_weighted = ske_stats.get("ske_weighted")
    n_accepted = ske_stats.get("n_accepted", 0)

    if ske_mean is not None and n_accepted > 0:
        if n_accepted == 1:
            text_str = (
                f"$s_{{ke}}$ = {ske_mean:10.3e} ($\\sigma$ = 0)\n"
                f"$s_{{ke\\ weighted}}$ = {ske_weighted:10.3e}"
            )
        else:
            ske_std = ske_stats.get("ske_std", 0)
            text_str = (
                f"$s_{{ke}}$ = {ske_mean:10.3e} ($\\sigma$ = {ske_std:10.3e})\n"
                f"$s_{{ke\\ weighted}}$ = {ske_weighted:10.3e}"
            )
        ax.text(
            0.98, 0.08, text_str,
            transform=ax.transAxes, ha="right", va="bottom",
            bbox={"boxstyle": "square", "facecolor": "white", "edgecolor": "black"},
            fontsize=9,
        )

    fig.tight_layout()
    _save_figure(fig, Path(out_stem))
    plt.close(fig)
