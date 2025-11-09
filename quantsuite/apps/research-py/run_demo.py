import pandas as pd
from factors.momentum import mom_close

df = pd.read_csv("../sample_data/sp500_sample.csv")
m = mom_close(df, lookback=2)
print("momentum(lookback=2):")
print(m.tail(3))