"""
ETL dimension builders for transforming raw dataset columns into normalized lookup tables
(country, sex, unit, statinfo, age) with surrogate keys and derived attributes.
"""
import re
import pandas as pd
import pycountry

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

YEAR_RE = re.compile(r"\d{4}")


def create_dimensions(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Build all dimension tables from a raw dataframe."""
    return {
        "country": create_country_dimension(df),
        "sex": create_sex_dimension(df),
        "unit": create_unit_dimension(df),
        "statinfo": create_statinfo_dimension(df),
        "age": create_age_dimension(df)
    }


def create_statinfo_dimension(df: pd.DataFrame) -> pd.DataFrame:
    """Create statinfo dimension table with surrogate key."""
    statinfo_dim = create_dimension(df, "statinfo")

    statinfo_dim["statinfo_label"] = statinfo_dim["statinfo"].map({
        "MEAN_EI": "Average Equivalised Income",
        "MED_EI": "Median Equivalised Income",
    })


    statinfo_dim.insert(
        0,
        "statinfo_id",
        range(1, len(statinfo_dim) + 1)
    )

    return statinfo_dim


def create_unit_dimension(df: pd.DataFrame) -> pd.DataFrame:
    """Create unit dimension table with surrogate key."""
    unit_dim = create_dimension(df, "unit")

    unit_dim["unit_label"] = unit_dim["unit"].map({
        "EUR": "Euro",
        "NAC": "National Currency",
        "PPS": "Purchasing Power Standard",
    })

    unit_dim.insert(
        0,
        "unit_id",
        range(1, len(unit_dim) + 1)
    )

    return unit_dim


def create_sex_dimension(df: pd.DataFrame) -> pd.DataFrame:
    """Create sex dimension with category mapping and surrogate key."""
    sex_dim = create_dimension(df, "sex")

    sex_dim["sex_label"] = sex_dim["sex"].map({
        "T": "All",
        "M": "Male",
        "F": "Female",
    })

    sex_dim.insert(
        0,
        "sex_id",
        range(1, len(sex_dim) + 1)
    )

    return sex_dim


def create_country_dimension(df: pd.DataFrame) -> pd.DataFrame:
    """Create country dimension with name lookup and metadata flags."""
    country_dim = create_dimension(df, "country_code")

    def enrich(code):
        if pd.isna(code):
            return pd.Series({
                "country_name": None,
                "is_country": False,
                "is_time_period": False,
            })

        country = get_country(code)

        return pd.Series({
            "country_name": SPECIAL_CODES.get(code) or (country.name if country else None),
            "is_country": code in COUNTRY_SPECIAL_CODES or country is not None,
            "is_time_period": YEAR_RE.search(code) is not None,
        })

    country_dim = country_dim.join(
        country_dim["country_code"].apply(enrich)
    )

    country_dim.insert(
        0,
        "country_id",
        range(1, len(country_dim) + 1)
    )

    return country_dim


def get_country(code: str):
    """Return pycountry country object for a given ISO alpha-2 code."""
    return pycountry.countries.get(alpha_2=code)


def create_age_dimension(df: pd.DataFrame) -> pd.DataFrame:
    """Create age dimension with parsed age ranges and labels."""
    age_dim = create_dimension(df, "age_group")

    age_info = age_dim["age_group"].apply(parse_age_group)

    age_dim = pd.concat(
        [age_dim, age_info.apply(pd.Series)],
        axis="columns"
    )

    age_dim.insert(
        0,
        "age_id",
        range(1, len(age_dim) + 1)
    )

    return age_dim


def create_dimension(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """Create a deduplicated sorted dimension table for a given column."""
    assert col in df.columns

    return (
        df[[col]]
        .drop_duplicates()
        .sort_values(col)
        .reset_index(drop=True)
    )


def parse_age_group(age_code: str) -> dict:
    """Parse age group codes into structured age metadata."""
    if age_code == "TOTAL":
        return {
            "min_age": None,
            "max_age": None,
            "age_type": "TOTAL",
            "age_label": "All ages"
        }

    if match := re.match(r"Y(\d+)-(\d+)", age_code):
        return {
            "min_age": int(match.group(1)),
            "max_age": int(match.group(2)),
            "age_type": "RANGE",
            "age_label": f"{match.group(1)}-{match.group(2)} years"
        }

    if match := re.match(r"Y_GE(\d+)", age_code):
        return {
            "min_age": int(match.group(1)),
            "max_age": None,
            "age_type": "OPEN_ENDED",
            "age_label": f"{match.group(1)}+ years"
        }

    if match := re.match(r"Y_LT(\d+)", age_code):
        return {
            "min_age": None,
            "max_age": int(match.group(1)) - 1,
            "age_type": "UPPER_BOUNDED",
            "age_label": f"Under {match.group(1)} years"
        }

    return {
        "min_age": None,
        "max_age": None,
        "age_type": "OTHER",
        "age_label": "Other"
    }
