from sqlalchemy import create_engine
import pandas as pd


DB_URI = "postgresql+psycopg2://postgres:password@localhost:5432/mydb"


def get_engine():
    """Create SQLAlchemy engine for PostgreSQL connection."""
    return create_engine(DB_URI)


def load_star_schema(fact: pd.DataFrame, dims: dict[str, pd.DataFrame]):
    engine = get_engine()

    for name, df in dims.items():
        df.to_sql(f"dim_{name}", engine, if_exists="replace", index=False)

    fact.to_sql("fact_income", engine, if_exists="replace", index=False)