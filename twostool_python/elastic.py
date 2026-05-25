"""Elastic period identification from stress-strain curves.

Translates Step 6 of the MATLAB algorithm: segments the time series into elastic
periods (head stays above preconsolidation threshold) and plastic transitions
(head drops below threshold → irreversible compaction).
"""

import numpy as np


def identify_elastic_periods(
    y1: np.ndarray,
    imax_final: np.ndarray,
    max_final: np.ndarray,
    hp_inicial: float,
    crecealinicio: bool,
) -> np.ndarray:
    """Segment the stress-strain curve into elastic periods.

    An elastic period is a time interval where the GWL head stays above the
    preconsolidation threshold (hp_inicial). When the head drops below this
    threshold, a plastic (irreversible) transition occurs and a new elastic
    period starts at the following peak.

    Parameters
    ----------
    y1 : np.ndarray
        GWL depth series (m).
    imax_final : np.ndarray
        Indices of accepted peaks (0-based), after x and y criteria.
    max_final : np.ndarray
        y-values at accepted peaks.
    hp_inicial : float
        Preconsolidation head — deepest GWL depth in the record.
    crecealinicio : bool
        True if the curve starts on a rising/loading limb.

    Returns
    -------
    tramoselasticos : np.ndarray, shape (n_periods, 2)
        Each row is [start_idx, end_idx] (0-based) for one elastic period.
    """
    n_peaks = len(imax_final)
    if n_peaks == 0:
        return np.array([[0, len(y1) - 1]])

    tramos = []

    # ── First elastic period: determine start ──────────────────────────
    ymax = max(hp_inicial, y1[0])
    contmax = 0  # tracks which peak defines the current ymax

    if not crecealinicio:
        # Curve starts falling — elastic starts at first data point
        tramos.append([0, None])
    else:
        # Curve starts rising — check if head is below preconsolidation
        if y1[0] < ymax:
            tramos.append([0, None])
        else:
            # Head above threshold → start first elastic at first peak
            tramos.append([int(imax_final[0]), None])
            contmax = 1
            if contmax < n_peaks:
                ymax = max_final[contmax]

    # ── First elastic period: determine end ────────────────────────────
    # Find first point where head crosses the threshold
    ja = np.where(y1 >= ymax)[0]
    flag_plastico = False

    if len(ja) == 0:
        # No crossing found → end at the next peak (or series end)
        if contmax < n_peaks:
            tramos[0][1] = int(imax_final[contmax])
            contmax += 1
        else:
            tramos[0][1] = len(y1) - 1
    else:
        next_peak_idx = int(imax_final[contmax]) if contmax < n_peaks else len(y1)
        if ja[0] <= next_peak_idx:
            # Head crosses threshold before the next peak → plastic transition
            tramos[0][1] = ja[0] - 1
            ymax = max_final[contmax] if contmax < n_peaks else hp_inicial
            flag_plastico = True
        else:
            # Reaches next peak before crossing → end there
            tramos[0][1] = next_peak_idx
            contmax += 1

    # ── Remaining elastic periods ──────────────────────────────────────
    MAX_ITER = 1000
    for _ in range(MAX_ITER):
        # Start of this elastic period
        if flag_plastico:
            # After plastic transition, new elastic starts at next peak
            if contmax >= n_peaks:
                break
            start = int(imax_final[contmax])
            ymax = max_final[contmax]
            contmax += 1
        else:
            # Continue from end of previous elastic period
            start = tramos[-1][1]

        # End of this elastic period
        ja = np.where(y1 > ymax)[0]

        if len(ja) == 0:
            alt1 = len(y1)
        else:
            alt1 = int(ja[0])

        if contmax >= n_peaks:
            # No more peaks — end at threshold crossing or series end
            end = min(alt1 - 1, len(y1) - 1) if alt1 < len(y1) else len(y1) - 1
        else:
            alt2 = int(imax_final[contmax])
            end = min(alt1 - 1, alt2)

        tramos.append([start, end])

        # Determine state for next iteration
        if end == alt1 - 1 and contmax < n_peaks:
            flag_plastico = True
            ymax = max_final[contmax]
        elif end == alt1 - 1 and contmax >= n_peaks:
            flag_plastico = True
            ymax = hp_inicial
            break
        elif contmax < n_peaks and end == int(imax_final[contmax]):
            contmax += 1
            flag_plastico = False
        else:
            # Reached end of series
            break
    else:
        pass  # MAX_ITER safety valve — should never trigger for real data

    return np.array(tramos, dtype=int)
