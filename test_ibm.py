import yfinance as yf
from curl_cffi import requests

s = requests.Session(impersonate='chrome')
print(yf.download('IBM', start='2024-01-01', end='2024-02-01', session=s).head())
