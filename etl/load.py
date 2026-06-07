import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
import pandas as pd


def get_engine():
    """Create SQLAlchemy engine for PostgreSQL connection."""
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")

    if not db_url:
        raise ValueError("db_url is not set in .env file.")

    return create_engine(db_url)


def load_star_schema(fact: pd.DataFrame, dims: dict[str, pd.DataFrame]):
    engine = get_engine()

    for name, df in dims.items():
        df.to_sql(f"dim_{name}", engine, if_exists="replace", index=False)

    fact.to_sql("fact_income", engine, if_exists="replace", index=False)