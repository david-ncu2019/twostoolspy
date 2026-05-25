"""Command-line interface for 2S-TOOL Python.

Usage:
    python -m twostool_python path/to/input.xlsx -o path/to/output/
    python -m twostool_python --batch path/to/inputs/ -o path/to/outputs/
"""

import argparse
import logging
import sys
from pathlib import Path

from .pipeline import run_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="2S-TOOL Part 2 — Compute S_kv and S_ke from stress-strain curves."
    )
    parser.add_argument(
        "input",
        nargs="?",
        type=str,
        help="Path to input .xlsx file (omit with --batch).",
    )
    parser.add_argument(
        "--batch",
        type=str,
        default=None,
        help="Process all .xlsx files in the given directory.",
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=str,
        default=None,
        help="Output directory (default: same as input file, or 'outputs/' for batch).",
    )
    args = parser.parse_args()

    if args.batch:
        input_dir = Path(args.batch)
        if not input_dir.is_dir():
            logger.error(f"Not a directory: {input_dir}")
            sys.exit(1)

        output_dir = Path(args.output_dir) if args.output_dir else input_dir / "outputs"
        files = sorted(input_dir.glob("2STOOL_*.xlsx"))

        if not files:
            logger.error(f"No 2STOOL_*.xlsx files found in {input_dir}")
            sys.exit(1)

        logger.info(f"Batch mode: {len(files)} files → {output_dir}")
        ok = skv_only = errors = 0
        for fp in files:
            try:
                result = run_pipeline(fp, output_dir)
                if result["status"] == "ok":
                    ok += 1
                elif result["status"] == "skv_only":
                    skv_only += 1
                else:
                    errors += 1
            except Exception as exc:
                logger.error(f"  {fp.name}: {exc}")
                errors += 1

        logger.info(f"Done: {ok} ok, {skv_only} skv-only, {errors} errors")
        sys.exit(1 if errors > 0 else 0)

    elif args.input:
        input_path = Path(args.input)
        if not input_path.exists():
            logger.error(f"File not found: {input_path}")
            sys.exit(1)

        output_dir = Path(args.output_dir) if args.output_dir else input_path.parent
        result = run_pipeline(input_path, output_dir)
        logger.info(f"Status: {result['status']}")
        logger.info(f"Output: {result['out_dir']}")
    else:
        parser.error("Either provide an input file path or use --batch.")
