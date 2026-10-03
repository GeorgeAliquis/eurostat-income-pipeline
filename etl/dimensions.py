"""
ETL dimension builders for transforming raw dataset columns into normalized lookup tables
(country, sex, unit, statinfo, age) with surrogate keys and derived attributes.
"""
import re
import pandas as pd
import pycountry
import requests
import math
import time
from dotenv import load_dotenv
import os

from etl.paths import ENV_FILE

COUNTRY_SPECIAL_CODES = {"EL", "UK", "XK"}

SPECIAL_CODES = {
    "EL": "Greece",  # Eurostat uses EL instead of GR
    "UK": "United Kingdom",  # legacy Eurostat code
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

load_dotenv(dotenv_path=ENV_FILE)

API_KEY = os.getenv("REST_COUNTRIES_API_KEY")

COLOR_SIMILARITY_THRESHOLD = 75


def create_dimensions(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Build all dimension tables from a raw dataframe."""
    return {
        "country": create_country_dimension(df),
        "sex": create_sex_dimension(df),
        "unit": create_unit_dimension(df),
        "statinfo": create_statinfo_dimension(df),
        "age": create_age_dimension(df)
    }


def create_dimension(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """Create a deduplicated sorted dimension table for a given column."""
    if col not in df.columns:
        raise ValueError(f"Missing column: {col}")

    return (
        df[[col]]
        .drop_duplicates()
        .sort_values(col)
        .reset_index(drop=True)
    )


def create_statinfo_dimension(df: pd.DataFrame) -> pd.DataFrame:
    """Create statinfo dimension table with surrogate key."""
    statinfo_dim = create_dimension(df, "statinfo")

    statinfo_dim["statinfo_label"] = statinfo_dim["statinfo"].map({
        "MEAN_EI": "Mean",
        "MED_EI": "Median",
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
            "country_name": (
                    SPECIAL_CODES.get(code)
                    or (country.name if country else None)
            ),
            "is_country": (
                    code in COUNTRY_SPECIAL_CODES
                    or country is not None
            ),
            "is_time_period": YEAR_RE.search(code) is not None,
        })

    country_dim = country_dim.join(
        country_dim["country_code"].apply(enrich)
    )

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

    country_dim.insert(
        0,
        "country_id",
        range(1, len(country_dim) + 1),
    )

    return country_dim


def get_country(code: str):
    """Return pycountry country object for a given ISO alpha-2 code."""
    return pycountry.countries.get(alpha_2=code)


def assign_flag_colors(countries: pd.Series) -> dict[str, str | None]:
    """Assign visually distinct flag colors to countries."""

    used_colors = []
    flag_colors = {}

    for country in countries:
        color = get_country_color(country, used_colors)

        flag_colors[country] = color

        if color is not None:
            used_colors.append(color)

    return flag_colors


def get_country_color(
        country: str,
        used_colors: list[str],
        max_retries: int = 3,
        initial_backoff: float = 1.0,
) -> str | None:
    """Fetch country flag colors from REST Countries and select a suitable color."""

    for attempt in range(max_retries + 1):
        response = requests.get(
            f"https://api.restcountries.com/countries/v5?q={country}",
            headers={"Authorization": f"Bearer {API_KEY}"},
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
        colors = data["data"]["objects"][0]["flag"]["colors"]

        return choose_flag_color(colors, used_colors)

    return None


def choose_flag_color(
        colors: dict,
        used_colors: list[str],
) -> str | None:
    """
    Select a visually distinct, sufficiently contrasting color for a chart line.

    Colors that are too light or too similar to previously used colors are
    skipped. If no suitable color is available, falls back to the first color
    that is not too close to white.
    """
    dominant = colors["dominant"]
    prominent = colors["prominent"]

    palette = sorted(
        colors["palette"],
        key=lambda x: x["proportion"],
        reverse=True,
    )

    swatches = {
        key: value
        for key, value in colors["swatches"].items()
        if value is not None
    }

    candidates = [
        dominant,
        prominent,
        *[color["hex"] for color in palette],
        *reversed(swatches.values()),
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
    # fall back to the first color that is not too close to white.
    for candidate in candidates:
        if not is_too_close_to_white(candidate):
            return candidate

    return dominant or None


def colors_are_too_similar(
        color_a: str,
        color_b: str,
        threshold: float = COLOR_SIMILARITY_THRESHOLD,
) -> bool:
    """Check whether two hex colors are too similar."""
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
        min_contrast: float = 2.5,
) -> bool:
    """Check whether a color has insufficient contrast against a white background."""
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


def is_too_close_to_white(
        hex_color: str,
        threshold: float = 70,
) -> bool:
    """Check whether a hex color is too close to white."""
    hex_color = hex_color.lstrip("#")

    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    distance = math.sqrt(
        (255 - r) ** 2 +
        (255 - g) ** 2 +
        (255 - b) ** 2
    )

    return distance < threshold


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
