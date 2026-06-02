"""2S-TOOL Python — Skeletal storage coefficients from stress-strain curves.

Translation of A02_StressStrain_Ske_Skv_Part2.m from MATLAB to Python
(Navarro-Hernández et al. 2025, doi:10.1007/s12145-025-02025-2).

Computes S_kv (anelastic) and S_ke (elastic) skeletal storage coefficients
from ground displacement vs. groundwater depth data pairs (stress-strain curve).

This package implements Part 2 of the 2S-TOOL methodology — coefficient
extraction from an already-built stress-strain curve. Part 1 (reading
separate GWL and displacement time series, finding the common period,
interpolation, merging, and writing the StrainStress sheet) is handled
by a separate preprocessing script (prepare_2stool_inputs). Users must
have the stress-strain curve already constructed in the Input Excel file
before running this tool.

Usage:
    python -m twostool_python input.xlsx
    python -m twostool_python --batch inputs/ --output-dir outputs/
"""

__version__ = "0.1.0"
