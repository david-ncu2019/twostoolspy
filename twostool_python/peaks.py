"""Peak and trough detection with x-interval and y-interval filtering.

Translates Steps 3-5 of the MATLAB algorithm:
  find_all_extrema       → raw peak/trough detection (Step 3)
  detect_boundary_trends → initial/final trend flags (Step 3)
  apply_x_criterion      → merge nearby peaks by displacement proximity (Step 4)
  apply_y_criterion      → keep only peaks with significant depth separation (Step 5)
"""

import numpy as np
from scipy.signal import find_peaks


def detect_boundary_trends(
    imax_ini: np.ndarray, imin_ini: np.ndarray
) -> tuple:
    """Determine whether the stress-strain curve starts/ends on a rising or falling limb.

    Parameters
    ----------
    imax_ini : np.ndarray
        Indices of all raw maxima (0-based).
    imin_ini : np.ndarray
        Indices of all raw minima (0-based).

    Returns
    -------
    crecealinicio : bool
        True if the first extremum is a peak (curve starts on loading/rising limb).
    crecealfinal : bool
        True if the last extremum is a minimum (curve ends on rising/loading limb).
    """
    crecealinicio = imax_ini[0] < imin_ini[0]
    crecealfinal = imax_ini[-1] < imin_ini[-1]
    return crecealinicio, crecealfinal


def find_all_extrema(y1: np.ndarray) -> dict:
    """Locate all local maxima and minima in the GWL depth series.

    Parameters
    ----------
    y1 : np.ndarray
        Groundwater depth values (m).

    Returns
    -------
    dict with keys:
        max_ini : np.ndarray — y-values at all local maxima
        imax_ini : np.ndarray — indices (0-based) of all local maxima
        min_ini : np.ndarray — y-values at all local minima
        imin_ini : np.ndarray — indices (0-based) of all local minima
    """
    imax_ini, _ = find_peaks(y1)
    max_ini = y1[imax_ini]

    imin_ini, _ = find_peaks(-y1)
    min_ini = y1[imin_ini]

    return {
        "max_ini": max_ini,
        "imax_ini": imax_ini,
        "min_ini": min_ini,
        "imin_ini": imin_ini,
    }


def apply_x_criterion(
    x1: np.ndarray,
    y1: np.ndarray,
    imax_ini: np.ndarray,
    imin_ini: np.ndarray,
    intervalo_x: float,
    crecealinicio: bool,
    crecealfinal: bool,
) -> dict:
    """Merge peaks that are closer than intervalo_x on the displacement axis.

    Groups peaks by proximity and keeps only the highest (largest y) in each group.
    Recomputes troughs to align with surviving peaks.

    Parameters
    ----------
    x1, y1 : np.ndarray
        Full displacement and GWL depth series.
    imax_ini : np.ndarray
        Indices of raw maxima (0-based).
    imin_ini : np.ndarray
        Indices of raw minima (0-based).
    intervalo_x : float
        Minimum displacement difference for two peaks to be distinct (m).
    crecealinicio : bool
        Whether the curve starts on a rising limb.
    crecealfinal : bool
        Whether the curve ends on a rising limb.

    Returns
    -------
    dict with keys:
        max_ini2 : np.ndarray — surviving peak y-values after x-criterion
        imax_ini2 : np.ndarray — surviving peak indices (0-based)
        min_ini2 : np.ndarray — recomputed trough y-values
        imin_ini2 : np.ndarray — recomputed trough indices (0-based)
        n2 : int — number of surviving peaks
    """
    n_peaks_raw = len(imax_ini)

    # Assign each peak to a group based on x-proximity
    xdemax_ini = x1[imax_ini]
    group_ids = np.zeros(n_peaks_raw, dtype=int)
    current_group = 0
    for i in range(n_peaks_raw - 1):
        group_ids[i] = current_group
        if abs(xdemax_ini[i] - xdemax_ini[i + 1]) > intervalo_x:
            current_group += 1
    group_ids[-1] = current_group

    # Keep the highest peak in each group
    n_groups = current_group + 1
    max_ini2 = np.zeros(n_groups)
    imax_ini2 = np.zeros(n_groups, dtype=int)
    for g in range(n_groups):
        mask = group_ids == g
        group_peaks = y1[imax_ini[mask]]
        best_local = np.argmax(group_peaks)
        best_global = np.where(mask)[0][best_local]
        max_ini2[g] = y1[imax_ini[best_global]]
        imax_ini2[g] = imax_ini[best_global]

    # Recompute troughs to align with surviving peaks
    min_ini2_list = []
    imin_ini2_list = []
    for i in range(len(imax_ini2) - 1):
        # Find minima between consecutive surviving peaks (0-based)
        mask = (imin_ini > imax_ini2[i]) & (imin_ini < imax_ini2[i + 1])
        if np.any(mask):
            best_local = np.argmin(y1[imin_ini[mask]])
            min_ini2_list.append(y1[imin_ini[mask]][best_local])
            imin_ini2_list.append(imin_ini[mask][best_local])

    min_ini2 = np.array(min_ini2_list)
    imin_ini2 = np.array(imin_ini2_list, dtype=int)

    # Prepend first trough if curve starts on falling limb
    if not crecealinicio:
        min_ini2 = np.concatenate([[y1[imin_ini[0]]], min_ini2])
        imin_ini2 = np.concatenate([[imin_ini[0]], imin_ini2])

    # Append last trough if curve ends on rising limb
    if crecealfinal:
        min_ini2 = np.concatenate([min_ini2, [y1[imin_ini[-1]]]])
        imin_ini2 = np.concatenate([imin_ini2, [imin_ini[-1]]])

    n2 = len(max_ini2)

    return {
        "max_ini2": max_ini2,
        "imax_ini2": imax_ini2,
        "min_ini2": min_ini2,
        "imin_ini2": imin_ini2,
        "n2": n2,
    }


def apply_y_criterion(
    x1: np.ndarray,
    y1: np.ndarray,
    max_ini2: np.ndarray,
    imax_ini2: np.ndarray,
    min_ini2: np.ndarray,
    imin_ini2: np.ndarray,
    intervalo_y: float,
    crecealinicio: bool,
    crecealfinal: bool,
) -> dict:
    """Filter peaks by vertical separation from neighbouring troughs.

    A peak survives only if its depth differs from BOTH neighbouring troughs
    by at least intervalo_y. The logic is asymmetric depending on whether the
    curve starts rising or falling.

    Parameters
    ----------
    x1, y1 : np.ndarray
        Full displacement and GWL depth series.
    max_ini2, imax_ini2 : np.ndarray
        Surviving peaks and indices after x-criterion.
    min_ini2, imin_ini2 : np.ndarray
        Troughs and indices after x-criterion.
    intervalo_y : float
        Minimum GWL depth difference (m).
    crecealinicio : bool
        Whether the curve starts on a rising limb.
    crecealfinal : bool
        Whether the curve ends on a rising limb.

    Returns
    -------
    dict with keys:
        max_final : np.ndarray — peaks surviving both x and y criteria
        imax_final : np.ndarray — indices (0-based) of surviving peaks
        min_final : np.ndarray — recomputed troughs aligned to final peaks
        imin_final : np.ndarray — indices (0-based) of final troughs
    """
    n2 = len(max_ini2)
    max_final_list = []
    imax_final_list = []

    if crecealinicio:
        # Curve starts rising — first peak must clear first trough
        if (max_ini2[0] - min_ini2[0] > intervalo_y) and \
           (max_ini2[0] - y1[0] > intervalo_y):
            max_final_list.append(max_ini2[0])
            imax_final_list.append(imax_ini2[0])

        # Intermediate peaks: must clear trough[i] and trough[i-1]
        for i in range(1, n2 - 1):
            if (max_ini2[i] - min_ini2[i] > intervalo_y) and \
               (max_ini2[i] - min_ini2[i - 1] > intervalo_y):
                max_final_list.append(max_ini2[i])
                imax_final_list.append(imax_ini2[i])

        # Last peak
        if crecealfinal:
            # Ends rising: last peak must clear trough[n2-2] and trough[n2-1]
            if (max_ini2[-1] - min_ini2[-2] > intervalo_y) and \
               (max_ini2[-1] - min_ini2[-1] > intervalo_y):
                max_final_list.append(max_ini2[-1])
                imax_final_list.append(imax_ini2[-1])
        else:
            # Ends falling: last peak must clear second-to-last trough and final y
            if (max_ini2[-1] - min_ini2[-2] > intervalo_y) and \
               (max_ini2[-1] - y1[-1] > intervalo_y):
                max_final_list.append(max_ini2[-1])
                imax_final_list.append(imax_ini2[-1])
    else:
        # Curve starts falling — first peak must clear trough[0] and trough[1]
        if (max_ini2[0] - min_ini2[0] > intervalo_y) and \
           (max_ini2[0] - min_ini2[1] > intervalo_y):
            max_final_list.append(max_ini2[0])
            imax_final_list.append(imax_ini2[0])

        # Intermediate peaks: must clear trough[i] and trough[i+1]
        for i in range(1, n2 - 1):
            if (max_ini2[i] - min_ini2[i] > intervalo_y) and \
               (max_ini2[i] - min_ini2[i + 1] > intervalo_y):
                max_final_list.append(max_ini2[i])
                imax_final_list.append(imax_ini2[i])

        # Last peak
        if crecealfinal:
            # Ends rising
            if (max_ini2[-1] - min_ini2[-2] > intervalo_y) and \
               (max_ini2[-1] - min_ini2[-1] > intervalo_y):
                max_final_list.append(max_ini2[-1])
                imax_final_list.append(imax_ini2[-1])
        else:
            # Ends falling
            if (max_ini2[-1] - min_ini2[-2] > intervalo_y) and \
               (max_ini2[-1] - y1[-1] > intervalo_y):
                max_final_list.append(max_ini2[-1])
                imax_final_list.append(imax_ini2[-1])

    max_final = np.array(max_final_list)
    imax_final = np.array(imax_final_list, dtype=int)
    xdemax_final = x1[imax_final]

    # Recompute troughs aligned to final peaks
    min_final_list = []
    imin_final_list = []
    for i in range(len(imax_final) - 1):
        mask = (imin_ini2 > imax_final[i]) & (imin_ini2 < imax_final[i + 1])
        if np.any(mask):
            best_local = np.argmin(y1[imin_ini2[mask]])
            min_final_list.append(y1[imin_ini2[mask]][best_local])
            imin_final_list.append(imin_ini2[mask][best_local])

    min_final = np.array(min_final_list)
    imin_final = np.array(imin_final_list, dtype=int)

    # Prepend first trough if curve starts falling
    if not crecealinicio:
        mask_before = imin_ini2 < imax_final[0]
        if np.any(mask_before):
            best_local = np.argmin(y1[imin_ini2[mask_before]])
            min_final = np.concatenate([[y1[imin_ini2[mask_before]][best_local]], min_final])
            imin_final = np.concatenate([[imin_ini2[mask_before][best_local]], imin_final])

    # Append last trough if curve ends rising
    if crecealfinal:
        mask_after = imin_ini2 > imax_final[-1]
        if np.any(mask_after):
            best_local = np.argmin(y1[imin_ini2[mask_after]])
            min_final = np.concatenate([min_final, [y1[imin_ini2[mask_after]][best_local]]])
            imin_final = np.concatenate([imin_final, [imin_ini2[mask_after][best_local]]])

    return {
        "max_final": max_final,
        "imax_final": imax_final,
        "xdemax_final": xdemax_final,
        "min_final": min_final,
        "imin_final": imin_final,
    }
