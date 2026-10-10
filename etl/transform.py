"""
Transform raw Eurostat income data into a star-schema dataset.

This module cleans and reshapes income data into long format, extracts
observation flags, attaches dimension surrogate keys, and builds the fact
and dimension tables. It also calculates international income benchmarks
(percentiles and mean) from eligible country-level observations, appends
them to the fact table, and exports the resulting tables as CSV files.

Main entry point:
    build_star_schema(): Builds and returns the fact table and dimensions.
"""
import pandas as pd

from etl.paths import RAW_DATASET, PROCESSED_DATA_DIR
from etl.dimensions import create_dimensions, build_dim_aggregate, insert_id_column

COLUMN_RENAMES = {
    "geo\\TIME_PERIOD": "country_code",
}

ID_VARS = [
    "freq",
    "age",
    "sex",
    "statinfo",
    "unit",
    "geo\\TIME_PERIOD",
]

DIMENSION_KEYS = {
    "country": ("country_code", "country_id"),
    "sex": ("sex", "sex_id"),
    "unit": ("unit", "unit_id"),
    "statinfo": ("statinfo", "statinfo_id"),
    "age": ("age", "age_id"),
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
    "country_count",
]

GROUP_COLS = [
    "year",
    "sex_id",
    "age_id",
    "unit_id",
    "statinfo_id",
]


def expand_info_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Expand the packed metadata column into separate columns.

    The first column contains comma-separated metadata field names and
    values. This function extracts the field names from the column header,
    splits each row into the corresponding fields, and removes the original
    packed column.

    Parameters
    ----------
    df : pd.DataFrame
        Raw dataset containing the packed metadata column.

    Returns
    -------
    pd.DataFrame
        Dataset with the metadata fields expanded into individual columns.
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
    Standardize column names and clean raw dataset values.

    Column names and string values are stripped of surrounding whitespace.
    The Eurostat missing-value marker ':' is replaced with a missing value,
    raw column names are normalized using COLUMN_RENAMES, and the redundant
    frequency column is removed. The year column is converted to integers;
    missing or invalid years raise an error.

    Parameters
    ----------
    df : pd.DataFrame
        Long-format dataset produced by reshape_data().

    Returns
    -------
    pd.DataFrame
        Cleaned dataset with standardized column names and integer years.

    Raises
    ------
    ValueError
        If year values are missing or cannot be converted to integers.
    """

    df.columns = df.columns.str.strip()

    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].str.strip()

    df = df.replace(":", pd.NA)

    if df["year"].isna().any():
        raise ValueError("Year contains null values")

    df["year"] = df["year"].astype(int)

    return (
        df
        .rename(columns=COLUMN_RENAMES)
        .drop(columns="freq")
    )


def extract_flags(df: pd.DataFrame) -> pd.DataFrame:
    """
    Separate income values from optional Eurostat data-quality flags.

    Income entries may contain a numeric value followed by a whitespace-
    separated flag. The function splits these entries into an income column
    and a flag column, converting income values to pandas' nullable integer
    type. Missing flags are represented by missing values.

    Parameters
    ----------
    df : pd.DataFrame
        Dataset containing an income column with optional embedded flags.

    Returns
    -------
    pd.DataFrame
        Dataset with numeric income values and a separate flag column.
    """
    split = (
        df["income"]
        .str.split(r"\s+", n=1, expand=True)
    )

    return df.assign(
        income=split[0].astype("Int64"),
        flag=split[1],
    )


def sort_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sort raw observations into a deterministic order.

    Observations are ordered by year, sex, country, statistic, age group,
    and unit using the predefined ascending or descending directions.
    This provides consistent processing and CSV output across runs.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned long-format observations.

    Returns
    -------
    pd.DataFrame
        Observations sorted by the configured column ordering.
    """

    order_mapping = {
        "year": False,
        "sex": True,
        "country_code": True,
        "statinfo": True,
        "age": True,
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
    Build the income star schema from the raw Eurostat dataset.

    The pipeline loads and expands the raw data, reshapes annual observations
    into long format, cleans values, extracts data-quality flags, and creates
    the dimension tables. It then maps natural keys to dimension surrogate
    keys and constructs the fact table using the required schema.

    Finally, it calculates European income benchmarks (P10, P25, P50, P75,
    P90, and mean) from individual-country observations, excluding national
    currency (NAC) values. The benchmark dimension rows are appended to
    dim_country, and the calculated benchmark observations are appended to
    fact_income.

    Returns
    -------
    tuple[pd.DataFrame, dict[str, pd.DataFrame]]
        A tuple containing:
        - The fact table, including original observations and calculated
          European benchmark rows.
        - The dimension tables, including the six additional benchmark
          entries in the country dimension.

    Notes
    -----
    The returned tables are ready for CSV export or downstream database
    loading. This function constructs the schema in memory but does not
    persist the output.
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

    fact["country_count"] = pd.NA
    fact = fact[FACT_COLUMNS].copy()

    # Append the six calculated benchmark series.
    fact, dims = append_international_aggregates(fact, dims)

    return fact, dims


def build_international_aggregates(
        fact_income: pd.DataFrame,
        dim_country: pd.DataFrame,
        dim_unit: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate European income benchmarks for each observation group.

    Only rows representing individual countries with non-missing income are
    included. National currency (NAC) observations and existing geographic
    aggregates, such as the EU and euro area, are excluded.

    For each combination of year, sex, age, unit, and statistic, the function
    calculates the 10th, 25th, 50th, 75th, and 90th income percentiles and
    the arithmetic mean. It also counts the distinct contributing countries.

    Each country contributes one country-level income value to the
    calculation; the statistics are not weighted by population. Percentiles
    use pandas' default quantile interpolation method.

    Parameters
    ----------
    fact_income : pd.DataFrame
        Fact table containing income values and dimension foreign keys.
    dim_country : pd.DataFrame
        Country dimension containing country_id and is_country.
    dim_unit : pd.DataFrame
        Unit dimension containing unit_id and unit.

    Returns
    -------
    pd.DataFrame
        Wide-format benchmark data, with one row per observation group,
        separate columns for each benchmark, and country_count.
    """
    # Identify the national-currency unit ID
    nac_unit_id = dim_unit.loc[
        dim_unit["unit"].eq("NAC"),
        "unit_id",
    ]

    # Add country metadata to each fact row
    df = fact_income.merge(
        dim_country[["country_id", "is_country"]],
        on="country_id",
        how="left",
        validate="many_to_one",
    )

    # Keep individual countries; exclude EU and euro-area aggregates
    df = df[
        df["is_country"].eq(True)
        & ~df["unit_id"].isin(nac_unit_id)
        ].copy()

    df = df.dropna(subset=["income"])

    international_aggregates = (
        df.groupby(GROUP_COLS, dropna=False)
        .agg(
            P10=("income", lambda s: s.quantile(0.10)),
            P25=("income", lambda s: s.quantile(0.25)),
            P50=("income", "median"),
            P75=("income", lambda s: s.quantile(0.75)),
            P90=("income", lambda s: s.quantile(0.90)),
            MEAN=("income", "mean"),
            country_count=("country_id", "nunique"),
        )
        .reset_index()
    )

    return international_aggregates


def reshape_international_aggregates(
        international_wide: pd.DataFrame,
        dim_aggregate: pd.DataFrame,
) -> pd.DataFrame:
    """
    Convert calculated European benchmarks into fact-table rows.

    The wide-format benchmark columns are melted into long format, so each
    benchmark becomes a separate observation. Benchmark codes are mapped
    to their surrogate country IDs using the supplied aggregate dimension.
    Income values are rounded to the nearest integer and converted to
    pandas' nullable integer type. The flag column is set to missing.

    Parameters
    ----------
    international_wide : pd.DataFrame
        Wide-format benchmark results containing grouping keys, benchmark
        values, and the number of contributing countries.
    dim_aggregate : pd.DataFrame
        Dimension rows containing country_code and country_id for each
        calculated benchmark.

    Returns
    -------
    pd.DataFrame
        Long-format benchmark observations ready to append to the fact table.

    Raises
    ------
    ValueError
        If any benchmark code cannot be matched to a dimension row.
    """
    id_cols = GROUP_COLS + ["country_count"]

    aggregate_columns = [
        "P10", "P25", "P50", "P75", "P90", "MEAN",
    ]

    international_long = international_wide.melt(
        id_vars=id_cols,
        value_vars=aggregate_columns,
        var_name="country_code",
        value_name="income",
    )

    international_long = international_long.merge(
        dim_aggregate[
            ["country_id", "country_code"]
        ],
        on="country_code",
        how="left",
        validate="many_to_one",
    )

    if international_long["country_id"].isna().any():
        raise ValueError(
            "An aggregate code could not be matched to dim_aggregate."
        )

    international_long = international_long.drop(
        columns=["country_code"]
    )

    international_long["flag"] = pd.NA

    international_long["income"] = (
        international_long["income"]
        .round()
        .astype("Int64")
    )

    return international_long


def append_international_aggregates(
        fact: pd.DataFrame,
        dims: dict[str, pd.DataFrame],
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    """
    Calculate and append European benchmarks to the existing star schema.

    The function calculates benchmark statistics from eligible country-level
    observations, creates dimension entries for P10, P25, P50, P75, P90,
    and MEAN, and assigns them new country surrogate IDs. These entries are
    appended to dim_country, while the corresponding benchmark observations
    are appended to the existing fact table.

    Original country observations are retained. Benchmark rows use the same
    columns as the original fact table and include country_count, indicating
    the number of distinct countries contributing to each calculation.

    Parameters
    ----------
    fact : pd.DataFrame
        Fact table containing country-level observations and foreign keys.
    dims : dict[str, pd.DataFrame]
        Dimension tables, including country and unit dimensions.

    Returns
    -------
    tuple[pd.DataFrame, dict[str, pd.DataFrame]]
        The expanded fact table and updated dimension dictionary.
    """
    print("Calculating European benchmarks...")

    # Calculate benchmarks using individual countries only.
    international_wide = build_international_aggregates(
        fact_income=fact,
        dim_country=dims["country"],
        dim_unit=dims["unit"],
    )

    # Build aggregate rows and assign country IDs.
    aggregate_dim = build_dim_aggregate()

    next_country_id = int(dims["country"]["country_id"].max()) + 1

    aggregate_dim = insert_id_column(
        aggregate_dim,
        column_name="country_id",
        start=next_country_id,
    )

    aggregate_dim["is_country"] = False

    # Append aggregate rows to dim_country.
    dim_country = pd.concat(
        [
            dims["country"],
            aggregate_dim.reindex(columns=dims["country"].columns),
        ],
        ignore_index=True,
    )

    # Reshape benchmarks and map their codes to dim_country IDs.
    international_long = reshape_international_aggregates(
        international_wide=international_wide,
        dim_aggregate=aggregate_dim,
    )

    # Keep the same schema for country observations and aggregate observations.
    fact = fact.copy()
    if "country_count" not in fact.columns:
        fact["country_count"] = pd.NA

    international_long = international_long.reindex(columns=fact.columns)

    # Append aggregate observations to the existing fact table.
    fact = pd.concat(
        [fact, international_long],
        ignore_index=True,
    )

    dims = dims.copy()
    dims["country"] = dim_country

    return fact, dims


def save_to_csv(
        fact: pd.DataFrame,
        dims: dict[str, pd.DataFrame]
) -> None:
    """
    Export the fact table and dimension tables as CSV files.

    Each dimension is written to a file named dim_<dimension>.csv, and the
    fact table is written to fact_income.csv. All files are saved in
    PROCESSED_DATA_DIR, overwriting existing files with the same names.

    Parameters
    ----------
    fact : pd.DataFrame
        Final fact table, including calculated European benchmark rows.
    dims : dict[str, pd.DataFrame]
        Final dimension tables, including benchmark entries in dim_country.

    Returns
    -------
    None

    Side Effects
    ------------
    Creates output files in PROCESSED_DATA_DIR.
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
