"""Command line entry point: cleankit dirty.csv -o clean.csv -r report.md."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cleankit.core import clean_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cleankit",
        description="Clean a messy CSV and write a validation report.",
    )
    parser.add_argument("source", type=Path, help="input CSV")
    parser.add_argument(
        "-o", "--output", type=Path, default=Path("clean.csv"), help="clean CSV to write"
    )
    parser.add_argument(
        "-r", "--report", type=Path, default=Path("report.md"), help="Markdown report to write"
    )
    parser.add_argument("--fill", choices=["median", "mean", "zero", "drop"], default="median")
    parser.add_argument("--no-dedupe", action="store_true", help="keep duplicate rows")
    parser.add_argument("--outlier-factor", type=float, default=1.5)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.source.exists():
        print(f"error: no such file: {args.source}", file=sys.stderr)
        return 2
    report = clean_file(
        args.source,
        args.output,
        args.report,
        fill=args.fill,
        drop_duplicates=not args.no_dedupe,
        outlier_factor=args.outlier_factor,
    )
    print(f"{args.output} written: {report.rows_out} rows")
    print(f"{args.report} written")
    print(f"duplicates removed: {report.duplicates_removed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
