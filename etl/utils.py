from pathlib import Path

# Paths & URLs
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

EUROSTAT_URL = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/ilc_di03?format=TSV"
