"""Extract raw income distribution data from Eurostat and save it locally."""

import pandas as pd
from pathlib import Path

from etl.utils import EUROSTAT_URL, RAW_DATA_DIR


def fetch_eurostat_data(url: str) -> pd.DataFrame:
    """
    Download Eurostat data from a TSV source.

    Args:
        url: URL of the Eurostat TSV dataset.

    Returns:
        A pandas DataFrame containing the downloaded data.
    """
    df = pd.read_csv(url, sep="\t")
    return df


def save_raw_data(df: pd.DataFrame, path: str | Path) -> None:
    """
    Persist raw data to disk as a CSV file.

    Args:
        df: DataFrame to save.
        path: Destination file path.
    """
    df.to_csv(path, index=False)


def main() -> None:
    """
    Run the extract step of the ETL pipeline.

    Downloads the Eurostat dataset and stores it in the raw data
    directory for subsequent processing steps.
    """
    raw_data_tsv = RAW_DATA_DIR / "estat_ilc_di03.csv"

    df = fetch_eurostat_data(EUROSTAT_URL)
    save_raw_data(df, path=raw_data_tsv)


if __name__ == "__main__":
    main()