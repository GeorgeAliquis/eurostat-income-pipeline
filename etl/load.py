import requests
from pyjstat import pyjstat

url = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/ilc_di03?format=JSON&lang=en"

json_data = requests.get(url).json()

datasets = pyjstat.from_json_stat(json_data)

df = datasets[0]

df.to_csv("eurostat_test.csv", index=False)

print(df.head())
print(df.columns)