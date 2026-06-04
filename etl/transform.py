import pandas as pd
import pycountry
from pathlib import Path

from etl.utils import RAW_DATA_DIR


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
        id_vars=["freq", "age", "sex", "statinfo", "unit", "geo\\TIME_PERIOD"],
        var_name="year",
        value_name="income"
    )

    return df

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        df[col] = df[col].str.strip()

    df = (
        df
        .rename(columns={
            "age": "age_group",
            "sex": "gender",
        })
        .replace(":", pd.NA)
    )

    return df


def extract_flags(df: pd.DataFrame) -> pd.DataFrame:
    df[["year", "flag"]] = (
        df["year"]
        .str.split(expand=True)
    )

    return df

def create_dimensions():
    pass

def save_processed_files():
    pass


def code_to_country(code):
    country = pycountry.countries.get(alpha_2=code.upper())
    return country.name if country else None

file = RAW_DATA_DIR / "estat_ilc_di03.csv"
df = (
    read_raw_data(file)
            .pipe(expand_info_column)
            .pipe(reshape_data)
            .pipe(clean_data)
)
