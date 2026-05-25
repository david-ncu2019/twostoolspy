"""S_ke (elastic storage coefficient) loop fitting and aggregation.

Translates Steps 7-9 of the MATLAB algorithm:
  fit_ske_loops         → fit S_ke for each elastic loop (Step 7)
  reject_small_loops    → discard loops < 20% of max amplitude (Step 8)
  aggregate_ske_stats   → weighted mean, std, min/max (Step 9)
"""

import numpy as np


def fit_ske_loops(
    x1: np.ndarray,
    y1: np.ndarray,
    tramoselasticos: np.ndarray,
) -> np.ndarray:
    """Fit S_ke for each elastic period.

    For each elastic period, finds the trough (minimum GWL depth), extracts the
    loading limb from trough to end, and fits a straight line. S_ke = -1/slope.

    Pre-allocates 11 columns (MATLAB bug fix: MATLAB pre-allocated only 5).

    Parameters
    ----------
    x1 : np.ndarray
        Ground displacement (m).
    y1 : np.ndarray
        Groundwater depth (m).
    tramoselasticos : np.ndarray, shape (n_periods, 2)
        Elastic period [start, end] indices (0-based).

    Returns
    -------
    AjusTramElas : np.ndarray, shape (n_periods, 11)
        Columns (0-based):
            0  — slope
            1  — intercept
            2  — x_start (m)
            3  — x_end (m)
            4  — y_fit_start (m)
            5  — y_fit_end (m)
            6  — delta_x (horizontal amplitude, m)
            7  — delta_y (vertical amplitude, m)
            8  — n_pts (points in the fit segment)
            9  — accepted (1 = accepted, 0 = rejected)
            10 — s_ke (elastic storage coefficient, = -1/slope)
    """
    n_periods = len(tramoselasticos)
    # Pre-allocate 11 columns (fixing MATLAB's 5-column pre-allocation bug)
    AjusTramElas = np.full((n_periods, 11), np.nan)

    for i in range(n_periods):
        start, end = tramoselasticos[i]
        tempx = x1[start:end + 1]
        tempy = y1[start:end + 1]

        # Find trough (minimum GWL depth within the elastic period)
        trough_idx = int(np.argmin(tempy))

        # Extract loading limb: from trough to end
        tempx3 = tempx[trough_idx:]
        tempy3 = tempy[trough_idx:]

        # Skip single-point segments — leave row as NaN
        if len(tempy3) <= 1:
            continue

        # Linear fit
        slope, intercept = np.polyfit(tempx3, tempy3, 1)
        x_fit_start = float(np.min(tempx3))
        x_fit_end = float(np.max(tempx3))
        y_fit = np.polyval([slope, intercept], [x_fit_start, x_fit_end])

        AjusTramElas[i, 0] = slope
        AjusTramElas[i, 1] = intercept
        AjusTramElas[i, 2] = x_fit_start
        AjusTramElas[i, 3] = x_fit_end
        AjusTramElas[i, 4] = y_fit[0]
        AjusTramElas[i, 5] = y_fit[1]
        AjusTramElas[i, 6] = x_fit_end - x_fit_start
        AjusTramElas[i, 7] = np.max(tempy3) - np.min(tempy3)
        AjusTramElas[i, 8] = len(tempx3)

        # Accept if slope <= 0 (negative slope = loading limb has physically
        # correct sign: displacement more negative while depth increases).
        # Positive slope on loading limb is physically impossible.
        if slope > 0:
            AjusTramElas[i, 9] = 0  # rejected — positive slope
        else:
            AjusTramElas[i, 9] = 1  # accepted

        AjusTramElas[i, 10] = -1.0 / slope

    return AjusTramElas


def reject_small_loops(AjusTramElas: np.ndarray, porcentaje: float) -> None:
    """Reject loops whose vertical amplitude is less than `porcentaje` of the largest.

    Modifies AjusTramElas in-place, setting column 9 (accepted) to 0 for small loops.

    Parameters
    ----------
    AjusTramElas : np.ndarray, shape (n_loops, 11)
        Loop-fitting array (modified in-place).
    porcentaje : float
        Fraction of max amplitude below which loops are rejected (e.g. 0.2).
    """
    valid = ~np.isnan(AjusTramElas[:, 7])
    if not np.any(valid):
        return
    max_amplitude = np.nanmax(AjusTramElas[:, 7])
    if max_amplitude <= 0:
        return
    threshold = porcentaje * max_amplitude
    small = AjusTramElas[:, 7] < threshold
    AjusTramElas[small, 9] = 0


def aggregate_ske_stats(AjusTramElas: np.ndarray) -> dict:
    """Compute aggregate S_ke statistics from all loops.

    Uses boolean masking (not row deletion) for the weighted mean, fixing the
    MATLAB approach of deleting rows then multiplying by the acceptance flag.

    Parameters
    ----------
    AjusTramElas : np.ndarray, shape (n_loops, 11)
        Loop-fitting array.

    Returns
    -------
    dict with keys:
        ske_weighted : float or None — amplitude-weighted mean S_ke
        ske_mean : float or None — arithmetic mean S_ke (accepted only)
        ske_std : float or None — std of accepted S_ke values
        ske_min : float or None
        ske_max : float or None
        n_loops_total : int
        n_accepted : int
    """
    n_total = len(AjusTramElas)  # all rows, matching MATLAB size(AjusTramElas,1)
    accepted_mask = AjusTramElas[:, 9] == 1
    n_accepted = int(np.sum(accepted_mask))

    if n_accepted == 0:
        return {
            "ske_weighted": None,
            "ske_mean": None,
            "ske_std": None,
            "ske_min": None,
            "ske_max": None,
            "n_loops_total": n_total,
            "n_accepted": 0,
        }

    ske_vals = AjusTramElas[accepted_mask, 10]
    amplitudes = AjusTramElas[accepted_mask, 7]

    # Amplitude-weighted mean (masked, no row deletion)
    ske_weighted = float(np.sum(ske_vals * amplitudes) / np.sum(amplitudes))

    ske_mean = float(np.mean(ske_vals))
    ske_std = float(np.std(ske_vals, ddof=1))  # ddof=1 matches MATLAB's std() default
    ske_min = float(np.min(ske_vals))
    ske_max = float(np.max(ske_vals))

    return {
        "ske_weighted": ske_weighted,
        "ske_mean": ske_mean,
        "ske_std": ske_std,
        "ske_min": ske_min,
        "ske_max": ske_max,
        "n_loops_total": n_total,
        "n_accepted": n_accepted,
    }
