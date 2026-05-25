"""Default parameters for 2S-TOOL analysis.

All defaults match the auto-parameter approach from the fixed MATLAB script.
Parameters can be overridden per-station via the InputData sheet in the Excel file.
"""

# Fraction of GWL depth range — min depth difference between a maximum and its
# following minimum to define an elastic-inelastic interval.
# Note: the MATLAB original uses an absolute threshold of 20 m (suited to deep
# Spanish aquifer datasets, GWL ~300 m). For the Taiwan dataset (GWL depth 5–25 m),
# a 20 m absolute threshold would eliminate all peaks. The fraction-based approach
# (5% of the depth range, ≈0.5 m for Taiwan) is intentionally used here instead.
INTERVALO_Y_FRACTION = 0.05

# Fraction of displacement range — min displacement difference between two
# maxima to treat them as distinct.
# The MATLAB original uses an absolute 0.01 m. At 1% of the displacement range
# this is comparable for Taiwan data (range ~0.1–0.2 m → threshold ~0.001–0.002 m).
INTERVALO_X_FRACTION = 0.01

# Preconsolidation head. None means compute at runtime as max(y1).
# Set to a float to override with a known historical value.
HP_INICIAL_DEFAULT = None

# Discard elastic loops whose vertical amplitude is less than this fraction
# of the largest loop's amplitude.
PORCENTAJE = 0.2

# Output figure resolution in dpi.
FIGURE_DPI = 600

# Output formats. PNG for development speed and browser preview.
# Add "tiff" for publication-ready lossless TIFF at 600 dpi.
FIGURE_FORMATS = ["png"]
