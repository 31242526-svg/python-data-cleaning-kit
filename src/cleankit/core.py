"""Core cleaning pipeline: dirty tabular data in, clean data plus report out."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

NUMERIC_PARSE_THRESHOLD = 0.9


def normalise_column(name: str) -> str:
    """Turn '  Participant ID ' into 'participant_id'."""
    text = re.sub(r"[^0-9a-zA-Z]+", "_", str(name).strip())
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", text)
    text = re.sub(r"_+", "_", text).strip("_").lower()
    if not text:
        text = "column"
    if text[0].isdigit():
        text = f"col_{text}"
    return text


@dataclass
class CleaningReport:
    rows_in: int = 0
    rows_out: int = 0
    duplicates_removed: int = 0
    empty_rows_dropped: int = 0
    empty_columns_dropped: list[str] = field(default_factory=list)
    renamed_columns: dict[str, str] = field(default_factory=dict)
    filled: dict[str, float] = field(default_factory=dict)
    outliers: dict[str, int] = field(default_factory=dict)

    def to_markdown(self) -> str:
        lines = [
            "# Cleaning report",
            "",
            "| Metric | Value |",
            "| --- | --- |",
            f"| Rows in | {self.rows_in} |",
            f"| Rows out | {self.rows_out} |",
            f"| Duplicates removed | {self.duplicates_removed} |",
            f"| Empty rows dropped | {self.empty_rows_dropped} |",
        ]
        if self.empty_columns_dropped:
            lines += ["", "## Dropped empty columns", ""]
            lines += [f"- `{name}`" for name in self.empty_columns_dropped]
        if self.renamed_columns:
            lines += ["", "## Renamed columns", "", "| Original | Normalised |", "| --- | --- |"]
            lines += [f"| {old} | `{new}` |" for old, new in self.renamed_columns.items()]
        if self.filled:
            lines += [
                "",
                "## Missing values filled",
                "",
                "| Column | Value used |",
                "| --- | --- |",
            ]
            lines += [f"| `{col}` | {value:g} |" for col, value in self.filled.items()]
        if self.outliers:
            lines += [
                "",
                "## IQR outliers flagged (not removed)",
                "",
                "| Column | Count |",
                "| --- | --- |",
            ]
            lines += [f"| `{col}` | {count} |" for col, count in self.outliers.items()]
        return "\n".join(lines) + "\n"


def _normalise_names(columns: pd.Index, report: CleaningReport) -> list[str]:
    names: list[str] = []
    seen: dict[str, int] = {}
    for original in columns:
        base = normalise_column(str(original))
        count = seen.get(base, 0) + 1
        seen[base] = count
        name = base if count == 1 else f"{base}_{count}"
        names.append(name)
        if str(original) != name:
            report.renamed_columns[str(original)] = name
    return names


def _is_text(series: pd.Series) -> bool:
    """True for object and string dtypes (pandas 3 uses ``str`` by default)."""
    return series.dtype == object or isinstance(series.dtype, pd.StringDtype)


def _coerce_numeric(series: pd.Series, threshold: float = NUMERIC_PARSE_THRESHOLD) -> pd.Series:
    """Convert a text column to numbers when nearly every value parses."""
    if not _is_text(series) or series.dropna().empty:
        return series
    cleaned = series.astype("string").str.strip().str.replace(",", "", regex=False)
    converted = pd.to_numeric(cleaned, errors="coerce")
    original_present = cleaned.notna().sum()
    if original_present and converted.notna().sum() / original_present >= threshold:
        return converted.astype("Float64")
    return series


def clean_frame(
    df: pd.DataFrame,
    *,
    fill: str = "median",
    drop_duplicates: bool = True,
    outlier_factor: float = 1.5,
) -> tuple[pd.DataFrame, CleaningReport]:
    """Clean a dataframe and describe every change in the returned report."""
    if fill not in {"median", "mean", "zero", "drop"}:
        raise ValueError(f"unknown fill strategy: {fill}")

    report = CleaningReport(rows_in=len(df))
    frame = df.copy()
    frame.columns = _normalise_names(frame.columns, report)

    for col in frame.columns:
        if _is_text(frame[col]):
            frame[col] = frame[col].map(lambda v: v.strip() if isinstance(v, str) else v)
            frame[col] = frame[col].replace("", pd.NA)

    empty_columns = [col for col in frame.columns if frame[col].isna().all()]
    if empty_columns:
        frame = frame.drop(columns=empty_columns)
        report.empty_columns_dropped = empty_columns

    before = len(frame)
    frame = frame.dropna(how="all")
    report.empty_rows_dropped = before - len(frame)

    for col in frame.columns:
        frame[col] = _coerce_numeric(frame[col])

    numeric_cols = [c for c in frame.columns if pd.api.types.is_numeric_dtype(frame[c])]
    for col in numeric_cols:
        series = frame[col]
        missing = int(series.isna().sum())
        if missing == 0:
            continue
        if fill == "drop":
            frame = frame[frame[col].notna()]
            continue
        if fill == "zero":
            value = 0.0
        elif fill == "mean":
            value = float(series.mean())
        else:
            value = float(series.median())
        frame[col] = series.fillna(value)
        report.filled[col] = value

    if drop_duplicates:
        before = len(frame)
        frame = frame.drop_duplicates()
        report.duplicates_removed = before - len(frame)

    for col in numeric_cols:
        series = frame[col].dropna()
        if len(series) < 4:
            continue
        q1, q3 = series.quantile([0.25, 0.75])
        iqr = q3 - q1
        if iqr == 0:
            continue
        low, high = q1 - outlier_factor * iqr, q3 + outlier_factor * iqr
        count = int(((series < low) | (series > high)).sum())
        if count:
            report.outliers[col] = count

    frame = frame.reset_index(drop=True)
    report.rows_out = len(frame)
    return frame, report


def clean_file(
    source: str | Path,
    output: str | Path,
    report_path: str | Path | None = None,
    *,
    fill: str = "median",
    drop_duplicates: bool = True,
    outlier_factor: float = 1.5,
) -> CleaningReport:
    """Clean a CSV file and optionally write the Markdown report next to it."""
    df = pd.read_csv(source)
    clean, report = clean_frame(
        df, fill=fill, drop_duplicates=drop_duplicates, outlier_factor=outlier_factor
    )
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    clean.to_csv(output, index=False)
    if report_path is not None:
        Path(report_path).write_text(report.to_markdown(), encoding="utf-8")
    return report
