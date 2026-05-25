"""Pipeline orchestrator for 2S-TOOL Part 2 analysis.

Runs the full 12-step pipeline on a single stress-strain curve input file:
  1. Read input Excel
  2. Compute S_kv (full-cloud linear fit)
  3. Auto-determine parameters from data
  4. Find all local extrema
  5. Apply x-interval criterion
  6. Apply y-interval criterion
  7. Identify elastic periods
  8. Fit S_ke for each elastic loop
  9. Reject small loops
  10. Aggregate S_ke statistics
  11. Generate 3 TIFF figures
  12. Write 3 CSV outputs
"""

import json
import logging
from pathlib import Path

import numpy as np

from . import config
from .io_utils import read_excel_input, write_outputs
from .skv import compute_skv
from .peaks import (
    detect_boundary_trends,
    find_all_extrema,
    apply_x_criterion,
    apply_y_criterion,
)
from .elastic import identify_elastic_periods
from .ske import fit_ske_loops, reject_small_loops, aggregate_ske_stats
from .visualize import plot_skv_figure, plot_peaks_figure, plot_ske_figure

logger = logging.getLogger(__name__)


def run_pipeline(
    input_path: str | Path,
    output_dir: str | Path,
) -> dict:
    """Run the full 2S-TOOL Part 2 pipeline on a single input file.

    Parameters
    ----------
    input_path : str or Path
        Path to the input .xlsx file.
    output_dir : str or Path
        Directory for per-file output subfolder.

    Returns
    -------
    dict with keys:
        status : str — "ok", "skv_only", or "error"
        summary : dict — aggregated results
        out_dir : str — per-file output subfolder path
    """
    input_path = Path(input_path)
    output_dir = Path(output_dir)

    # ── Step 0: Read input ─────────────────────────────────────────────
    data = read_excel_input(input_path)
    x1 = data["x1"]
    y1 = data["y1"]
    basename = data["filename"]

    out_subdir = output_dir / basename
    out_subdir.mkdir(parents=True, exist_ok=True)

    logger.info(f"{basename}: {len(x1)} points, "
                f"disp=[{x1.min():.4f}, {x1.max():.4f}] m, "
                f"depth=[{y1.min():.2f}, {y1.max():.2f}] m")

    # ── Step 1: Compute S_kv ───────────────────────────────────────────
    skv_result = compute_skv(x1, y1)
    skv = skv_result["skv"]
    x_est = skv_result["x_est"]
    y_est = skv_result["y_est"]

    # ── Step 2: Auto-determine parameters ──────────────────────────────
    intervalo_y = config.INTERVALO_Y_FRACTION * (np.max(y1) - np.min(y1))
    intervalo_x = config.INTERVALO_X_FRACTION * (np.max(x1) - np.min(x1))
    hp_inicial = config.HP_INICIAL_DEFAULT
    if hp_inicial is None and config.HP_INICIAL_OVERRIDES_PATH:
        overrides_file = Path(config.HP_INICIAL_OVERRIDES_PATH)
        if overrides_file.exists():
            with open(overrides_file) as f:
                overrides = json.load(f)
            stem = basename  # e.g. "2STOOL_TUKU_F1"
            if stem in overrides:
                hp_inicial = overrides[stem]
    if hp_inicial is None:
        hp_inicial = float(np.max(y1))
    porcentaje = config.PORCENTAJE

    logger.info(f"  auto-params: intervalo_y={intervalo_y:.3f}, "
                f"intervalo_x={intervalo_x:.5f}, hp_inicial={hp_inicial:.2f}")

    # ── Fig02: S_kv figure (always generated) ──────────────────────────
    plot_skv_figure(x1, y1, x_est, y_est, skv,
                    out_subdir / f"{basename}_Fig02_skv_jva")

    # ── Step 3: Find all local extrema ─────────────────────────────────
    extrema = find_all_extrema(y1)
    max_ini = extrema["max_ini"]
    imax_ini = extrema["imax_ini"]
    min_ini = extrema["min_ini"]
    imin_ini = extrema["imin_ini"]

    crecealinicio, crecealfinal = detect_boundary_trends(imax_ini, imin_ini)

    # ── Step 4: Apply x-interval criterion ─────────────────────────────
    x_result = apply_x_criterion(
        x1, y1, imax_ini, imin_ini, intervalo_x,
        crecealinicio, crecealfinal,
    )
    n2 = x_result["n2"]
    max_ini2 = x_result["max_ini2"]
    imax_ini2 = x_result["imax_ini2"]
    min_ini2 = x_result["min_ini2"]
    imin_ini2 = x_result["imin_ini2"]

    # ── Early-exit guard: too few peaks for elastic analysis ───────────
    # Python improvement beyond MATLAB: explicit guard with clean CSV output.
    if n2 < 2:
        logger.warning(f"  Only {n2} peak(s) after x-criterion — "
                       "insufficient for elastic cycle analysis. Writing S_kv-only output.")

        AjusTramElas = np.zeros((0, 11))
        tramoselasticos = np.zeros((0, 2), dtype=int)
        empty_stats = {
            "ske_weighted": None, "ske_mean": None, "ske_std": None,
            "ske_min": None, "ske_max": None,
            "n_loops_total": 0, "n_accepted": 0,
        }

        write_outputs(
            out_subdir, basename, x1, y1, skv, empty_stats,
            None, None, intervalo_y, intervalo_x, hp_inicial, porcentaje,
        )
        return {"status": "skv_only", "summary": {"skv": skv, **empty_stats},
                "out_dir": str(out_subdir)}

    # ── Step 5: Apply y-interval criterion ─────────────────────────────
    y_result = apply_y_criterion(
        x1, y1, max_ini2, imax_ini2, min_ini2, imin_ini2,
        intervalo_y, crecealinicio, crecealfinal,
    )
    max_final = y_result["max_final"]
    imax_final = y_result["imax_final"]
    min_final = y_result["min_final"]
    imin_final = y_result["imin_final"]
    xdemax_final = y_result["xdemax_final"]

    # ── Fig02 v2: Peaks figure ────────────────────────────────────────
    plot_peaks_figure(
        x1, y1, x_est, y_est, skv,
        imax_ini2, imin_ini2, imax_final, imin_final,
        out_subdir / f"{basename}_Fig02_skv_jva_v2",
    )

    # ── Step 6: Identify elastic periods ───────────────────────────────
    tramoselasticos = identify_elastic_periods(
        y1, imax_final, max_final, hp_inicial, crecealinicio,
    )

    # ── Steps 7-8: Fit S_ke + reject small loops ───────────────────────
    AjusTramElas = fit_ske_loops(x1, y1, tramoselasticos)
    reject_small_loops(AjusTramElas, porcentaje)

    # ── Step 9: Aggregate S_ke statistics ──────────────────────────────
    ske_stats = aggregate_ske_stats(AjusTramElas)

    # ── Fig03: S_ke figure ─────────────────────────────────────────────
    plot_ske_figure(
        x1, y1, tramoselasticos, AjusTramElas,
        xdemax_final, max_final, ske_stats,
        out_subdir / f"{basename}_Fig03_ske_jva",
    )

    # ── Step 11: Write CSV outputs ─────────────────────────────────────
    write_outputs(
        out_subdir, basename, x1, y1, skv, ske_stats,
        AjusTramElas, tramoselasticos,
        intervalo_y, intervalo_x, hp_inicial, porcentaje,
    )

    logger.info(f"  s_kv={skv:.4e}, s_ke(weighted)={ske_stats['ske_weighted']}, "
                f"loops={ske_stats['n_accepted']}/{ske_stats['n_loops_total']}")

    return {
        "status": "ok",
        "summary": {"skv": skv, **ske_stats},
        "out_dir": str(out_subdir),
    }
