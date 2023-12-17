import pandas as pd
import pandas_ta as ta
import numpy as np
import plotly.graph_objects as go
import os
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException
from binance import ThreadedWebsocketManager
from dotenv import load_dotenv
from datetime import datetime, timedelta
import time

# Chargement des variables d'environnement pour la sécurité des clés API
load_dotenv()
api_key = os.getenv("API_KEY_TEST")
secret_key = os.getenv("SECRET_KEY_TEST")

# Initialisation de l'API Binance avec les clés API
client = Client(api_key=api_key, api_secret=secret_key, tld='com', testnet=False)

def get_data(symbol, start):
    
    data = pd.DataFrame(client.get_historical_klines(symbol=symbol, interval="1h", start_str=start))
    data = data.iloc[:,:6]
    data.columns = ["Time", "Open", "High", "Low", "Close", "Volume"]
    data.set_index("Time", inplace=True)
    data.index = pd.to_datetime(data.index, unit="ms")
    data = data.astype(float)
    return data

df = get_data("BTCUSDT", "2023-01-01")
df["Chg"] = df.Close.pct_change() + 1
df["Chg_12"] = df.Chg.rolling(12).sum()
df["buyprice"] = df.Open.shift(-1)
df.dropna(inplace=True)

def calc_prof(change, target_profit, stop_loss):
    in_position = False
    profits = []

    for index,row in df.iterrows():
        if not in_position:
            if row["Chg_12"] > change:
                buyprice = row.buyprice
                in_position = True

        if in_position:
            if row.High >= buyprice * target_profit:
                sellprice = buyprice * target_profit
                profit = (sellprice-buyprice)/buyprice
                profits.append(profit)
                in_position = False
            elif row.Low <= buyprice * stop_loss:
                sellprice = buyprice * stop_loss
                profit = (sellprice-buyprice)/buyprice
                profits.append(profit)
                in_position = False

    return ((pd.Series(profits) + 1).prod() - 1)


# profit = calc_prof(0.02, 1.04, 0.96)
arr = np.arange(0.01, 0.16, 0.01)
for ele in arr:
    print(f"for {str(ele)}")
    print(calc_prof(0.02, 1+ele, 1-ele))



