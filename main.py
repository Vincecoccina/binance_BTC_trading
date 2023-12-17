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

# A implémenter
# ------------------
# Création class => organisation du code


def get_recent(symbol, start):
    
    data = pd.DataFrame(client.get_historical_klines(symbol=symbol, interval="1h", start_str=start))
    data = data.iloc[:,:6]
    data.columns = ["Time", "Open", "High", "Low", "Close", "Volume"]
    data.set_index("Time", inplace=True)
    data.index = pd.to_datetime(data.index, unit="ms")
    data = data.astype(float)
    return data

def get_real_time_data(symbol, interval):
    twm = ThreadedWebsocketManager()
    twm.start()
    twm.start_kline_socket(callback = stream_candles, symbol = symbol, interval = interval )

def stream_candles(data, msg):
        event_time = pd.to_datetime(msg["E"], unit = "ms")
        start_time = pd.to_datetime(msg["k"]["t"], unit = "ms")
        first   = float(msg["k"]["o"])
        high    = float(msg["k"]["h"])
        low     = float(msg["k"]["l"])
        close   = float(msg["k"]["c"])
        volume  = float(msg["k"]["v"])
        complete=       msg["k"]["x"]
        print("Time: {} | Price: {}".format(event_time, close))
        new_data = pd.DataFrame({
        "Open": [first],
        "High": [high],
        "Low": [low],
        "Close": [close],
        "Volume": [volume],
        "Complete": [complete]
        }, index=[start_time])

        # Concaténer avec les données existantes
        data = pd.concat([data, new_data])


df = get_recent("BTCUSDT", "2023-01-01")
df["Chg"] = df.Close.pct_change() + 1
df["Chg_12"] = df.Chg.rolling(12).sum()
df["buyprice"] = df.Open.shift(-1)
df.dropna(inplace=True)

def calc_prof(data, change, target_profit, stop_loss):
    in_position = False
    profits = []
    data["Signal"] = 0

    for index, row in data.iterrows():
        if not in_position:
            if row["Chg_12"] > change:
                buyprice = row.buyprice
                in_position = True
                data.at[index, "Signal"] = 1  # Mettre à jour le signal pour cette ligne
        if in_position:
            if row.High >= buyprice * target_profit:
                sellprice = buyprice * target_profit
                profit = (sellprice - buyprice) / buyprice
                profits.append(profit)
                in_position = False
                data.at[index, "Signal"] = -1  # Mettre à jour le signal pour cette ligne
            elif row.Low <= buyprice * stop_loss:
                sellprice = buyprice * stop_loss
                profit = (sellprice - buyprice) / buyprice
                profits.append(profit)
                in_position = False
                data.at[index, "Signal"] = -1  # Mettre à jour le signal pour cette ligne

    return ((pd.Series(profits) + 1).prod() - 1)

def execute_trades(data):
    for index, row in data.iterrows():
        signal = row["Signal"]

        try:
            if signal == 1:
                 print(f"Achat effectué")
            elif signal == -1:
                print(f"Vente effectuée")

        except BinanceAPIException as e:
            print(f"Erreur lors de l'envoi de l'ordre de trade à {index}: {e}")



# profit = calc_prof(0.02, 1.04, 0.96)

arr = np.arange(0.01, 0.16, 0.01)
for ele in arr:
    print(f"for {str(ele)}")
    print(calc_prof(df, 0.02, 1+ele, 1-ele))
data_filtered = df[df["Signal"]!=0]
print(data_filtered)
trades = execute_trades(df)
print(trades)



