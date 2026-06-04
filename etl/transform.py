import pandas as pd

df = pd.read_csv("../data/raw/estat_ilc_di03.tsv")

df_long = df.melt(
    id_vars=["freq", "age", "sex", "statinfo", "unit", r"geo\TIME_PERIOD"],
    var_name="year",
    value_name="income"
)