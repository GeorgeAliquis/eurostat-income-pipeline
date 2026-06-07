"""
ETL pipeline for transforming raw income data into a cleaned fact table and
associated dimension tables.
"""
import pandas as pd
from pathlib import Path

from etl.utils import RAW_DATASET, PROCESSED_DATA_DIR
from etl.dimensions import create_dimensions

COLUMN_RENAMES = {
    "age": "age_group",
    "geo\\TIME_PERIOD": "country_code",
}

ID_VARS = ["freq", "age", "sex", "statinfo", "unit", "geo\\TIME_PERIOD"]

DIMENSION_KEYS = {
    "country": ("country_code", "country_id"),
    "sex": ("sex", "sex_id"),
    "unit": ("unit", "unit_id"),
    "statinfo": ("statinfo", "statinfo_id"),
    "age": ("age_group", "age_id"),
}

FACT_COLUMNS = [
    "country_id",
    "age_id",
    "sex_id",
    "unit_id",
    "statinfo_id",
    "year",
    "income",
    "flag",
]


def expand_info_column(df: pd.DataFrame) -> pd.DataFrame:
    """Split the combined metadata column into individual columns."""
    info_column = df.columns[0]

    metadata_columns = info_column.split(",")

    df[metadata_columns] = (
        df[info_column]
        .str.strip()
        .str.split(",", expand=True)
    )

    return df.drop(columns=[info_column])


def reshape_data(df: pd.DataFrame) -> pd.DataFrame:
    """Convert yearly income columns from wide to long format."""
    return df.melt(
        id_vars=ID_VARS,
        var_name="year",
        value_name="income"
    )


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean values, rename columns, and remove unused fields."""
    df.columns = df.columns.str.strip()

    for col in df.columns:
        df[col] = df[col].str.strip()

    return (
        df
        .replace(":", None)
        .rename(columns=COLUMN_RENAMES)
        .drop(columns="freq")
    )


def extract_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Separate income values from any accompanying flag codes."""
    split = (
        df["income"]
        .str.split(r"\s+", n=1, expand=True)
    )

    return df.assign(
        income=split[0],
        flag=split[1],
    )


def materialize_star_schema(df: pd.DataFrame) -> None:
    """
    Create dimension tables and a fact table from cleaned data, then
    persist them as CSV files in a star schema layout.

    Dimensions are generated via `create_dimensions`, surrogate keys
    are mapped onto the fact table, and both facts and dimensions are
    written to `PROCESSED_DATA_DIR`.
    """
    fact = df.copy()
    dims = create_dimensions(df)

    for dim_name, (natural_key, surrogate_key) in DIMENSION_KEYS.items():
        dim_df = dims[dim_name]

        lookup = dim_df.set_index(natural_key)[surrogate_key]
        fact[surrogate_key] = fact[natural_key].map(lookup)

        dim_df.to_csv(
            PROCESSED_DATA_DIR / f"dim_{dim_name}.csv",
            index=False,
        )

    fact_income = fact[FACT_COLUMNS].copy()

    fact_income["income"] = pd.to_numeric(
        fact_income["income"],
        errors="coerce"
    )

    fact_income.to_csv(
        PROCESSED_DATA_DIR / "fact_income.csv",
        index=False,
    )


def sort_values(df: pd.DataFrame) -> pd.DataFrame:
    """Sort records using a consistent ordering for output."""
    order_mapping = {
        "year": False,
        "sex": True,
        "country_code": True,
        "statinfo": True,
        "age_group": True,
        "unit": True,
    }

    order = list(order_mapping.keys())
    rules = list(order_mapping.values())

    return df.sort_values(by=order, ascending=rules)


def main() -> None:
    df = (
        pd.read_csv(RAW_DATASET)
        .pipe(expand_info_column)
        .pipe(reshape_data)
        .pipe(clean_data)
        .pipe(extract_flags)
        .pipe(sort_values)
    )

    materialize_star_schema(df)


if __name__ == "__main__":
    main()
