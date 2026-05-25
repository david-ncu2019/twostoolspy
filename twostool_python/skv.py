"""S_kv (anelastic storage coefficient) computation.

Fits a straight line through all (displacement, GWL depth) data points.
S_kv = -1 / slope.
"""

import numpy as np


def compute_skv(x1: np.ndarray, y1: np.ndarray) -> dict:
    """Compute the anelastic skeletal storage coefficient from full-cloud linear fit.

    Parameters
    ----------
    x1 : np.ndarray
        Ground displacement (m).
    y1 : np.ndarray
        Groundwater depth (m).

    Returns
    -------
    dict with keys:
        skv : float — anelastic storage coefficient (-1/slope)
        slope : float — fitted slope
        intercept : float — fitted intercept
        x_est : np.ndarray — [min(x1), max(x1)]
        y_est : np.ndarray — fitted y at x_est endpoints
    """
    slope, intercept = np.polyfit(x1, y1, 1)
    skv = -1.0 / slope
    x_est = np.array([np.min(x1), np.max(x1)])
    y_est = np.polyval([slope, intercept], x_est)
    return {
        "skv": skv,
        "slope": slope,
        "intercept": intercept,
        "x_est": x_est,
        "y_est": y_est,
    }
