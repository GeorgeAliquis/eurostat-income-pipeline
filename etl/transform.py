import pandas as pd

df = pd.read_csv("../data/raw/estat_ilc_di03.tsv")

df_long = df.melt(
    id_vars=["freq", "age", "sex", "statinfo", "unit", r"geo\TIME_PERIOD"],
    var_name="year",
    value_name="income"
)

def read_raw_data():
    pass

def reshape_data():
    pass

def extract_flags():
    pass

def clean_data():
    pass

def create_dimensions():
    pass

def save_processed_files():
    pass