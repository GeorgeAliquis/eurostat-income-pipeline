import pandas as pd

url = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/ilc_di03?format=TSV&compressed=true"

df = pd.read_csv(
    url,
    sep="\t",
    compression="gzip"
)

df.to_csv("../data/raw/ilc_di03.tsv", index=False)