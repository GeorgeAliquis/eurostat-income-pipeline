import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
import pandas as pd

from etl.utils import ENV_PATH


def get_engine():
    """Create SQLAlchemy engine for PostgreSQL connection."""
    load_dotenv(dotenv_path=ENV_PATH)

    required_vars = ["DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT", "DB_NAME"]

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


def load_star_schema(
        fact: pd.DataFrame,
        dims: dict[str, pd.DataFrame]
) -> None:
    engine = get_engine()

    for name, df in dims.items():
        df.to_sql(f"dim_{name}", engine, if_exists="replace", index=False)

    fact.to_sql("fact_income", engine, if_exists="replace", index=False)
