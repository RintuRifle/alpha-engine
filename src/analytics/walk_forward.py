import pandas as pd

class WalkForward:
    """Out-of-sample backtest splits (70/30)"""
    @staticmethod
    def split_data(df: pd.DataFrame, train_ratio: float = 0.7):
        if df.empty: return df, df
        split_idx = int(len(df) * train_ratio)
        train = df.iloc[:split_idx]
        test = df.iloc[split_idx:]
        return train, test
