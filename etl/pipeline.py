from etl.extract import fetch_eurostat_data, save_raw_data
from etl.transform import build_star_schema, save_to_csv
from etl.load import load_star_schema

from etl.utils import EUROSTAT_URL, RAW_DATASET


def run_pipeline():
    # 1. EXTRACT
    print("Fetching data...")
    df = fetch_eurostat_data(EUROSTAT_URL)

    print("Saving raw data...")
    save_raw_data(df, path=RAW_DATASET)

    # 2. TRANSFORM
    print("Building star schema...")
    fact, dims = build_star_schema()

    print("Saving star schema to CSVs...")
    save_to_csv(fact, dims)

    # 3. LOAD
    print("Loading into PostgreSQL...")
    load_star_schema(fact, dims)

    print("Pipeline completed successfully.")


if __name__ == "__main__":
    run_pipeline()