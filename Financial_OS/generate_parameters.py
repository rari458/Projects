import json
import warnings
from datetime import datetime
import numpy as np
import pandas as pd
import yfinance as yf
import scipy.optimize as sco
from arch import arch_model

warnings.filterwarnings('ignore')

class AlphaFactory:

    def __init__(self, tickers: list, period: str = '2y'):
        self.tickers = tickers
        self.period = period
        self.data = pd.DataFrame()
        self.rets = pd.DataFrame()

    def fetch_data(self) -> None:
        print(f"[Alpha Factory] Fetching {self.period} data for {self.tickers}...")
        df = yf.download(self.tickers, period=self.period, progress=False)
        self.data = df['Close']
        self.rets = self.data.pct_change().dropna()

    def get_risk_parity_weights(self) -> dict:
        cov = self.rets.cov().values * 252
        noa = len(self.tickers)
        target_risk = np.full(noa, 1.0 / noa)

        def objective(weights):
            port_var = np.dot(weights.T, np.dot(cov, weights))
            marginal_contrib = np.dot(cov, weights)
            risk_contrib = weights * marginal_contrib / port_var
            return np.sum(np.square(risk_contrib - target_risk))

        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
        bounds = tuple((0.0, 1.0) for _ in range(noa))
        init_guess = np.full(noa, 1.0 / noa)

        res = sco.minimize(objective, init_guess, method='SLSQP', bounds=bounds, constraints=constraints)

        return {ticker: round(weight, 4) for ticker, weight in zip(self.tickers, res.x)}

    def estimate_garch_volatility(self, target_ticker: str) -> float:
        target_rets = self.rets[target_ticker]
        am = arch_model(target_rets * 100, mean='Zero', vol='GARCH')
        res = am.fit(disp='off')

        forecasts = res.forecast(horizon=1)
        next_var = forecasts.variance.iloc[-1, 0]

        return round(float(np.sqrt(next_var * 252) / 100.0), 4)

    def calculate_kelly_fraction(self, target_ticker: str) -> float:
        target_rets = self.rets[target_ticker]
        win_rets = target_rets[target_rets > 0]
        loss_rets = target_rets[target_rets < 0]

        if len(win_rets) == 0 or len(loss_rets) == 0:
            return 0.0

        hit_ratio = len(win_rets) / len(target_rets[target_rets != 0])
        avg_win = win_rets.mean()
        avg_loss = abs(loss_rets.mean())

        kelly = hit_ratio - ((1 - hit_ratio) / (avg_win / avg_loss))
        half_kelly = kelly / 2.0

        return round(float(np.clip(half_kelly, 0.0, 1.0)), 4)

    def calculate_cvar(self, target_ticker: str, delta: float = 0.01) -> float:
        target_rets = self.rets[target_ticker]
        var = target_rets.quantile(delta)
        cvar = target_rets[target_rets <= var].mean()

        return round(float(cvar), 4)

    def generate_parameters(self, output_file: str = 'parameters.json') -> None:
        self.fetch_data()

        print("[Alpha Factory] Executing mathematical models...")
        target_weights = self.get_risk_parity_weights()

        benchmark = self.tickers[0]

        garch_vol = self.estimate_garch_volatility(benchmark)
        kelly_frac = self.calculate_kelly_fraction(benchmark)
        cvar_limit = self.calculate_cvar(benchmark)

        payload = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "universe": self.tickers
            },
            "meta_brain_weights": target_weights,
            "risk_management": {
                "kelly_fraction": kelly_frac,
                "forecasted_volatility": garch_vol,
                "cvar_limit": cvar_limit,
                "toxicity_shield_threshold": -0.8
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(payload, f, indent=4)

        print(f"-> [Success] Engine instructions exported to {output_file}.")

if __name__ == "__main__":
    UNIVERSE = ['SPY', 'TLT', 'GLD']

    factory = AlphaFactory(tickers=UNIVERSE, period='2y')
    factory.generate_parameters('parameters.json')