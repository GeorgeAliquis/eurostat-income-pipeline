import pandas as pd
import pycountry
from pathlib import Path

from etl.utils import RAW_DATASET


SPECIAL_CODES = {
    "EL": "Greece",            # Eurostat uses EL instead of GR
    "UK": "United Kingdom",    # legacy Eurostat code
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

def read_raw_data(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path)

def expand_info_column(df: pd.DataFrame) -> pd.DataFrame:
    info_col = df.columns[0]

    split_cols = info_col.split(",")

    df[split_cols] = (
        df[info_col]
        .str.strip()
        .str.split(",", expand=True)
    )

    df.drop(columns=[info_col], inplace=True)

    return df


def reshape_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.melt(
        id_vars=["freq", "age_group", "gender", "statinfo", "unit", "geo\\TIME_PERIOD"],
        var_name="year",
        value_name="income"
    )

    df["country_name"] = df["geo\\TIME_PERIOD"].apply(code_to_country)

    return df

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = df.columns.str.strip()

    for col in df.columns:
        df[col] = df[col].str.strip()

    df = (
        df
        .replace(":", None)
        .rename(columns={
            "age": "age_group",
            "sex": "gender",
        })
    )

    return df


def extract_flags(df: pd.DataFrame) -> pd.DataFrame:
    split = (
        df["income"]
        .str.split(r"\s+", n=1, expand=True)
    )

    df["income"] = split[0]
    df["flag"] = split[1]

    return df


def create_dimensions():
    pass


def save_processed_files():
    pass


def code_to_country(code):
    if pd.isna(code):
        return None

    if code in SPECIAL_CODES:
        return SPECIAL_CODES[code]

    country = pycountry.countries.get(alpha_2=code)
    return country.name if country else None


if __name__ == "__main__":
    df = (
        read_raw_data(RAW_DATASET)
                .pipe(expand_info_column)
                .pipe(clean_data)
                .pipe(reshape_data)
                .pipe(extract_flags)
    )

    df.to_csv(RAW_DATASET.parent / "text.csv", index=False)
