"""Excel input reading and output writing for 2S-TOOL.

Reads stress-strain curve data from Excel and writes machine-readable output:
  CSV — _sscurve.csv, _loops.csv, _summary.csv (for collect_2stool_results.py)
  JSON — _loops.json, _summary.json (for cross-tool consumption)
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path


def read_excel_input(filepath: str | Path) -> dict:
    """Read a 2S-TOOL input Excel file.

    Reads the StrainStress sheet (columns B and C, skipping row 1 for header).
    Optionally reads parameter overrides from the InputData sheet if populated.

    Parameters
    ----------
    filepath : str or Path
        Path to the .xlsx file.

    Returns
    -------
    dict with keys:
        x1 : np.ndarray — ground displacement (m), NaN-free
        y1 : np.ndarray — groundwater depth (m), NaN-free
        filename : str — stem of the input file (e.g. "2STOOL_TUKU_F1")
        params : dict — parameter overrides from InputData sheet (empty if absent)
    """
    filepath = Path(filepath)
    filename = filepath.stem

    # Read StrainStress sheet — columns B (idx 1) and C (idx 2), skip row 1
    sheet = pd.read_excel(filepath, sheet_name="StrainStress", header=None)
    x1 = sheet.iloc[1:, 1].dropna().to_numpy(dtype=float)
    y1 = sheet.iloc[1:, 2].dropna().to_numpy(dtype=float)

    if len(x1) != len(y1):
        raise ValueError(
            f"Length mismatch: {len(x1)} displacement values vs {len(y1)} GWL depth values"
        )

    # Read optional parameter overrides from InputData sheet
    params = _read_inputdata_sheet(filepath)

    return {"x1": x1, "y1": y1, "filename": filename, "params": params}


def _read_inputdata_sheet(filepath: Path) -> dict:
    """Read parameter overrides from the InputData sheet if present.

    The sheet may contain station-specific calibration values for:
    intervalo_y, intervalo_x, hp_inicial, porcentaje.

    Returns empty dict if the sheet is absent or empty.
    """
    try:
        xl = pd.ExcelFile(filepath)
    except Exception:
        return {}

    if "InputData" not in xl.sheet_names:
        return {}

    try:
        df = pd.read_excel(filepath, sheet_name="InputData", header=None)
    except Exception:
        return {}

    if df.empty:
        return {}

    params = {}
    # InputData sheet is created empty by prepare_2stool_inputs.py.
    # No station-specific overrides are currently written there.
    # If future scripts populate this sheet, add parsing logic here.
    return params


def write_outputs(
    out_dir: str | Path,
    basename: str,
    x1: np.ndarray,
    y1: np.ndarray,
    skv: float,
    ske_stats: dict,
    AjusTramElas: np.ndarray | None,
    tramoselasticos: np.ndarray | None,
    intervalo_y: float,
    intervalo_x: float,
    hp_inicial: float,
    porcentaje: float,
) -> None:
    """Write CSV and JSON output files for a 2S-TOOL run.

    Produces:
      _sscurve.csv   — full stress-strain curve (one row per observation)
      _loops.csv     — one row per identified elastic loop
      _loops.json    — same, as an array of loop objects
      _summary.csv   — one-row run summary
      _summary.json  — same, as a flat dict

    Parameters
    ----------
    out_dir : str or Path
        Output directory (per-file subfolder).
    basename : str
        Stem of the input file (e.g. "2STOOL_TUKU_F1").
    x1, y1 : np.ndarray
        Full stress-strain curve data.
    skv : float
        Anelastic storage coefficient.
    ske_stats : dict
        Aggregated S_ke statistics from aggregate_ske_stats().
    AjusTramElas : np.ndarray or None
        Loop-fitting array, shape (n_loops, 11). None when no loops found.
    tramoselasticos : np.ndarray or None
        Elastic period index ranges, shape (n_periods, 2). None when no loops.
    intervalo_y, intervalo_x, hp_inicial, porcentaje : float
        Analysis parameters used.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # --- _sscurve.csv ---
    sscurve_df = pd.DataFrame({
        "index": np.arange(1, len(x1) + 1),
        "disp_m": x1,
        "gwl_depth_m": y1,
    })
    sscurve_df.to_csv(out_dir / f"{basename}_sscurve.csv", index=False)

    # --- _loops (CSV + JSON) ---
    loops_records = []
    if AjusTramElas is not None and tramoselasticos is not None and len(AjusTramElas) > 0:
        n_loops = len(AjusTramElas)
        loops_df = pd.DataFrame({
            "loop_id": np.arange(1, n_loops + 1),
            "slope": AjusTramElas[:, 0],
            "intercept": AjusTramElas[:, 1],
            "x_start": AjusTramElas[:, 2],
            "x_end": AjusTramElas[:, 3],
            "y_fit_start": AjusTramElas[:, 4],
            "y_fit_end": AjusTramElas[:, 5],
            "delta_x_m": AjusTramElas[:, 6],
            "delta_y_m": AjusTramElas[:, 7],
            "n_pts": np.where(np.isnan(AjusTramElas[:, 8]), 0, AjusTramElas[:, 8]).astype(int),
            "accepted": np.where(np.isnan(AjusTramElas[:, 9]), 0, AjusTramElas[:, 9]).astype(int),
            "s_ke": AjusTramElas[:, 10],
            "start_idx": tramoselasticos[:, 0].astype(int) + 1,  # 1-based for CSV
            "end_idx": tramoselasticos[:, 1].astype(int) + 1,
        })
        loops_df.to_csv(out_dir / f"{basename}_loops.csv", index=False)

        # Build JSON-serializable records (NaN → null)
        for i in range(n_loops):
            rec = {
                "loop_id": i + 1,
                "slope": _json_float(AjusTramElas[i, 0]),
                "intercept": _json_float(AjusTramElas[i, 1]),
                "x_start": _json_float(AjusTramElas[i, 2]),
                "x_end": _json_float(AjusTramElas[i, 3]),
                "y_fit_start": _json_float(AjusTramElas[i, 4]),
                "y_fit_end": _json_float(AjusTramElas[i, 5]),
                "delta_x_m": _json_float(AjusTramElas[i, 6]),
                "delta_y_m": _json_float(AjusTramElas[i, 7]),
                "n_pts": int(AjusTramElas[i, 8]) if not np.isnan(AjusTramElas[i, 8]) else 0,
                "accepted": int(AjusTramElas[i, 9]) if not np.isnan(AjusTramElas[i, 9]) else 0,
                "s_ke": _json_float(AjusTramElas[i, 10]),
                "start_idx": int(tramoselasticos[i, 0]) + 1,
                "end_idx": int(tramoselasticos[i, 1]) + 1,
            }
            loops_records.append(rec)
    else:
        loops_df = pd.DataFrame(columns=[
            "loop_id", "slope", "intercept", "x_start", "x_end",
            "y_fit_start", "y_fit_end", "delta_x_m", "delta_y_m",
            "n_pts", "accepted", "s_ke", "start_idx", "end_idx",
        ])
        loops_df.to_csv(out_dir / f"{basename}_loops.csv", index=False)

    with open(out_dir / f"{basename}_loops.json", "w") as f:
        json.dump(loops_records, f, indent=2)

    # --- _summary (CSV + JSON) ---
    summary_record = {
        "file": basename,
        "skv": skv,
        "ske_max": ske_stats.get("ske_max"),
        "ske_mean": ske_stats.get("ske_mean"),
        "ske_min": ske_stats.get("ske_min"),
        "ske_weighted": ske_stats.get("ske_weighted"),
        "ske_std": ske_stats.get("ske_std"),
        "n_loops_total": ske_stats.get("n_loops_total", 0),
        "n_loops_accepted": ske_stats.get("n_accepted", 0),
        "y_interval": intervalo_y,
        "x_interval": intervalo_x,
        "hc": hp_inicial,
        "pct_amplitude": porcentaje,
    }
    summary_df = pd.DataFrame([summary_record])
    summary_df.to_csv(out_dir / f"{basename}_summary.csv", index=False)

    with open(out_dir / f"{basename}_summary.json", "w") as f:
        json.dump(summary_record, f, indent=2)


def _json_float(value: float) -> float | None:
    """Convert numpy float to JSON-safe float (NaN → null)."""
    if np.isnan(value):
        return None
    return float(value)
