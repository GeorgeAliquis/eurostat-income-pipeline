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

    print("Resetting database objects...")
    reset_database(engine)

    print("Loading dimensions...")

    for name, df in dims.items():
        df.to_sql(
            f"dim_{name}",
            engine,
            if_exists="fail",
            index=False,
        )

    print("Loading fact table...")

    fact.to_sql(
        "fact_income",
        engine,
        if_exists="fail",
        index=False,
    )

    print("Creating analytical view...")
    create_analysis_view(engine)
