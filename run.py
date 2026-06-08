# run_data.py
from src.data.database import init_db
from src.data.fetcher import fetch_and_store_data

def main():
    print("🚀 Starting Data Setup...")
    
    # 1. Yeh database aur tables banayega (agar nahi bane hain toh)
    init_db()
    
    # 2. Hum Apple (AAPL) aur Reliance (RELIANCE.NS) ka pichle 2 saal ka data fetch karenge
    stocks = ["AAPL", "RELIANCE.NS"]
    start = "2023-01-01"
    end = "2024-01-01"
    
    for stock in stocks:
        fetch_and_store_data(stock, start, end)
        
    print("✅ Data Fetching Completed! Check data/market_data.db file.")

if __name__ == "__main__":
    main()