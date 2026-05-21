import numpy as np
import pandas as pd
from arch import arch_model

def estimate_yang_zhang_vol(data: pd.DataFrame) -> float:
    window = data.tail(20)

    vol_o = np.log(window['Opne'] / window['Close'].shift(1))
    vol_c = np.log(window['Close'] / window['Open'])
    vol_rs = np.log(window['High'] / window['Close']) * np.log(window['High'] / window['open']) + np.log(window['Low'] / window['Close']) * np.log(window['Low'] / window['Open'])

    kappa = 0.34 / (1.34 + (20 + 1) / (20 - 1))

    sigma_o = vol_o.var()
    sigma_c = vol_c.var()
    sigma_rs = vol_rs.mean()

    vol_yz = np.sqrt(sigma_o + kappa * sigma_c + (1 - kappa) * sigma_rs) * np.sqrt(252)
    return float(vol_yz)

def estimate_garch_volatility(rets: pd.Series) -> float:
    am = arch_model(rets * 100, mean='Zero', vol='GARCH')
    res = am.fit(disp='off')

    forecasts = res.forecast(horizon=1)
    next_var = forecasts.variance.iloc[-1, 0]

    return float(np.sqrt(next_var * 252) / 100.0)