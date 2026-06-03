import requests
import pandas as pd

url = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/ilc_di03"

response = requests.get(url)
data = response.json()
df = pd.read_json(data)
print(df.head())