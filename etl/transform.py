"""
ETL pipeline for transforming raw income data into a cleaned fact table and
associated dimension tables.
"""
import pandas as pd

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
    """
    Expands a single combined metadata column into multiple structured columns.

    The raw dataset encodes multiple attributes (e.g. country, sex, unit)
    in a single comma-separated column. This function splits that column
    into separate fields and removes the original combined column.

    Returns
    -------
    DataFrame
        DataFrame with expanded metadata columns and no original packed column.
    """
    info_column = df.columns[0]

    metadata_columns = info_column.strip().split(",")

    df[metadata_columns] = (
        df[info_column]
        .str.strip()
        .str.split(",", expand=True)
    )

    return df.drop(columns=[info_column])


def reshape_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converts the dataset from wide format (years as columns)
    into long format (one row per year-observation).

    The resulting structure is suitable for analytical modeling
    and star schema fact table construction.

    Returns
    -------
    DataFrame
        Melted DataFrame with columns: id_vars + year + income
    """
    return df.melt(
        id_vars=ID_VARS,
        var_name="year",
        value_name="income"
    )


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardizes column names and cleans string-based values.

    Operations:
    - Strips whitespace from column names
    - Strips whitespace from string columns
    - Converts 'year' column dtype to integer
    - Replaces missing-value marker ':' with None
    - Renames raw dataset columns to standardized schema names
    - Removes redundant 'freq' column

    Returns
    -------
    DataFrame
        Cleaned and normalized dataset ready for transformation steps.
    """
    df.columns = df.columns.str.strip()

    for col in df.columns:
        df[col] = df[col].str.strip()

    assert df["year"].isna().sum() == 0

    df["year"] = df["year"].astype(int)

    return (
        df
        .replace(":", None)
        .rename(columns=COLUMN_RENAMES)
        .drop(columns="freq")
    )


def extract_flags(df: pd.DataFrame) -> pd.DataFrame:
    """
    Separates numeric income values from embedded quality/metadata flags.

    Some income entries contain a numeric value followed by a flag
    (e.g. estimation or data quality indicator). This function splits
    them into two explicit columns.

    Returns
    -------
    DataFrame
        DataFrame with:
        - income (numeric value as string at this stage)
        - flag (optional metadata indicator)
    """
    split = (
        df["income"]
        .str.split(r"\s+", n=1, expand=True)
    )

    return df.assign(
        income=split[0].astype(float),
        flag=split[1],
    )


def sort_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Applies deterministic ordering to the dataset for reproducible output.

    Sorting ensures consistent CSV exports and stable diffs between runs,
    which is useful for debugging and version control comparisons.

    Returns
    -------
    DataFrame
        Sorted DataFrame according to predefined ordering rules.
    """
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


def attach_surrogate_keys(
        fact: pd.DataFrame,
        dims: dict[str, pd.DataFrame]
) -> pd.DataFrame:
    """
    Maps natural keys in the fact table to surrogate keys from dimension tables.

    This function performs the dimensional modeling step of the ETL pipeline,
    replacing human-readable attributes with integer surrogate keys
    suitable for relational storage.

    Parameters
    ----------
    fact : DataFrame
        Fact table containing natural keys prior to dimension mapping.
    dims : dict[str, DataFrame]
        Dictionary of dimension tables keyed by dimension name.

    Returns
    -------
    DataFrame
        Fact table enriched with surrogate key foreign keys.
    """
    fact = fact.copy()

    for dim_name, (natural_key, surrogate_key) in DIMENSION_KEYS.items():
        dim_df = dims[dim_name]

        lookup = dim_df.set_index(natural_key)[surrogate_key]
        fact[surrogate_key] = fact[natural_key].map(lookup)

    return fact


def build_star_schema():
    """
    Executes the full transformation pipeline and constructs a star schema.

    Pipeline stages:
    1. Load raw dataset
    2. Expand packed metadata columns
    3. Reshape wide format into long format
    4. Clean and normalize values
    5. Extract data quality flags
    6. Sort for deterministic output
    7. Build dimension tables
    8. Attach surrogate keys to fact table
    9. Finalize fact table schema

    Returns
    -------
    fact : DataFrame
        Final fact table containing surrogate keys and analytical measures.
    dims : dict[str, DataFrame]
        Dictionary of dimension tables keyed by dimension name.

    Notes
    -----
    This function is the canonical "model builder" for both CSV export
    and database loading.
    """
    df = (
        pd.read_csv(RAW_DATASET)
        .pipe(expand_info_column)
        .pipe(reshape_data)
        .pipe(clean_data)
        .pipe(extract_flags)
        .pipe(sort_values)
    )

    dims = create_dimensions(df)
    fact = attach_surrogate_keys(df, dims)
    fact = fact[FACT_COLUMNS].copy()

    return fact, dims


def save_to_csv(
        fact: pd.DataFrame,
        dims: dict[str, pd.DataFrame]
) -> None:
    """
    Persists the star schema to disk as CSV files.

    This function is a pure I/O layer:
    it does not perform any transformation or schema inference.

    Outputs
    -------
    - One CSV file per dimension table (dim_<name>.csv)
    - One fact table CSV (fact_income.csv)

    Parameters
    ----------
    fact : DataFrame
        Final fact table with surrogate keys already applied.
    dims : dict[str, DataFrame]
        Dictionary of dimension tables.

    Side Effects
    ------------
    Writes files to PROCESSED_DATA_DIR.
    """
    for dim_name in DIMENSION_KEYS.keys():
        dims[dim_name].to_csv(
            PROCESSED_DATA_DIR / f"dim_{dim_name}.csv",
            index=False,
        )

    fact.to_csv(
        PROCESSED_DATA_DIR / "fact_income.csv",
        index=False,
    )
