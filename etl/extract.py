import eurostat

df = eurostat.get_data_df('ilc_di03')

df_long = df.melt(
    id_vars=["freq", "age", "sex", "statinfo", "unit", r"geo\TIME_PERIOD"],
    var_name="year",
    value_name="income"
)

df.to_csv('eurostat.csv', index=False)
df_long.to_csv('long_eurostat.csv', index=False)