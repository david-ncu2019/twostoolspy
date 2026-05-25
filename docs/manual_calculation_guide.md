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
    Example (TUKU Aqf_2, first 3 measurements):

    t        h(t) [m]    E_well [m]    depth(t) [m]
    ───────  ──────────   ───────────   ────────────
    15/1/12     5.923         17.3          11.38
    15/2/09     0.923         17.3          16.38
    15/3/19    −0.902         17.3          18.20
                             ↑
                     from levelling survey
```

### A.3 Step 2: Compute ground displacement

There are three common sources. 2S-TOOL accepts any of them — the algorithm operates on
relative changes in x, not on absolute values.

#### Source 1: MLCW ring-level cumulative compaction (project default)

The standard project pipeline (`prepare_2stool_inputs.py --raw`) reads raw ring-by-ring
MLCW measurements, sums rings within each hydrogeological layer, and converts to metres:

```
    disp(t) = compaction_MM(t) / 1000        [mm → m]
```

where `compaction_MM(t)` is the cumulative compaction (mm) at time `t` since the MLCW
station was installed. Values are **negative** in the project sign convention
(negative = subsidence). The first value is NOT zero — compaction was already
accumulating before the first InSAR-aligned date.

```
    Example: TUKU_F1 real input file (159 points, 2015–2025):

    disp range: [−0.029, −0.011] m
    depth range: [8.24, 22.36] m

    First row:  x = −0.01172 m  (already ~12 mm of compaction by Jan 2015)
    Last row:   x = −0.02801 m  (~28 mm cumulative by Dec 2025)
```

#### Source 2: MLCW reconstructed layer-grouped data

The `--no-raw` flag uses precomputed reconstructed data from
`data/mlcw/group_byLayer/{STATION}_reconst_grouped.csv`. Same mm→m conversion and sign
convention applies.

#### Source 3: Manual from ring absolute elevation

If you have raw leveling measurements of individual magnetic rings:

```
    L(t) = z_ring_upper(t) − z_ring_lower(t)     [layer thickness, m]
    disp(t) = L(t) − L(t_ref)                    [compaction since reference, m]
```

where `t_ref` can be the first measurement date. This gives **positive** values for
compaction. 2S-TOOL accepts either sign convention — the S_kv and S_ke magnitude is
unchanged; only the sign of the output S values flips.

```
    Example: ring elevations at t_ref = 2003-12-06

    t           z_upper [m]   z_lower [m]   L(t) [m]    disp(t) [m]
    ─────────   ───────────   ───────────   ─────────   ───────────
    2003-12-06     8.775        11.938        3.163       0.000
    2004-01-15     8.760        11.920        3.160       0.003
    2004-03-01     8.750        11.910        3.160       0.003
                        ↓
            ring sinks → L decreases → positive disp = compaction
```

#### Source 4: InSAR surface displacement

If you use InSAR surface displacement directly (e.g., from
`data/insar/InSAR_measures_at_MLCW.csv`), values are already in metres. The project
convention is positive = subsidence (InSAR is negated on load), so no conversion is
needed — but check your dataset's sign convention.

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

We use the TUKU Aqf_2 test dataset (83 points, 2015–2021). The full dataset produces:

```
    Reference: twostool_python output
    S_kv = 1.0953 × 10⁻⁴
    S_ke (weighted) = 1.291 × 10⁻⁵
    17 elastic periods, 15 accepted loops
```

### B.1 The 12-step algorithm (indexed to match pipeline.py)

---

#### Step 1 — Compute S_kv (full-cloud linear fit)

Fit a straight line through ALL (x, y) points:

```
    y = slope × x + intercept          [polyfit, degree 1]
    S_kv = −1 / slope
```

For a hand-worked example, pick 4 points from Aqf_2:

```
    i    x (disp, m)     y (depth, m)
    ───  ────────────    ────────────
    0    0.000000        11.377          ← reference date
    1    0.000066        16.377
    2    0.000113        18.202
    3    0.000170        18.183
```

Manual linear regression (least squares):

```
    n = 4
    Σx = 0.000066 + 0.000113 + 0.000170 = 0.000349          (excluding x₀=0)
    Σy = 11.377 + 16.377 + 18.202 + 18.183 = 64.139
    Σxy = 0×11.377 + 0.000066×16.377 + 0.000113×18.202 + 0.000170×18.183
        = 0 + 0.001081 + 0.002057 + 0.003091 = 0.006229
    Σx² = 0² + 0.000066² + 0.000113² + 0.000170²
        = 0 + 4.36e-9 + 1.28e-8 + 2.89e-8 = 4.61e-8
    x̄ = 0.000349/4 = 0.000087
    ȳ = 64.139/4 = 16.035

    slope = (Σxy − n·x̄·ȳ) / (Σx² − n·x̄²)
          = (0.006229 − 4×0.000087×16.035) / (4.61e-8 − 4×0.000087²)
          = (0.006229 − 0.005580) / (4.61e-8 − 3.03e-8)
          = 0.000649 / 1.58e-8
          = 41076

    S_kv = −1/slope = −1/41076 = −2.43 × 10⁻⁵
```

> Note: 4 points is insufficient for a stable fit. The full 83-point fit gives
> S_kv = 1.0953 × 10⁻⁴. For hand calculation, use at least 10–15 points covering
> the full range of displacement.

**With the full 83 points (computed by numpy):**
```
    slope = −9130.0
    intercept = 12.15
    S_kv = −1/(−9130.0) = 1.0953 × 10⁻⁴
```
The intercept (12.15 m) is the depth at zero displacement — the average static
water level.

---

#### Step 2 — Auto-determine parameters

```
    intervalo_y = 0.05 × (max(y) − min(y))     [5% of depth range]
    intervalo_x = 0.01 × (max(x) − min(x))     [1% of displacement range]
    hp_inicial  = max(y)                        [deepest GWL depth in record]
    porcentaje  = 0.2                           [20% amplitude threshold]
```

For Aqf_2 (using depth = −head, elev = 0):
```
    y_range = 8.09 − (−3.86) = 11.95 m
    intervalo_y = 0.05 × 11.95 = 0.598 m

    x_range = 0.000688 − 0 = 0.000688 m
    intervalo_x = 0.01 × 0.000688 = 6.88 × 10⁻⁶ m

    hp_inicial = max(y) = 8.09 m
    porcentaje = 0.2
```

---

#### Step 3 — Find all local extrema

Walk through the y-series and mark every point that is higher than BOTH neighbours
(peak) or lower than BOTH neighbours (trough).

```
    Data (first 8 points of Aqf_2, depth = −head):

    i:   0      1       2       3       4       5       6       7
    y:  5.923  0.923  −0.902  −0.883  −2.185   1.094   2.836   3.647
                        ↑               ↑               ↑
                      trough          trough           peak

    Peaks:   i=0 (y=5.923)*, i=6 (y=2.836), i=7 (y=3.647), ...
    Troughs: i=2 (y=−0.902), i=4 (y=−2.185), ...
    * i=0 is a peak because the series starts there AND 5.923 > 0.923
```

**Boundary trends:**
```
    crecealinicio = (first peak idx < first trough idx) = (0 < 2) = True
        → curve starts on a rising/loading limb

    crecealfinal = (last peak idx < last trough idx)
        → determines whether the curve ends rising or falling
```

For the full 83-point Aqf_2 dataset: 19 raw peaks, 18 raw troughs.

---

#### Step 4 — Apply x-interval criterion

Peaks whose displacement values differ by less than `intervalo_x` are merged into
one group. Only the **highest** (largest y) peak in each group survives.

```
    Worked example (subset of peaks from Aqf_2):

    Peak at i=31: x=−0.000207, y=6.190
    Peak at i=33: x=−0.000226, y=6.011

    |x₃₁ − x₃₃| = |−0.000207 − (−0.000226)| = 0.000019 m

    intervalo_x = 6.88 × 10⁻⁶ m
    0.000019 > 6.88 × 10⁻⁶  →  NOT merged — peaks are far enough apart
```

For the full dataset: 19 raw peaks → 17 survive the x-criterion.

Troughs are recomputed between surviving peaks. For each pair of consecutive
surviving peaks, the deepest trough between them is selected.

---

#### Step 5 — Apply y-interval criterion

A peak survives only if its depth exceeds BOTH neighbouring troughs by at least
`intervalo_y`. This ensures each peak represents a genuine loading cycle with
meaningful depth change.

```
    For a peak at i=31 (y=6.190):
    Left trough:  y=3.031
    Right trough: y=3.491

    y_peak − y_trough_left  = 6.190 − 3.031 = 3.159 > 0.598 ✓
    y_peak − y_trough_right = 6.190 − 3.491 = 2.699 > 0.598 ✓
    → Peak survives
```

The exact logic depends on `crecealinicio` and `crecealfinal` — see `peaks.py`
lines 209–262 for the full branching. For the Aqf_2 full dataset: 17 → 17 peaks
survive the y-criterion.

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

For Aqf_2: 17 elastic periods identified.

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
    Worked example — single loop from Aqf_2 (indices 55–60):

    x_seg:  [ −0.000349, −0.000367, −0.000301, −0.000367, −0.000386, −0.000377 ]
    y_seg:  [  5.782,      5.218,      7.525,      4.102,      2.896,      5.733 ]

    Trough at idx=4: y=2.896  (deepest = most stressed)

    Loading limb (trough → end):
    x_load: [ −0.000386, −0.000377 ]
    y_load: [  2.896,      5.733  ]

    slope = (5.733 − 2.896) / (−0.000377 − (−0.000386))
          = 2.837 / 9.0 × 10⁻⁶
          = 315,222

    S_ke = −1 / 315,222 = −3.172 × 10⁻⁶

    slope > 0 → rejected (positive slope on loading limb is physically impossible
    for depth data where more compaction should mean deeper water).
```

> For the Aqf_2 dataset with `depth = head` (the test run), most loops show the
> correct negative slope. The above example illustrates a loop that would be rejected.

For the full Aqf_2 (depth = −head convention, elev = 0): 17 loops, 15 accepted.

---

#### Step 8 — Reject small loops

```
    max_amplitude = max(delta_y across all loops)
    threshold = 0.2 × max_amplitude

    Any loop with delta_y < threshold is rejected (accepted flag → 0)
```

For Aqf_2: max_amplitude ≈ 5.09 m, threshold ≈ 1.02 m.
Loops with vertical amplitude < 1.02 m are discarded.

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

For Aqf_2 (depth = head, our test run):
```
    S_ke_weighted = 1.291 × 10⁻⁵
    S_ke_mean     = 1.386 × 10⁻⁵
    S_ke_std      = 1.528 × 10⁻⁵
    S_ke_min      = 4.808 × 10⁻⁷
    S_ke_max      = 5.074 × 10⁻⁵
    15 accepted / 17 total loops
```

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
# Run twostool_python on the same data and compare
import sys; sys.path.insert(0, '/home/davidncu/2S-TOOL-Python')
from twostool_python.pipeline import run_pipeline
from pathlib import Path

result = run_pipeline(
    Path('data/gwl/2stool_test_inputs/2STOOL_TEST_Aqf_2.xlsx'),
    Path('data/gwl/2stool_test_outputs')
)
s = result['summary']
print(f"S_kv = {s['skv']:.4e}")
print(f"S_ke (weighted) = {s['ske_weighted']:.4e}")
print(f"Loops: {s['n_accepted']}/{s['n_loops_total']}")
```

Your hand-computed values should match within rounding error for S_kv and within
~5% for S_ke_weighted (the weighted mean is sensitive to exact amplitude values).
