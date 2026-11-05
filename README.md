# python-data-cleaning-kit

[![CI](https://github.com/31242526-svg/python-data-cleaning-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/31242526-svg/python-data-cleaning-kit/actions/workflows/ci.yml)

Dirty CSV in, clean CSV and a validation report out.

Built for datasets that arrive as exports rather than as clean tables: survey dumps,
instrument logs, hand-edited spreadsheets. The goal is that a collaborator can see
**what changed and why**, not just receive a silently fixed file.

## What it does

- normalises column names to `snake_case` (and reports the renames)
- drops columns and rows that are entirely empty
- trims whitespace and turns numeric-looking text into numbers
- fills missing numeric values (median by default, configurable)
- removes duplicate rows
- flags IQR outliers per numeric column
- writes a Markdown report with row counts, per-column nulls, fills and outliers

## Quick start

```bash
pip install -e ".[dev]"
cleankit examples/messy_survey.csv -o clean.csv -r report.md
```

```
clean.csv written: 7 rows x 5 columns
report.md written
duplicates removed: 1
```

Example report:

| Metric | Value |
| --- | --- |
| Rows in | 9 |
| Rows out | 7 |
| Duplicates removed | 1 |
| Empty rows dropped | 1 |

## Use it as a library

```python
import pandas as pd
from cleankit import clean_frame

df = pd.read_csv("examples/messy_survey.csv")
clean, report = clean_frame(df, fill="median")
print(report.to_markdown())
```

## Options

| Flag | Default | Meaning |
| --- | --- | --- |
| `--fill` | `median` | `median`, `mean`, `zero` or `drop` for missing numerics |
| `--no-dedupe` | off | keep duplicate rows |
| `--outlier-factor` | `1.5` | IQR multiplier used for flagging |

## Limitations

- Numeric coercion accepts values that parse after commas and whitespace are removed;
  mixed units (`12 kg`, `3 cm`) are left as text on purpose.
- Outliers are flagged, never removed. Removing data is a research decision, not a
  cleaning step.
- Dates are not parsed. That needs column-specific instructions, which this tool does
  not guess.

## Tests

```bash
pytest
```

MIT licensed.
