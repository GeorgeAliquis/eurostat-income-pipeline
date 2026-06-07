from pathlib import Path

# ==========================
# PATHS & URLS
# ==========================
EUROSTAT_URL = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/ilc_di03?format=TSV"

ROOT = Path(__file__).resolve().parent.parent

ENV_FILE = ROOT / ".env"
DATA_DIR = ROOT / "data"

RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

RAW_DATASET = RAW_DATA_DIR / "estat_ilc_di03.csv"
