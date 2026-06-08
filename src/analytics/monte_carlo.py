import numpy as np
import pandas as pd

class MonteCarlo:
    @staticmethod
    def simulate_paths(returns: pd.Series, num_sims: int = 100, horizon: int = 252) -> pd.DataFrame:
        if returns.empty: return pd.DataFrame()
        mu = returns.mean()
        std = returns.std()
        
        sims = []
        for _ in range(num_sims):
            path = np.random.normal(mu, std, horizon)
            sim_equity = np.cumprod(1 + path)
            sims.append(sim_equity)
            
        return pd.DataFrame(sims).T
