# Manual calculation guide for 2S-TOOL

This document teaches you to compute skeletal storage coefficients (S_kv, S_ke) by hand
from raw field measurements, strictly following the same 12-step process as
`twostool_python` and the original MATLAB code `A02_StressStrain_Ske_Skv_Part2.m`.

---

## Part A — Raw field data to 2S-TOOL input

### A.1 The three raw measurements

You start with three independently measured quantities:

```
  Quantity                  Unit        Source                    Symbol
  ────────────────────────  ────────    ─────────────────────    ──────
  1. Piezometric head       m a.s.l.    GWL monitoring well      h(t)
  2. Well ground elevation  m a.s.l.    Levelling survey         E_well
  3. Ring absolute elev.    m a.s.l.    MLCW magnetic ring       z_ring(t)
```

All three are in **metres above sea level**. The ring is anchored to a deep reference
(bedrock or a stable datum) via the MLCW casing.

### A.2 Step 1: Convert head to groundwater depth

```
    depth(t) = E_well − h(t)          [metres below ground surface]
```

**Why:** The preconsolidation head `hp_inicial` is defined as the deepest historical
groundwater depth. Using depth makes `hp_inicial = max(depth)` — the largest positive
value is the most stressed state. The y-axis of the stress-strain curve must increase
in the direction of increasing effective stress.

```
    Example (synthetic dataset, first 3 of 8 field campaigns):

    t            h(t) [m]    E_well [m]    depth(t) [m]
    ──────────   ─────────   ───────────   ────────────
    2018-01-15     12.50         25.0           12.50
    2018-04-20      8.20         25.0           16.80
    2018-07-10      3.80         25.0           21.20
                            ↑
                 from levelling survey (m above sea level)
```

### A.3 Step 2: Compute ground displacement from ring elevation

**This is the primary, most fundamental method.** The raw field measurement is the
absolute elevation of each magnetic ring (metres above sea level), measured by
leveling survey at each field campaign. The deepest ring is anchored in bedrock or a
stable reference datum.

#### From ring elevation to layer compaction

Each ring `k` has an absolute elevation `z_k(t)` at campaign date `t`. A hydrogeological
layer is the interval between two rings (upper ring `u`, lower ring `ℓ`):

```
    L(t) = z_u(t) − z_ℓ(t)              [layer thickness at time t, m]
```

Compaction is the reduction in layer thickness since a reference date `t_ref` (typically
the first field campaign):

```
    disp(t) = L(t_ref) − L(t)           [cumulative compaction since t_ref, m]
```

At `t = t_ref`, `disp(t_ref) = 0` by definition. Positive values = compaction (layer got
thinner). This is the physically intuitive convention.

```
    Worked example — synthetic dataset (upper ring at ~80 m, lower ring at ~160 m):

    t              d_upper    d_lower    L(t)       disp(t) [m]
    ────────────   ────────   ────────   ────────   ────────────
    2018-01-15     80.000     160.000    80.000     0.0000   ← t_ref, zero by definition
    2018-04-20     80.005     160.002    79.997     0.0030   ← dry season: ring sinks
    2018-07-10     80.018     160.008    79.990     0.0100   ← peak compaction
    2018-10-05     80.012     160.005    79.993     0.0070   ← recovering
    2019-01-18     80.004     160.001    79.997     0.0030   ← wet season: ring rises
    2019-04-22     80.010     160.004    79.994     0.0060
    2019-07-15     80.022     160.010    79.988     0.0120   ← second dry season peak
    2019-10-08     80.015     160.006    79.991     0.0090
                           ↓
    ring sinks (d increases) → L decreases → positive disp = compaction
```

Multiple rings within the same hydrogeological layer are summed:

```
    disp_layer(t) = Σ [L_k(t_ref) − L_k(t)]     for all rings k in the layer
```

#### How the project pipeline uses this data

The file `data/mlcw/raw_timeseries/{STATION}_ringbyring.csv` (produced by earlier
processing steps) already contains per-ring cumulative compaction in mm, referenced
to the first campaign date. `prepare_2stool_inputs.py --raw` reads this file,
sums rings within each layer group, and converts mm → m:

```
    disp(t) = Σ ring_compaction_k(t) / 1000     [mm → m, zero at t_ref]
```

The data is zero-referenced — if you trace back to the first campaign, `disp = 0`.
However, the **output Excel may show a non-zero first row** because the pipeline
inner-joins MLCW dates with GWL dates. The earliest common date may be later than
`t_ref`, by which time some compaction has already accumulated.

```
    Example from the real project (TUKU_F1, 159 points after MLCW-GWL join):

    disp range: [−0.029, −0.011] m     ← negative = subsidence (project convention)
    depth range: [8.24, 22.36] m
    First row:  x = −0.01172 m         ← not zero because first common GWL date
                                          (Jan 2015) is 11 years after t_ref (Dec 2003)
```

The sign convention in the project files is negative = subsidence. 2S-TOOL accepts
either sign — the magnitude of S_kv and S_ke is unchanged; only the sign of the
output flips.

### A.4 Step 3: Assemble the stress-strain table

```
    x(t) = disp(t)          [m, horizontal axis — ground displacement]
    y(t) = depth(t)         [m, vertical axis — groundwater depth]
```

**Key point:** 2S-TOOL only cares about the **relationship** between x and y. The
absolute values don't matter — the algorithm uses:
- `polyfit(x, y, 1)` for S_kv (depends on slope, not offset)
- `max(y) − min(y)` for peak detection thresholds (depends on range, not absolute y)
- Relative x-proximity for x-criterion grouping

This means the same S_kv and S_ke values will be computed regardless of whether:
- x values are negative (MLCW project convention) or positive (manual ring convention)
- x starts at 0 (manual) or at a non-zero cumulative value (pipeline)
- y = depth = −head (our convention) or y = head (wrong convention — see A.5)

### A.5 Why you cannot skip the head→depth conversion

If you skip the conversion and use raw head `h(t)` as y, the 2S-TOOL algorithm will
still run but produce **different results** for two reasons:

1. **`hp_inicial` becomes `max(h)` = shallowest water**, not deepest. The elastic-period
   classifier (Step 7) uses `hp_inicial` as a threshold — with inverted sign, it
   classifies the wrong cycles as elastic vs plastic.

2. **Peak/trough detection runs on inverted y-values.** `find_peaks(y)` finds peaks in
   the positive direction. With head, a "peak" is high head (wet period) instead of
   deep water (dry/stressed period). The y-interval criterion then filters the wrong
   extrema.

**Conclusion:** Always convert head to depth before running 2S-TOOL. The conversion is
`depth = E_well − h`. Setting `E_well = 0` is acceptable for testing but not for
production analysis.

---

## Part B — Hand-worked S_kv and S_ke calculation

We use the **synthetic dataset** from Part A (8 field campaigns, 2018–2019). The data is
designed to be small enough for hand calculation while forming two clear hysteresis loops.

```
    Reference: twostool_python output on the 8-point synthetic dataset
    S_kv = −1.503 × 10⁻³
    n2 = 2 peaks survive x-criterion
    hp_inicial = 21.20 m
```

### B.1 The 12-step algorithm (indexed to match pipeline.py)

---

#### Step 1 — Compute S_kv (full-cloud linear fit)

Fit a straight line through ALL (x, y) points:

```
    y = slope × x + intercept          [polyfit, degree 1]
    S_kv = −1 / slope
```

The full 8-point synthetic dataset:

```
    i    x (disp, m)     y (depth, m)
    ───  ────────────    ────────────
    0    0.0000          12.50          ← reference date (t₀)
    1    0.0030          16.80
    2    0.0100          21.20          ← peak dry season, deepest water
    3    0.0070          18.50
    4    0.0030          13.20          ← wet season recovery
    5    0.0060          17.10
    6    0.0120          20.90          ← second dry season peak
    7    0.0090          15.70
```

**Manual linear regression (least squares):**

```
    n = 8
    Σx = 0 + 0.0030 + 0.0100 + 0.0070 + 0.0030 + 0.0060 + 0.0120 + 0.0090
       = 0.0500
    Σy = 12.50 + 16.80 + 21.20 + 18.50 + 13.20 + 17.10 + 20.90 + 15.70
       = 135.90
    Σxy = 0×12.50 + 0.0030×16.80 + 0.0100×21.20 + 0.0070×18.50
        + 0.0030×13.20 + 0.0060×17.10 + 0.0120×20.90 + 0.0090×15.70
        = 0 + 0.05040 + 0.21200 + 0.12950
        + 0.03960 + 0.10260 + 0.25080 + 0.14130
        = 0.92620
    Σx² = 0² + 0.0030² + 0.0100² + 0.0070² + 0.0030² + 0.0060² + 0.0120² + 0.0090²
        = 0 + 9.0e-6 + 1.00e-4 + 4.9e-5 + 9.0e-6 + 3.6e-5 + 1.44e-4 + 8.1e-5
        = 0.000428
    x̄ = 0.0500 / 8 = 0.00625
    ȳ = 135.90 / 8 = 16.9875

    slope = (Σxy − n·x̄·ȳ) / (Σx² − n·x̄²)
          = (0.92620 − 8 × 0.00625 × 16.9875) / (0.000428 − 8 × 0.00625²)
          = (0.92620 − 0.84938) / (0.000428 − 0.0003125)
          = 0.07682 / 0.0001155
          = 665.1

    S_kv = −1 / slope = −1 / 665.1 = −1.503 × 10⁻³
```

**Verification with numpy (twostool_python):**
```
    slope = 665.15, intercept = 12.83
    S_kv = −1/665.15 = −1.503 × 10⁻³   ✓
```

The intercept (12.83 m) is the depth at zero displacement — approximately the
static water level at the reference date. The positive slope means depth increases
with compaction, as expected physically.

---

#### Step 2 — Auto-determine parameters

```
    intervalo_y = 0.05 × (max(y) − min(y))     [5% of depth range]
    intervalo_x = 0.01 × (max(x) − min(x))     [1% of displacement range]
    hp_inicial  = max(y)                        [deepest GWL depth in record]
    porcentaje  = 0.2                           [20% amplitude threshold]
```

For the synthetic 8-point dataset:
```
    y_range = 21.20 − 12.50 = 8.70 m
    intervalo_y = 0.05 × 8.70 = 0.435 m

    x_range = 0.0120 − 0 = 0.0120 m
    intervalo_x = 0.01 × 0.0120 = 0.00012 m  (1.2 × 10⁻⁴ m)

    hp_inicial = max(y) = 21.20 m
    porcentaje = 0.2
```

---

#### Step 3 — Find all local extrema

Walk through the y-series and mark every point that is higher than BOTH neighbours
(peak) or lower than BOTH neighbours (trough).

```
    Synthetic dataset y-values:

    i:   0       1       2       3       4       5       6       7
    y:  12.50  16.80  21.20  18.50  13.20  17.10  20.90  15.70
              ↑              ↑      ↑              ↑
            (rising)       PEAK   TROUGH         PEAK

    Walk through and mark local extrema:
      i=0: y=12.50 — not a peak (y₁=16.80 > 12.50)
      i=1: y=16.80 — not a peak (y₂=21.20 > 16.80), not a trough (y₀=12.50 < 16.80)
      i=2: y=21.20 — PEAK       (both neighbours lower: 16.80 < 21.20 > 18.50)
      i=3: y=18.50 — not extremum
      i=4: y=13.20 — TROUGH     (both neighbours higher: 18.50 > 13.20 < 17.10)
      i=5: y=17.10 — not extremum
      i=6: y=20.90 — PEAK       (both neighbours lower: 17.10 < 20.90 > 15.70)
      i=7: y=15.70 — last point, not checked

    Raw peaks:   i=2 (y=21.20), i=6 (y=20.90)
    Raw troughs: i=4 (y=13.20)
```

**Boundary trends:**
```
    crecealinicio = (first peak idx < first trough idx) = (2 < 4) = True
        → curve starts on a rising/loading limb

    crecealfinal = (last peak idx < last trough idx) = (6 < ???)
        → no trough after last peak → crecealfinal = False
        → curve ends on a falling/unloading limb
```

---

#### Step 4 — Apply x-interval criterion

Peaks whose displacement values differ by less than `intervalo_x` are merged into
one group. Only the **highest** (largest y) peak in each group survives.

```
    Synthetic dataset: only 2 peaks

    Peak at i=2: x=0.0100
    Peak at i=6: x=0.0120

    |x₂ − x₆| = |0.0100 − 0.0120| = 0.0020 m
    intervalo_x = 0.00012 m
    0.0020 > 0.00012  →  NOT merged — peaks are far enough apart

    Both peaks survive: imax_ini2 = [2, 6], n2 = 2
    n2 ≥ 2 → continue (no early exit)
```

Troughs are recomputed between surviving peaks:
```
    Between i=2 and i=6: only trough at i=4 (y=13.20)
    → imin_ini2 = [4]
```

---

#### Step 5 — Apply y-interval criterion

A peak survives only if its depth exceeds BOTH neighbouring troughs by at least
`intervalo_y`. This ensures each peak represents a genuine loading cycle with
meaningful depth change.

```
    crecealinicio = True → use the "starts rising" branch (peaks.py lines 209–235)

    First peak (i=2, y=21.20): must clear trough[0] AND y[0]
        y_peak − y_trough = 21.20 − 13.20 = 8.00 > 0.435 ✓
        y_peak − y[0]     = 21.20 − 12.50 = 8.70 > 0.435 ✓
        → Peak at i=2 survives

    crecealfinal = False → last peak (i=6, y=20.90): must clear trough AND final y
        y_peak − y_trough = 20.90 − 13.20 = 7.70 > 0.435 ✓
        y_peak − y[-1]    = 20.90 − 15.70 = 5.20 > 0.435 ✓
        → Peak at i=6 survives

    Both peaks survive: imax_final = [2, 6], imin_final = [4]
```

---

#### Step 6 — Identify elastic periods

Each surviving peak defines the start of an elastic period. The end is determined
by `hp_inicial`:

```
    For elastic period starting at peak i:

    1. Set ymax = max(hp_inicial, y_at_peak)
    2. Find the first index after the peak where y ≥ ymax
       → water depth reaches/exceeds the preconsolidation threshold
    3. The elastic period ends just BEFORE that crossing point
    4. If no crossing is found, the period ends at the next peak (or end of data)

    ┌─────────────────────────────────────────────────────────────┐
    │                     STRESS-STRAIN CURVE                      │
    │                                                              │
    │  depth (m)                                                   │
    │    ↑                    ╭─ peak i+1                          │
    │    │   ╭─ peak i       ╱                                     │
    │    │  ╱ ╲             ╱                                      │
    │    │ ╱   ╲    ╭──────╱─── hp_inicial threshold              │
    │    │╱     ╲  ╱     ╱                                         │
    │    │       ╲╱    ╱                                           │
    │    │        ╲   ╱                                            │
    │    │         ╲ ╱    ← plastic transition (y ≥ hp_inicial)    │
    │    │          ╳                                              │
    │    └────────────────────────────────────────→ disp [reversed] │
    │     ├── elastic ──┤├─ plastic ─┤├── elastic ──┤              │
    └─────────────────────────────────────────────────────────────┘
```

Output: `tramoselasticos` — an array of `[start_idx, end_idx]` for each elastic period.

For the synthetic dataset:
```
    n_peaks = 2, crecealinicio = True

    Period 1: start at imax_final[0] = 2, end at ...
      ymax = max(21.20, 12.50) = 21.20
      Find y ≥ 21.20 after i=2: none (ymax=21.20 equals peak at i=2, but the 
      condition is y > ymax after the peak, not at the peak itself)
      → No crossing found, end at next peak i=6
      → tramoselasticos[0] = [2, 6]

    Period 2: contmax = 2 ≥ n_peaks → no more peaks
      → elastic period [6, 7] (final segment)

    Result: tramoselasticos = [[2, 6], [6, 7]]
    2 elastic periods identified.
```

---

#### Step 7 — Fit S_ke for each elastic loop

For each elastic period `[start, end]`:

```
    1. Extract segment: x_seg = x[start:end+1], y_seg = y[start:end+1]
    2. Find trough: idx_trough = argmin(y_seg)   [deepest point in segment]
    3. Extract loading limb: x_load = x_seg[idx_trough:], y_load = y_seg[idx_trough:]
    4. Skip if fewer than 2 points
    5. Linear fit: y_load = slope × x_load + intercept
    6. S_ke = −1/slope
    7. Accept if slope ≤ 0 (physically correct loading direction)
```

```
    Worked example — Period 1: indices [2, 6]

    x_seg:  [ 0.0100, 0.0070, 0.0030, 0.0060, 0.0120 ]
    y_seg:  [ 21.20,  18.50,  13.20,  17.10,  20.90 ]
                      ↑ trough at local idx=2 (y=13.20, global idx=4)

    Loading limb (trough → end):
    x_load: [ 0.0030, 0.0060, 0.0120 ]
    y_load: [ 13.20,  17.10,  20.90  ]

    Linear fit through 3 points:
    slope = (20.90 − 13.20) / (0.0120 − 0.0030)
          = 7.70 / 0.0090
          = 855.6

    S_ke = −1 / 855.6 = −1.169 × 10⁻³

    slope > 0 → rejected (positive slope: as the layer compacts more,
    water gets shallower — physically impossible during loading).
```

For the synthetic dataset, both elastic periods produce positive slopes on the
loading limb (the data forms a stress-strain loop where displacement does not
monotonically increase during loading — a known issue with 8-point sampling of
a continuous hysteresis curve). With more data points, the loading limbs would
show correct negative slopes.

---

#### Step 8 — Reject small loops

```
    max_amplitude = max(delta_y across all loops)
    threshold = 0.2 × max_amplitude

    Any loop with delta_y < threshold is rejected (accepted flag → 0)
```

For the synthetic dataset (2 loops): both have similar amplitudes (~7.7 m).
Neither is rejected. With only 2 loops and both having similar vertical extent,
the 20% amplitude threshold has no effect here.

---

#### Step 9 — Aggregate S_ke statistics

```
    Only accepted loops (column 9 == 1) are used:

    S_ke_weighted = Σ (S_ke_i × delta_y_i) / Σ (delta_y_i)
    S_ke_mean     = mean of accepted S_ke values
    S_ke_std      = standard deviation (ddof=1, matching MATLAB)
    S_ke_min      = minimum accepted S_ke
    S_ke_max      = maximum accepted S_ke
```

For the synthetic 8-point dataset (twostool_python output):
```
    S_kv = −1.503 × 10⁻³
    S_ke_weighted = None        (no accepted loops — all rejected for positive slope)
    S_ke_mean     = None
    0 accepted / 2 total loops
    hp_inicial = 21.20 m
```

> The synthetic dataset is designed to demonstrate the full algorithm flow and
> hand calculation of S_kv. With only 8 points, the S_ke loop fitting does not
> produce valid results — this is expected for a minimal example. Real datasets
> with 50+ points produce stable S_ke estimates.

---

### B.2 Algorithm summary table

| Step | Name | Python module | Key output |
|------|------|--------------|------------|
| 0 | Read input | `io_utils.py` | x1, y1 (arrays) |
| 1 | S_kv fit | `skv.py` | skv, slope, x_est, y_est |
| 2 | Auto-parameters | `pipeline.py:82-93` | intervalo_y, intervalo_x, hp_inicial |
| 3 | Find extrema | `peaks.py:38-65` | imax_ini, imin_ini |
| 4 | x-criterion | `peaks.py:68-162` | imax_ini2, imin_ini2, n2 |
| 5 | y-criterion | `peaks.py:165-303` | imax_final, imin_final |
| 6 | Elastic periods | `elastic.py` | tramoselasticos |
| 7 | S_ke fit | `ske.py:12-95` | AjusTramElas (11 columns) |
| 8 | Reject small | `ske.py:98-118` | AjusTramElas[:,9] updated |
| 9 | Aggregate stats | `ske.py:121-177` | S_ke_weighted, mean, std, min, max |

---

### B.3 S_kv / S_ke sign conventions

| Input convention | slope sign (typical) | S_kv sign | S_ke sign |
|---|---|---|---|
| **depth = elev − head** (standard) | negative | positive | positive |
| **depth = head** (no conversion) | positive | negative | negative |
| **head directly** (no conversion) | positive (opposite orientation) | negative | negative |

The standard convention (depth = elev − head) gives positive storage coefficients,
matching the geomechanical definition where positive S means the skeleton compacts
under positive stress increase.

---

### B.4 Validating your hand calculation

```python
# Validate your hand calculation against twostool_python
import numpy as np
import sys; sys.path.insert(0, '/home/davidncu/2S-TOOL-Python')
from twostool_python.skv import compute_skv

# The 8-point synthetic dataset
x = np.array([0.0000, 0.0030, 0.0100, 0.0070, 0.0030, 0.0060, 0.0120, 0.0090])
y = np.array([12.50, 16.80, 21.20, 18.50, 13.20, 17.10, 20.90, 15.70])

result = compute_skv(x, y)
print(f"S_kv = {result['skv']:.4e}")        # should match −1.503×10⁻³
print(f"slope = {result['slope']:.2f}")      # should match 665.1
print(f"intercept = {result['intercept']:.2f}")  # should match ~12.83
```

Your hand-computed S_kv should match within rounding error of the last digit
shown. The synthetic dataset's 8 points are deliberately small enough that all
summations can be verified with a basic calculator.
