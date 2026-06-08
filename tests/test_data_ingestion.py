import pytest
from src.data.validator import DataValidator

def test_data_validator_cleans_nans(sample_ohlcv):
    # Introduce NaNs
    df = sample_ohlcv.copy()
    df.loc[5:10, 'close'] = None
    
    cleaned = DataValidator.clean_and_validate(df)
    assert not cleaned['close'].isnull().any()
