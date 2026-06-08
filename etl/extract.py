"""Extract raw income distribution data from Eurostat and save it locally."""

import pandas as pd
from pathlib import Path

from etl.utils import EUROSTAT_URL, RAW_DATASET


def fetch_eurostat_data(url: str) -> pd.DataFrame:
    """Download Eurostat data from a TSV source."""
    try:
        return pd.read_csv(url, sep="\t")
    except Exception as e:
        raise RuntimeError(
            f"Failed downloading Eurostat dataset"
        ) from e


def save_raw_data(df: pd.DataFrame, path: str | Path) -> None:
    """Persist raw data to disk as a CSV file."""
    df.to_csv(path, index=False)


def main() -> None:
    """
    Run the extract step of the ETL pipeline.

    Downloads the Eurostat dataset and stores it in the raw data
    directory for subsequent processing steps.
    """
    df = fetch_eurostat_data(EUROSTAT_URL)
    save_raw_data(df, path=RAW_DATASET)


if __name__ == "__main__":
    main()
