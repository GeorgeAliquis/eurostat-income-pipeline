"""
ETL dimension builders for transforming raw dataset columns into normalized lookup tables
(country, sex, unit, statinfo, age) with surrogate keys and derived attributes.
"""
import math
import os
import re
import time

import pandas as pd
import pycountry
import requests
from dotenv import load_dotenv

from etl.paths import ENV_FILE

COUNTRY_SPECIAL_CODES = {"EL", "UK", "XK"}

SPECIAL_CODES = {
    "EL": "Greece",  # Eurostat uses EL instead of GR
    "UK": "United Kingdom",  # legacy Eurostat code
    "XK": "Kosovo",

    "EA": "Euro area",
    "EA18": "Euro area (2014)",
    "EA19": "Euro area (2015–2022)",
    "EA20": "Euro area (2023–2025)",
    "EA21": "Euro area (from 2026)",

    "EU": "European Union",
    "EU15": "European Union (1995–2004)",
    "EU27_2007": "European Union (2007–2013)",
    "EU28": "European Union (2013–2020)",
    "EU27_2020": "European Union (from 2020)",
}

load_dotenv(dotenv_path=ENV_FILE)

API_KEY = os.getenv("REST_COUNTRIES_API_KEY")

COLOR_SIMILARITY_THRESHOLD = 75

SWATCH_PRIORITY = {
    "dark_vibrant": 0,
    "dark_muted": 1,
    "vibrant": 2,
    "muted": 3,
    "light_vibrant": 4,
    "light_muted": 5,
}


def create_dimensions(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """
    Build all dimension tables required by the data warehouse.

    Each dimension is created from the raw dataset and enriched with
    labels, ordering attributes, and surrogate keys where needed.
    """
    return {
        "country": create_country_dimension(df, include_flag_colors=True),
        "sex": create_sex_dimension(df),
        "unit": create_unit_dimension(df),
        "statinfo": create_statinfo_dimension(df),
        "age": create_age_dimension(df)
    }


def create_base_dimension(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """
    Create a clean base table from a single dataframe column.

    The function validates that the column exists, removes duplicate values,
    and sorts the result further dimension processing.
    """
    if col not in df.columns:
        raise ValueError(f"Missing column: {col}")

    return (
        df[[col]]
        .drop_duplicates()
        .sort_values(col)
        .reset_index(drop=True)
    )


def create_statinfo_dimension(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create the statistical information dimension with labels and surrogate keys.

    Raw statistic codes are mapped to user-friendly labels such as Mean and Median,
    then ordered consistently before sequential surrogate keys are assigned.
    """
    statinfo_dim = create_base_dimension(df, "statinfo")

    statinfo_dim["statinfo_label"] = statinfo_dim["statinfo"].map({
        "MEAN_EI": "Mean",
        "MED_EI": "Median",
    })

    statinfo_order = {
        "MEAN_EI": 1,
        "MED_EI": 2,
    }

    statinfo_dim["_sort_order"] = statinfo_dim["statinfo"].map(statinfo_order)

    statinfo_dim = (
        statinfo_dim
        .sort_values(by=["_sort_order"])
        .drop(columns=["_sort_order"])
        .reset_index(drop=True)
    )

    statinfo_dim.insert(
        0,
        "statinfo_id",
        range(1, len(statinfo_dim) + 1)
    )

    return statinfo_dim


def create_unit_dimension(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create the income unit dimension with labels and surrogate keys.

    Raw unit codes are mapped to user-friendly labels and arranged in a
    predefined order before sequential surrogate keys are assigned.
    """
    unit_dim = create_base_dimension(df, "unit")

    unit_dim["unit_label"] = unit_dim["unit"].map({
        "EUR": "Euro",
        "NAC": "National Currency",
        "PPS": "Purchasing Power Standard",
    })

    unit_order = {
        "EUR": 1,
        "PPS": 2,
        "NAC": 3,
    }

    unit_dim["_sort_order"] = unit_dim["unit"].map(unit_order)

    unit_dim = (
        unit_dim
        .sort_values(by=["_sort_order"])
        .drop(columns=["_sort_order"])
        .reset_index(drop=True)
    )

    unit_dim.insert(
        0,
        "unit_id",
        range(1, len(unit_dim) + 1)
    )

    return unit_dim


def create_sex_dimension(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create the sex dimension with user-friendly labels and surrogate keys.

    Raw Eurostat sex codes are mapped to All, Male, and Female, then
    ordered consistently before sequential surrogate keys are assigned.
    """
    sex_dim = create_base_dimension(df, "sex")

    sex_dim["sex_label"] = sex_dim["sex"].map({
        "T": "All",
        "M": "Male",
        "F": "Female",
    })

    sex_order = {
        "T": 1,
        "M": 2,
        "F": 3,
    }

    sex_dim["_sort_order"] = sex_dim["sex"].map(sex_order)

    sex_dim = (
        sex_dim
        .sort_values(by=["_sort_order"])
        .drop(columns=["_sort_order"])
        .reset_index(drop=True)
    )

    sex_dim.insert(
        0,
        "sex_id",
        range(1, len(sex_dim) + 1)
    )

    return sex_dim


def create_country_dimension(
        df: pd.DataFrame,
        include_flag_colors: bool = False,
) -> pd.DataFrame:
    """
    Create the country dimension with names, classification flags, and colors.

    Country codes are mapped to standard or custom names, including Eurostat
    special codes and European aggregates. Flag colors can optionally be
    retrieved from the REST Countries API when enabled and configured.
    """
    country_dim = create_base_dimension(df, "country_code")

    def enrich(code):
        if pd.isna(code):
            return pd.Series({
                "country_name": None,
                "is_country": False,
            })

        country = get_country(code)

        return pd.Series({
            "country_name": (
                    SPECIAL_CODES.get(code)
                    or (country.name if country else None)
            ),
            "is_country": (
                    code in COUNTRY_SPECIAL_CODES
                    or country is not None
            )
        })

    country_dim = country_dim.join(
        country_dim["country_code"].apply(enrich)
    )

    country_dim["flag_color"] = None

    if include_flag_colors and API_KEY:
        print("Fetching REST Countries data...")

        flag_colors = assign_flag_colors(
            country_dim.loc[
                country_dim["is_country"],
                "country_name",
            ]
        )

        country_dim["flag_color"] = (
            country_dim["country_name"].map(flag_colors)
        )

    elif include_flag_colors:
        print("Skipping flag colors: REST_COUNTRIES_API_KEY is not configured.")

    aggregate_order = {
        "Euro area": 1,
        "Euro area (2014)": 2,
        "Euro area (2015–2022)": 3,
        "Euro area (2023–2025)": 4,
        "Euro area (from 2026)": 5,
        "European Union": 6,
        "European Union (1995–2004)": 7,
        "European Union (2007–2013)": 8,
        "European Union (2013–2020)": 9,
        "European Union (from 2020)": 10,
    }

    country_dim["_sort_group"] = country_dim["is_country"].map({True: 0, False: 1})
    country_dim["_sort_order"] = country_dim["country_name"].map(aggregate_order)

    country_dim = (
        country_dim.sort_values(
            ["_sort_group", "_sort_order", "country_name"],
            ascending=[True, True, True],
            na_position="last",
        )
        .drop(columns=["_sort_group", "_sort_order"])
        .reset_index(drop=True)
    )

    country_dim.insert(
        0,
        "country_id",
        range(1, len(country_dim) + 1),
    )

    return country_dim


def get_country(code: str):
    """
    Look up a country by its ISO alpha-2 code using pycountry.

    Returns the matching country object when the code is recognized,
    or None when no matching country is found.
    """
    return pycountry.countries.get(alpha_2=code)


def assign_flag_colors(countries: pd.Series) -> dict[str, str | None]:
    """
    Assign a distinct flag-derived color to each country.

    Countries are processed sequentially so previously selected colors
    can be considered when choosing colors for subsequent countries.
    """

    used_colors = []
    flag_colors = {}

    for country in countries:
        colors = fetch_country_colors(country)
        color = choose_flag_color(colors, used_colors)

        flag_colors[country] = color

        if color is not None:
            used_colors.append(color)

    return flag_colors


def fetch_country_colors(
        country: str,
        max_retries: int = 3,
        initial_backoff: float = 1.0,
) -> dict | None:
    """
    Fetch flag color information for a country from the REST Countries API.

    The request is retried when the API returns a rate-limit response,
    using Retry-After or exponential backoff before trying again.
    """

    for attempt in range(max_retries + 1):
        response = requests.get(
            f"https://api.restcountries.com/countries/v5?q={country}",
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=20,
        )

        if response.status_code == 429:
            if attempt == max_retries:
                response.raise_for_status()

            retry_after = response.headers.get("Retry-After")

            if retry_after is not None:
                wait_time = float(retry_after)
            else:
                wait_time = initial_backoff * (2 ** attempt)

            time.sleep(wait_time)
            continue

        response.raise_for_status()

        data = response.json()
        objects = data.get("data", {}).get("objects", [])

        if not objects:
            return None

        colors = objects[0].get("flag", {}).get("colors")

        return colors if colors else None

    return None


def choose_flag_color(
        colors: dict | None,
        used_colors: list[str],
) -> str | None:
    """
    Select a suitable flag color for a chart series.

    Candidate colors are evaluated based on prominence, contrast, and
    similarity to colors already assigned to other countries.
    """
    if colors is None:
        return None

    dominant = colors["dominant"]
    prominent = colors["prominent"]

    palette = sorted(
        colors["palette"],
        key=lambda x: x["proportion"],
        reverse=True,
    )

    swatches = {
        key: value
        for key, value in sorted(
            (
                (key, value)
                for key, value in colors["swatches"].items()
                if value is not None
            ),
            key=lambda item: SWATCH_PRIORITY[item[0]],
        )
    }

    candidates = [
        dominant,
        prominent,
        *[color["hex"] for color in palette],
        *swatches.values(),
    ]

    for candidate in candidates:
        if is_visually_too_light(candidate):
            continue

        if any(
                colors_are_too_similar(candidate, used_color)
                for used_color in used_colors
        ):
            continue

        return candidate

    # If no sufficiently distinct color is available,
    # fall back to the first color that is not visually too light.
    for candidate in candidates:
        if not is_visually_too_light(candidate):
            return candidate

    return dominant or None


def colors_are_too_similar(
        color_a: str,
        color_b: str,
        threshold: float = COLOR_SIMILARITY_THRESHOLD,
) -> bool:
    """
    Check whether two hexadecimal colors are visually too similar.

    The function calculates the Euclidean distance between their RGB values
    and compares it with the specified similarity threshold.
    """
    color_a = color_a.lstrip("#")
    color_b = color_b.lstrip("#")

    r1, g1, b1 = (
        int(color_a[0:2], 16),
        int(color_a[2:4], 16),
        int(color_a[4:6], 16),
    )

    r2, g2, b2 = (
        int(color_b[0:2], 16),
        int(color_b[2:4], 16),
        int(color_b[4:6], 16),
    )

    distance = math.sqrt(
        (r1 - r2) ** 2 +
        (g1 - g2) ** 2 +
        (b1 - b2) ** 2
    )

    return distance < threshold


def is_visually_too_light(
        hex_color: str,
        min_contrast: float = 3.0,
) -> bool:
    """
    Check whether a hexadecimal color has sufficient contrast against white.

    The function calculates the color's relative luminance and contrast ratio
    to determine whether it may be difficult to see on a white background.
    """
    hex_color = hex_color.lstrip("#")

    r = int(hex_color[0:2], 16) / 255
    g = int(hex_color[2:4], 16) / 255
    b = int(hex_color[4:6], 16) / 255

    def linearize(channel: float) -> float:
        if channel <= 0.04045:
            return channel / 12.92
        return ((channel + 0.055) / 1.055) ** 2.4

    r = linearize(r)
    g = linearize(g)
    b = linearize(b)

    luminance = (
            0.2126 * r
            + 0.7152 * g
            + 0.0722 * b
    )

    contrast_ratio = 1.05 / (luminance + 0.05)

    return contrast_ratio < min_contrast


def create_age_dimension(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create the age dimension with parsed age metadata and surrogate keys.

    Age group codes are converted into structured age information and
    ordered by age category and numeric boundary for consistent presentation.
    """
    age_dim = create_base_dimension(df, "age_group")

    age_info = age_dim["age_group"].apply(parse_age_group)

    age_dim = pd.concat(
        [age_dim, age_info.apply(pd.Series)],
        axis="columns"
    )

    age_dim["_type_order"] = age_dim["age_type"].map({
        "TOTAL": 1,
        "RANGE": 2,
        "OPEN_ENDED": 3,
        "UPPER_BOUNDED": 4,
    })

    age_dim["_age_sort"] = age_dim["min_age"].fillna(age_dim["max_age"])

    age_dim = (
        age_dim.sort_values(
            ["_type_order", "_age_sort"],
            ascending=[True, True],
            na_position="last",
        )
        .drop(columns=["_type_order", "_age_sort"])
        .reset_index(drop=True)
    )

    age_dim.insert(
        0,
        "age_id",
        range(1, len(age_dim) + 1)
    )

    return age_dim


def parse_age_group(age_code: str) -> dict:
    """
    Parse a Eurostat age group code into structured age metadata.

    Recognized codes are converted into age boundaries, a category type,
    and a user-friendly label. Unrecognized codes are classified as `Other`.
    """
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
            "age_label": f"{match.group(1)}–{match.group(2)}"
        }

    if match := re.match(r"Y_GE(\d+)", age_code):
        return {
            "min_age": int(match.group(1)),
            "max_age": None,
            "age_type": "OPEN_ENDED",
            "age_label": f"{match.group(1)}+"
        }

    if match := re.match(r"Y_LT(\d+)", age_code):
        return {
            "min_age": None,
            "max_age": int(match.group(1)) - 1,
            "age_type": "UPPER_BOUNDED",
            "age_label": f"Under {match.group(1)}"
        }

    return {
        "min_age": None,
        "max_age": None,
        "age_type": "OTHER",
        "age_label": "Other"
    }
