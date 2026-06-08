from typing import TypedDict, Dict, Any

class OrderParameters(TypedDict, total=False):
    ticker: str
    action: str  # 'BUY' or 'SELL'
    quantity: float
    price: float
    date: Any

class TradeRecord(TypedDict):
    date: Any
    ticker: str
    action: str
    quantity: float
    price: float
    commission: float
    slippage: float
