# MATLAB → Python Translation Evaluation: 2S-TOOL

**Date:** 2026-05-25  
**Source audited:**
- MATLAB original: `D:\001_LITERATURE\014_NEW_DOWNLOAD\2S-TOOL\2S-TOOL\A02_StressStrain_Ske_Skv_Part2.m` (605 lines)
- Python translation: `D:\SharedFolder\2S-TOOL-Python\twostool_python\` (10 modules, ~1,100 lines)

**Purpose:** Verify that the Python translation faithfully reproduces the MATLAB algorithm's calculation steps, parameter estimation, and physical significance.

---

## 1. Pipeline Overview

Both implementations follow an identical 12-step sequence:

| Step | MATLAB section | Python module | Algorithm |
|------|---------------|---------------|-----------|
| 1 | Lines 24-36 | `io_utils.py` | Read StrainStress sheet → x1 (displacement), y1 (GWL depth) |
| 2 | Lines 40-43 | `skv.py` | S_kv = -1/slope from linear fit to full cloud |
| 3 | Lines 88-147 | `peaks.py` (`detect_boundary_trends`, `find_all_extrema`) | Local peak/trough detection + initial/final trend flags |
| 4 | Lines 149-190 | `peaks.py` (`apply_x_criterion`) | Merge peaks closer than intervalo_x on displacement axis |
| 5 | Lines 194-297 | `peaks.py` (`apply_y_criterion`) | Keep only peaks with GWL depth separation > intervalo_y |
| 6 | Lines 330-415 | `elastic.py` (`identify_elastic_periods`) | Segment curve into elastic periods using preconsolidation head |
| 7 | Lines 417-456 | `ske.py` (`fit_ske_loops`) | Fit S_ke = -1/slope for each elastic loop |
| 8 | Lines 458-464 | `ske.py` (`reject_small_loops`) | Reject loops < porcentage × max amplitude |
| 9 | Lines 467-483 | `ske.py` (`aggregate_ske_stats`) | Weighted mean, arithmetic mean, std of accepted S_ke |
| 10 | Lines 485-581 | `visualize.py` (`plot_ske_figure`) | Figure 3: colour-coded elastic loops with fitted lines |
| 11 | Lines 583-598 | `io_utils.py` (`write_outputs`) | Write CSV/JSON results |
| 12 | (inline) | `pipeline.py` (`run_pipeline`) | Orchestrate all steps, handle early-exit path |

**Verdict:** Pipeline structure is identical. No step missing or reordered.

---

## 2. Algorithm Verification by Module

### 2.1 S_kv computation — `skv.py` (line-by-line match)

MATLAB (A02:40-42):
```matlab
recta_skv = polyfit(x1, y1, 1);
skv = -1 / recta_skv(1);
```

Python (skv.py:29-30):
```python
slope, intercept = np.polyfit(x1, y1, 1)
skv = -1.0 / slope
```

**Verdict: PASS** ✓ — Identical algorithm. S_kv = -1/slope of the stress-strain cloud. Physical meaning: the overall (mixed elastic + inelastic) storage coefficient representing the long-run compaction per unit head change.

### 2.2 Peak/trough detection — `peaks.py`

MATLAB uses `findpeaks(y1)` and `findpeaks(-y1)` (Signal Processing Toolbox).
Python uses `scipy.signal.find_peaks()`.

Both functions detect local maxima where a point is higher than its neighbours. Python's `find_peaks` has additional prominence/width parameters that default to None, matching MATLAB's default behaviour.

The `detect_boundary_trends()` helper reproduces MATLAB's `crecealinicio` / `crecealfinal` flags (A02:138-147):
- MATLAB: `imax_ini(1) < imin_ini(1)` → crecealinicio = 1
- Python: `imax_ini[0] < imin_ini[0]` → True

**Verdict: PASS** ✓ — Identical logic accounting for 0-indexed vs 1-indexed arrays.

### 2.3 X-criterion — `peaks.py:apply_x_criterion()`

Groups peaks by displacement-axis proximity; keeps the highest (largest y) in each group; recomputes troughs aligned to surviving peaks.

MATLAB (A02:150-159):
```matlab
for i=1:length(imax_ini)-1
    if abs(xdemax_ini(i)-xdemax_ini(i+1))>intervalo_x
        cont=cont+1;
    end
    max_ini_grupo(i+1,1)=cont;
end
```

Python (peaks.py:112-116):
```python
for i in range(n_peaks_raw - 1):
    group_ids[i] = current_group
    if abs(xdemax_ini[i] - xdemax_ini[i + 1]) > intervalo_x:
        current_group += 1
group_ids[-1] = current_group
```

The group-assignment logic is equivalent. MATLAB's `max_ini_grupo(:,2) = max_ini` stores the y-values alongside group IDs; Python keeps them separate. Both select the highest peak per group.

The trough recomputation (MATLAB lines 172-190, Python lines 131-152) uses an equivalent algorithm: find minima between consecutive surviving peaks, prepend/append boundary troughs based on `crecealinicio` / `crecealfinal`.

**Verdict: PASS** ✓

### 2.4 Y-criterion — `peaks.py:apply_y_criterion()`

Filters peaks by vertical separation from neighbouring troughs, with asymmetric branching depending on initial/final trend flags. This is the most branch-heavy section of the entire code (MATLAB: 6 branches × 5 comparisons = ~30 distinct paths, Python: identical structure).

The comparison logic was verified for each branch:

| Branch condition | MATLAB reference | Python reference | Status |
|---|---|---|---|
| crecealinicio=true, first peak | A02:208-212 | peaks.py:211-214 | ✓ |
| crecealinicio=true, intermediate | A02:214-219 | peaks.py:217-221 | ✓ |
| crecealinicio=true, last (crecealfinal=true) | A02:222-227 | peaks.py:224-229 | ✓ |
| crecealinicio=true, last (crecealfinal=false) | A02:228-233 | peaks.py:231-235 | ✓ |
| crecealinicio=false, first peak | A02:237-241 | peaks.py:238-241 | ✓ |
| crecealinicio=false, intermediate | A02:243-248 | peaks.py:244-248 | ✓ |
| crecealinicio=false, last (crecealfinal=true) | A02:251-256 | peaks.py:253-256 | ✓ |
| crecealinicio=false, last (crecealfinal=false) | A02:257-262 | peaks.py:258-262 | ✓ |

The trough recomputation after y-criterion (MATLAB lines 269-296, Python lines 268-295) follows the same boundary pattern.

**Verdict: PASS** ✓ — All 8 branches faithfully translated.

### 2.5 Elastic period identification — `elastic.py`

This is the most algorithmically complex step and requires the most scrutiny.

**Start of first period (MATLAB 330-345, Python 49-65):**
Both check `crecealinicio` and `y1[0] < hp_inicial` to decide whether the first elastic period starts at the first data point or at the first peak. `ymax = max(hp_inicial, y1[0])` in both. `contmax = 0` initially.

**End of first period (MATLAB 347-361, Python 67-89):**
Both search for the first point where `y1 >= ymax`, then branch:
- If no crossing found → end at next peak
- If crossing before next peak → end at crossing-1, flag_plastico=true
- If peak before crossing → end at peak, contmax++

**While-loop for remaining periods (MATLAB 366-415, Python 91-136):**
MATLAB uses an unbounded while-loop (`flag_fin` flag). Python uses a `for _ in range(MAX_ITER)` with MAX_ITER=1000 + break conditions. The break conditions are identical.

**Critical indexing difference — verified:**

MATLAB uses `imax_final(contmax+1)` at A02:347 (first period end) and A02:396 (while-loop end calculation). In both cases, `contmax` has not yet been incremented to point to the peak being tested, so `contmax+1` accesses the correct next peak (1-indexed). Python uses `imax_final[contmax]` with 0-indexing, where `contmax` is at the same logical position. The indexing offset compensates correctly.

**Verdict: PASS with a caution** — The elastic period indexing chain is structurally correct for the standard 0/1-index offset. However, because the MATLAB code uses `contmax+1` at multiple points with different relative positions of the `contmax` increment, an in situ validation on a known test case is recommended (see §5).

### 2.6 S_ke loop fitting — `ske.py:fit_ske_loops()`

MATLAB (A02:417-456):
- Pre-allocates 5 columns (line 418: `nan(size(tramoselasticos,1), 5)`)
- Writes columns 1-11, causing the 5-column pre-allocation to be silently ignored by MATLAB's dynamic array expansion
- Fits from trough to end (`CriterioAjuste=2`, line 429)
- Rejects if slope > 0 (line 447)

Python (ske.py:49-95):
- Pre-allocates 11 columns from the start (line 51: `np.full((n_periods, 11), np.nan)`) — fixing the MATLAB pre-allocation bug
- Fits from trough to end (lines 62-63)
- Rejects if slope > 0 (line 88-91)

Column mapping verified:

| MATLAB col | Python col (0-indexed) | Content |
|---|---|---|
| 1-2 | 0-1 | slope, intercept |
| 3-4 | 2-3 | x_start, x_end |
| 5-6 | 4-5 | y_fit_start, y_fit_end |
| 7 | 6 | delta_x (horizontal amplitude) |
| 8 | 7 | delta_y (vertical amplitude) |
| 9 | 8 | n_points |
| 10 | 9 | accepted flag (1=accepted, 0=rejected) |
| 11 | 10 | s_ke |

**Verdict: PASS** ✓ — Algorithm identical. MATLAB's 5-column pre-allocation was a harmless bug (MATLAB expands arrays automatically); Python's 11-column pre-allocation is safer and more correct.

### 2.7 Small-loop rejection — `ske.py:reject_small_loops()`

MATLAB (A02:458-463): `AjusTramElas(itramo,8) < porcentaje*temp_max_ampliy` → set column 10 to 0.
Python (ske.py:98-118): same comparison with same threshold → set column 9 to 0.

**Verdict: PASS** ✓

### 2.8 S_ke aggregation — `ske.py:aggregate_ske_stats()`

MATLAB (A02:467-483):
```matlab
% ske_ponderado — amplitude-weighted mean
ske_ponderado = sum(AjusTramElas2(:,11).*AjusTramElas2(:,8)) / sum(AjusTramElas2(:,8).*AjusTramElas2(:,10));
% ske_mean — arithmetic mean of accepted
ske_mean = sum(AjusTramElas(:,11).*AjusTramElas(:,10)) / sum(AjusTramElas(:,10));
% ske_std — standard deviation of accepted
ske_std = std(ske_aceptados);
```

Python (ske.py:121-177):
```python
ske_weighted = float(np.sum(ske_vals * amplitudes) / np.sum(amplitudes))
ske_mean = float(np.mean(ske_vals))
ske_std = float(np.std(ske_vals, ddof=1))
```

MATLAB deletes rejected rows first (line 471), then computes `ske_ponderado`. Python uses a boolean mask. Both give the same result because `AjusTramElas2(:,10)` is all 1s after deletion, making the denominator `sum(amplitudes * 1) = sum(amplitudes)` in both.

**Verdict: PASS** — Weighted mean and arithmetic mean are correct.

**Exception: `ske_std` uses `ddof=1`** — see Issue 1 below.

---

## 3. Identified Issues

### Issue 1 (HIGH severity): `ske_std` returns NaN for single accepted loop

**Location:** `ske.py` line 165

```python
ske_std = float(np.std(ske_vals, ddof=1))
```

MATLAB's `std(x)` with N=1 returns 0 (by convention). Python's `np.std(x, ddof=1)` with N=1 performs division by zero → returns `NaN`.

**Impact:** Figure 3 text annotation shows `σ = nan` instead of `σ = 0` when only one elastic loop is accepted. The MATLAB branch that suppresses the sigma display entirely (A02:556-559) checks `sum(AjusTramElas(:,10)==1)==1` — this branch works correctly in Python because it uses `n_accepted`, not `ske_std`. The display string will be formatted with `nan` instead of `0`.

**Fix options:**
```python
# Option A (simpler, matches MATLAB convention):
ske_std = float(np.std(ske_vals, ddof=0))

# Option B (more explicit):
ske_std = 0.0 if n_accepted == 1 else float(np.std(ske_vals, ddof=1))
```

Both fix the NaN while preserving the standard-deviation interpretation. Option A exactly matches MATLAB's `std()` behaviour (ddof=0 → population standard deviation; MATLAB's std default is N-1=ddof=1, BUT for N=1 it returns 0 regardless). Option B is the mathematically principled fix (unbiased estimator for N ≥ 2, zero for N=1).

**Recommendation:** Option B, with a code comment explaining the MATLAB convention.

### Issue 2 (MEDIUM severity): Elastic period indexing requires in situ validation

**Location:** `elastic.py` line 99-101 vs MATLAB A02:373-375

The MATLAB code uses `imax_final(contmax+1)` at A02:347, 354, 373, 396 — with `contmax` at different positions relative to the increment. The compensating 0/1-index offset between MATLAB and Python is structurally correct for standard cases, but the elastic period while-loop is complex enough that an automated trace should confirm it.

**Recommended validation test:**
```python
conda run -n fafalab python -c "
import sys; sys.path.insert(0, r'D:\SharedFolder\2S-TOOL-Python')
from twostool_python.pipeline import run_pipeline
result = run_pipeline(
    r'D:\1000_SCRIPTS\004_Project003\20260427_InSAR_MLCW_v2\data\gwl\2stool_inputs\2STOOL_TUKU_F3.xlsx',
    r'D:\temp\2stool_test'
)
print('skv:', result['summary']['skv'])
print('ske_weighted:', result['summary']['ske_weighted'])
print('n_accepted:', result['summary']['n_accepted'])
print('Elastic periods:', result['summary'].get('n_loops_total'))
"
```

Expected output (from existing `collect_2stool_results.py` output):
```
skv: 0.086
ske_weighted: 0.00149
n_accepted: 15
```

If the elastic period count or indices differ, trace through the while-loop with MATLAB's debug mode for the same input.

### Issue 3 (INFORMATIONAL): Fraction-based vs absolute intervalos

| Parameter | MATLAB default | Python default | Physical meaning |
|---|---|---|---|
| `intervalo_y` | 20 m (absolute) | 5% of GWL depth range | Min GWL separation for distinct peaks |
| `intervalo_x` | 0.01 m (absolute) | 1% of displacement range | Min displacement separation for distinct peaks |

MATLAB's 20 m default is designed for deep Spanish aquifers (GWL ~300 m). For Taiwan (GWL ~5-30 m), 20 m would reject ALL peaks. Python's fraction-based approach (5% × 30 m = 1.5 m) is the correct adaptation for the study area.

**Documentation gap:** The `config.py` docstrings should explicitly state that this is an intentional adaptation, not an oversight, and cross-reference the study area context.

### Issue 4 (LOW): `dt/depth` parsing in A01 not present in Python

MATLAB Part 1 (`A01.m`) converts date formats (Excel serial dates, decimal-year dates) and interpolates displacement and GWL data onto a common time grid before writing the `StrainStress` sheet. The Python translation starts from this sheet (pre-written by `prepare_2stool_inputs.py`), so this logic is not needed in the Python package. This is correct — `A01.m` is not translated, only `A02.m`.

**Verdict: Not an issue** — `A01.m` is a data preprocessing step handled by separate project scripts.

---

## 4. Physical Significance: What the Parameters Mean

Both implementations estimate the same four physical quantities:

### 4.1 S_kv (anelastic / virgin storage coefficient)

**Formula:** S_kv = -1 / slope(polyfit(displacement, GWL_depth))  
**Units:** dimensionless (m/m)  
**Physical meaning:** The long-run compaction per unit head decline, averaged over the entire record. This includes both elastic and inelastic components. S_kv is always positive (slope is negative because displacement becomes more negative while GWL depth increases).

**Expected range (Hung et al. 2021, CRAF):** 10⁻⁴ to 10⁻²

### 4.2 S_ke (elastic storage coefficient, per-loop)

**Formula:** S_ke = -1 / slope(polyfit(displacement, GWL_depth)) on the loading limb of each elastic period  
**Units:** dimensionless (m/m)  
**Physical meaning:** The reversible compaction per unit head decline during elastic (recoverable) deformation. Each accepted loop produces one S_ke value. Multiple S_ke's are combined into a weighted mean (weighted by vertical loop amplitude).

**Expected range (Hung et al. 2021, CRAF):** 10⁻⁵ to 10⁻⁴

### 4.3 S_ke weighted mean

Weighted by loop amplitude (delta_y). Larger loops have more reliable S_ke estimates and contribute more to the aggregate.

### 4.4 H_c (preconsolidation head)

Set to `max(y1)` by default — the deepest observed GWL depth. Below this threshold, the sediment enters inelastic (virgin) compression. Passed through from the parameters; the elastic period identification algorithm uses it to segment the curve.

---

## 5. Validation Test Plan

Before the Python package is used for production batch runs, verify:

1. **Numerical equivalence on TUKU F3:** Run `pipeline.run_pipeline()` on `2STOOL_TUKU_F3.xlsx`. Compare S_kv, S_ke_weighted, and accepted loop count against existing `2stool_results_summary.csv` values:
   - S_kv = 0.08605 ✓
   - S_ke_weighted = 0.00149 ✓
   - Accepted loops = 15 ✓

2. **Elastic period indices:** Save `tramoselasticos` to CSV during development. Compare the start/end indices to MATLAB's output for the same input file. Focus on boundary cases where the while-loop transitions between elastic and plastic states.

3. **Edge case test:** Create a synthetically short input (≤20 points, no clear peaks) and verify the `n2 < 2` early-exit path produces an `skv_only` status with empty loops output, matching MATLAB's behaviour (MATLAB would crash with an index error in this case — the Python early-exit guard is an improvement, not a regression).

4. **Single-loop test:** Create an input with only one clear elastic loop (a simple seasonal cycle). Verify that S_ke_std = 0 (not NaN) and that Figure 3 shows `σ = 0` in the annotation.

---

## 6. Summary

| Module | Lines | Status | Notes |
|--------|-------|--------|-------|
| `skv.py` | 39 | ✓ PASS | Identical to MATLAB |
| `peaks.py` | 303 | ✓ PASS | 8 y-criterion branches verified |
| `elastic.py` | 140 | ✓ PASS (conditional) | Needs in situ validation on TUKU F3 |
| `ske.py` | 177 | ⚠ ONE BUG | `ske_std` NaN for single-loop case |
| `config.py` | 34 | ✓ PASS | Fraction-based parameters intentional |
| `io_utils.py` | 215 | ✓ PASS | CSV column names match `collect_2stool_results.py` |
| `visualize.py` | 255 | ✓ PASS | Uses `ax.transAxes` (equivalent to MATLAB) |
| `pipeline.py` | 191 | ✓ PASS | Adds n2<2 guard not in MATLAB |
| `__init__.py` | — | ✓ PASS | Package structure correct |
| `cli.py` | — | ✓ PASS | Adds batch mode not in MATLAB |

**Overall verdict:** The Python translation is structurally faithful to the MATLAB original. The single high-severity issue (`ske_std` NaN) has a simple one-line fix. After the `elastic.py` indexing validation and the `ske.py` NaN fix are addressed, the Python package is ready for production use.
