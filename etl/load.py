"""
Manage the PostgreSQL database operations for the income ETL pipeline.

This module provides functions to create a database connection, reset the
database objects used by the pipeline, create the income analysis view, and
load the fact and dimension tables into PostgreSQL.

Database connection settings are loaded from environment variables defined
in the configured environment file. The star schema consists of country,
age, sex, statinfo, and unit dimensions, the income fact table, and an
analytical view for reporting.
"""

import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from etl.paths import ENV_FILE, INCOME_VIEW_SQL_FILE


def get_engine():
    """Create SQLAlchemy engine for PostgreSQL connection."""
    load_dotenv(dotenv_path=ENV_FILE)

    required_vars = [
        "DB_USER",
        "DB_PASSWORD",
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
    ]

    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    db_url = (
        f"postgresql+psycopg2://"
        f"{os.getenv('DB_USER')}:"
        f"{os.getenv('DB_PASSWORD')}@"
        f"{os.getenv('DB_HOST')}:"
        f"{os.getenv('DB_PORT')}/"
        f"{os.getenv('DB_NAME')}"
    )

    return create_engine(db_url)


def reset_database(engine):
    """Drop objects that are rebuilt by the ETL pipeline."""

    with engine.begin() as conn:
        conn.execute(text("""
            DROP VIEW IF EXISTS vw_income_analysis;
            DROP TABLE IF EXISTS fact_income;
            DROP TABLE IF EXISTS dim_age;
            DROP TABLE IF EXISTS dim_country;
            DROP TABLE IF EXISTS dim_sex;
            DROP TABLE IF EXISTS dim_statinfo;
            DROP TABLE IF EXISTS dim_unit;
        """))


def create_analysis_view(engine):
    """Create the analytical view from the SQL file."""

    view_sql = INCOME_VIEW_SQL_FILE.read_text(encoding="utf-8")

    with engine.begin() as conn:
        conn.execute(text(view_sql))


def load_star_schema(
        fact: pd.DataFrame,
        dims: dict[str, pd.DataFrame],
) -> None:
    """Load the dimensional model into PostgreSQL."""

    engine = get_engine()

    reset_database(engine)

    for name, df in dims.items():
        df.to_sql(
            name=f"dim_{name}",
            con=engine,
            if_exists="fail",
            index=False,
        )

    fact.to_sql(
        name="fact_income",
        con=engine,
        if_exists="fail",
        index=False,
    )

    create_analysis_view(engine)
