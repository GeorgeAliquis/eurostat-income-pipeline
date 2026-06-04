import pandas as pd
import pycountry
from pathlib import Path

from etl.utils import RAW_DATASET, PROCESSED_DATA_DIR

COUNTRY_SPECIAL_CODES = {"EL", "UK", "XK"}

SPECIAL_CODES = {
    "EL": "Greece",  # Eurostat uses EL instead of GR
    "UK": "United Kingdom",  # legacy Eurostat code
    "MK": "Skopje",
    "XK": "Kosovo",

    "EA": "Euro Area",
    "EA18": "Euro Area (18 countries)",
    "EA19": "Euro Area (19 countries)",
    "EA20": "Euro Area (20 countries)",
    "EA21": "Euro Area (21 countries)",

    "EU": "European Union",
    "EU15": "European Union (15 countries)",
    "EU27_2007": "European Union (27 countries, 2007 composition)",
    "EU27_2020": "European Union (27 countries, post-Brexit)",
    "EU28": "European Union (28 countries)",
}

COLUMN_RENAMES = {
    "age": "age_group",
    "sex": "gender",
    "geo\\TIME_PERIOD": "country_code",
}

ID_VARS = ["freq", "age_group", "gender", "statinfo", "unit", "country_code"]


def read_raw_data(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path)


def expand_info_column(df: pd.DataFrame) -> pd.DataFrame:
    info_columns = df.columns[0]

    metadata_columns = info_columns.split(",")

    df[metadata_columns] = (
        df[info_columns]
        .str.strip()
        .str.split(",", expand=True)
    )

    return df.drop(columns=[info_columns])


def reshape_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.melt(
        id_vars=ID_VARS,
        var_name="year",
        value_name="income"
    )

    return df.assign(
        country_name=df["country_code"].map(code_to_country),
        is_country=df["country_code"].map(is_country_code),
    )


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = df.columns.str.strip()

    for col in df.columns:
        df[col] = df[col].str.strip()

    return (
        df
        .replace(":", None)
        .rename(columns=COLUMN_RENAMES)
    )


def extract_flags(df: pd.DataFrame) -> pd.DataFrame:
    split = (
        df["income"]
        .str.split(r"\s+", n=1, expand=True)
    )

    return df.assign(
        income=split[0],
        flag=split[1],
    )


def create_dimensions():
    pass


def save_processed_files():
    pass


def code_to_country(code: str | None) -> str | None:
    if pd.isna(code):
        return None

    if code in SPECIAL_CODES:
        return SPECIAL_CODES[code]

    country = pycountry.countries.get(alpha_2=code)
    return country.name if country else None


def is_country_code(code: str | None) -> bool:
    if pd.isna(code):
        return False

    if code in COUNTRY_SPECIAL_CODES:
        return True

    return pycountry.countries.get(alpha_2=code) is not None


if __name__ == "__main__":
    df = (
        read_raw_data(RAW_DATASET)
        .pipe(expand_info_column)
        .pipe(clean_data)
        .pipe(reshape_data)
        .pipe(extract_flags)
    )

    df.to_csv(PROCESSED_DATA_DIR / "processed.csv", index=False)
