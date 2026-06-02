"""Default parameters for 2S-TOOL analysis.

All defaults match the auto-parameter approach from the fixed MATLAB script.
Parameters can be overridden per-station via the InputData sheet in the Excel file.
"""

# Fraction of GWL depth range — min depth difference between a maximum and its
# following minimum to define an elastic-inelastic interval.
# Identical to the MATLAB original (A02_StressStrain_Ske_Skv_Part2.m, line 96):
#   intervalo_y = 0.05 * (max(y1) - min(y1));
# This fraction-based approach scales with the data. For the Taiwan dataset
# (GWL depth 5–25 m), this yields ~0.25–1.25 m; for the published Spanish
# aquifers (GWL depth ~300 m), ~15 m.
INTERVALO_Y_FRACTION = 0.05

# Fraction of displacement range — min displacement difference between two
# maxima to treat them as distinct.
# Identical to the MATLAB original (A02_StressStrain_Ske_Skv_Part2.m, line 97):
#   intervalo_x = 0.01 * (max(x1) - min(x1));
# For Taiwan data (range ~0.03 m), this yields ~0.0003 m.
INTERVALO_X_FRACTION = 0.01

# Preconsolidation head. None means compute at runtime as max(y1).
# Set to a float to override with a known historical value.
HP_INICIAL_DEFAULT = None

# Optional path to a JSON file mapping input file stems to hp_inicial values.
# Example: {"2STOOL_TUKU_F1": 22.78, "2STOOL_TUKU_F2": 22.51, ...}
# Set to None (default) for no external overrides — hp_inicial is computed from
# max(y1) in the input data (or HP_INICIAL_DEFAULT if set).
# Set to None (default) — hp_inicial is computed from max(y1) in the input data.
# Point to a JSON file with per-input-file hp_inicial values to override.
HP_INICIAL_OVERRIDES_PATH: str | None = None

# Discard elastic loops whose vertical amplitude is less than this fraction
# of the largest loop's amplitude.
PORCENTAJE = 0.2

# ── Preconsolidation head from well_timeseries ──────────────────────────
# Directory containing {GWL_STATION}_gwl_timeseries.feather files with
# daily long-term GWL records (dating back to 2000). When set, the pipeline
# derives hp_inicial from the historical maximum GWL depth in these records.
# Requires HC_ASSIGNMENT_CSV and HC_WELL_ELEVATIONS_CSV to also be set.
HC_WELL_TIMESERIES_DIR: str | None = None

# Path to GWL-to-MLCW layer assignment CSV (v3), mapping each
# (station, layer) to its gwl_station, wellcode, and feather_file.
HC_ASSIGNMENT_CSV: str | None = None

# Path to allwells flat CSV for well elevation (elev_leveling_m) lookup.
HC_WELL_ELEVATIONS_CSV: str | None = None

# Output figure resolution in dpi.
FIGURE_DPI = 600

# Figure dimensions in mm for Elsevier journals.
# Single column: 90 mm, 1.5 column: 140 mm, Double column: 190 mm.
FIGURE_WIDTH_MM = 190      # double-column width
FIGURE_HEIGHT_MM = 140     # ~4:3 aspect ratio
FIGURE_FONT_SIZE = 8       # readable at journal print size

# Output formats. PNG for development speed and browser preview.
# Add "tiff" for publication-ready lossless TIFF at 600 dpi.
FIGURE_FORMATS = ["png"]
