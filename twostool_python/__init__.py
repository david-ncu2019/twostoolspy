"""2S-TOOL Python — Skeletal storage coefficients from stress-strain curves.

Translation of A02_StressStrain_Ske_Skv_Part2.m from MATLAB to Python.
Computes S_kv (anelastic) and S_ke (elastic) from ground displacement vs.
groundwater depth time series.

Usage:
    python -m twostool_python input.xlsx
    python -m twostool_python --batch inputs/ --output-dir outputs/
"""

__version__ = "0.1.0"
