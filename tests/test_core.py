import pandas as pd
import pytest

from cleankit import clean_frame, normalise_column


def test_normalise_column_variants():
    assert normalise_column("  Participant ID ") == "participant_id"
    assert normalise_column("Age (years)") == "age_years"
    assert normalise_column("2024 score") == "col_2024_score"
    assert normalise_column("!!!") == "column"


def test_clean_frame_removes_duplicates_and_empty_columns():
    df = pd.DataFrame(
        {
            "Participant ID": [1, 2, 2],
            "Age": [" 21 ", "22", "22"],
            "Notes": [None, None, None],
        }
    )
    clean, report = clean_frame(df)

    assert list(clean.columns) == ["participant_id", "age"]
    assert len(clean) == 2
    assert report.duplicates_removed == 1
    assert report.empty_columns_dropped == ["notes"]
    assert report.renamed_columns["Participant ID"] == "participant_id"


def test_numeric_text_is_coerced_and_missing_is_filled_with_median():
    df = pd.DataFrame({"id": [1, 2, 3, 4, 5], "score": ["10", "20", "1,000", None, "30"]})
    clean, report = clean_frame(df)

    assert pd.api.types.is_numeric_dtype(clean["score"])
    assert clean["score"].tolist() == [10, 20, 1000, 25, 30]
    assert report.filled["score"] == 25


def test_non_numeric_text_is_left_alone():
    df = pd.DataFrame({"unit": ["12 kg", "3 cm", "7 kg"]})
    clean, _ = clean_frame(df)
    assert clean["unit"].tolist() == ["12 kg", "3 cm", "7 kg"]


def test_fill_drop_removes_rows_with_missing_values():
    df = pd.DataFrame({"x": [1.0, None, 3.0]})
    clean, _ = clean_frame(df, fill="drop")
    assert clean["x"].tolist() == [1.0, 3.0]


def test_outliers_are_flagged_not_removed():
    df = pd.DataFrame({"x": [1, 2, 3, 4, 5, 100]})
    clean, report = clean_frame(df)
    assert len(clean) == 6
    assert report.outliers["x"] == 1


def test_report_markdown_mentions_the_changes():
    df = pd.DataFrame({"A ": [1, 1]})
    _, report = clean_frame(df)
    text = report.to_markdown()
    assert "Rows in | 2" in text
    assert "Duplicates removed | 1" in text
    assert "Renamed columns" in text


def test_unknown_fill_strategy_is_rejected():
    with pytest.raises(ValueError):
        clean_frame(pd.DataFrame({"x": [1]}), fill="magic")
