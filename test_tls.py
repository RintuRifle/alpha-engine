import yfinance as yf
import tls_client

s = tls_client.Session(client_identifier="chrome_120")
# yfinance session requires standard requests methods
class TLSAdapter:
    def __init__(self, session):
        self.session = session
        self.headers = {}
        self.cookies = {}
    def get(self, url, **kwargs):
        res = self.session.get(url, **kwargs)
        res.raise_for_status = lambda: None # Mock
        return res
    def post(self, url, **kwargs):
        return self.session.post(url, **kwargs)

s_adapted = TLSAdapter(s)
print(yf.download('IBM', start='2024-01-01', end='2024-02-01', session=s_adapted).head())
