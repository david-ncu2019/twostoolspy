# twostoolspy

A Python translation of **2S-TOOL** (Stress-Strain Skeleton Storage Coefficients), a method for estimating elastic (`S_ke`) and anelastic (`S_kv`) skeletal storage coefficients from stress-strain curves of aquifer systems.

## Original Method & Authors

This software is based on the method described in:

> **Navarro-Hernández, M.I., Valdes-Abellan, J., & Tomás, R.** (2025). *2S-TOOL: A tool for estimating elastic and inelastic skeletal storage coefficients from stress–strain curves.* [Paper DOI — add if known]

Please cite the original authors when using this tool in research:

| Author | ORCID |
|--------|-------|
| María I. Navarro-Hernández | [0000-0002-8989-3807](https://orcid.org/0000-0002-8989-3807) |
| Javier Valdes-Abellan | [0000-0003-3570-4983](https://orcid.org/0000-0003-3570-4983) |
| Roberto Tomás | [0000-0003-2947-9441](https://orcid.org/0000-0003-2947-9441) |

## Modules

```
twostool_python/
├── __init__.py          # Package init
├── __main__.py          # python -m entry point
├── cli.py               # Command-line interface
├── config.py            # Default parameters
├── io_utils.py          # Excel read, CSV/JSON write
├── skv.py               # Anelastic (virgin) storage coefficient
├── peaks.py             # Extrema detection and filtering
├── elastic.py           # Elastic period identification
├── ske.py               # Elastic loop fitting and stats
├── visualize.py         # Publication-ready figures (PNG)
└── pipeline.py          # Orchestrator (12-step flow)
```

## Requirements

- Python 3.x
- numpy, scipy, pandas, matplotlib, openpyxl

Install: `pip install -r requirements.txt`

## Usage

```bash
# Single file
python -m twostool_python path/to/input.xlsx --output-dir path/to/output/

# Batch process all files in a directory
python -m twostool_python --batch path/to/inputs/ --output-dir path/to/outputs/
```

## License

BSD 3-Clause — see [LICENSE](LICENSE).
