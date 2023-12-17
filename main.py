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


# Réorganisation du code

class Trader():
    def __init__(self, symbol, bar_length, stop_loss, target_profit, change):
        self.symbol = symbol
        self.bar_length = bar_length
        self.available_intervals = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"]
        self.position = 0
        self.stop_loss = stop_loss
        self.target_profit = target_profit
        self.change = change
    
    def start_trading(self):

        self.twm = ThreadedWebsocketManager()
        self.twm.start()

        if self.bar_length in self.available_intervals:
            self.get_recent(symbol = self.symbol, interval = self.bar_length)
            self.twm.start_kline_socket(callback = self.stream_candles,
                                        symbol = self.symbol, interval = self.bar_length)
    
    def get_recent(self, symbol, interval):
        
        start = "2023-01-01"

        df = pd.DataFrame(client.get_historical_klines(symbol=symbol, interval=interval, start_str=start))
        df = df.iloc[:,:6]
        df.columns = ["Time", "Open", "High", "Low", "Close", "Volume"]
        df.set_index("Time", inplace=True)
        df.index = pd.to_datetime(df.index, unit="ms")
        df = df.astype(float)
        self.data = df
        self.calculate_indicators()
    
    def calculate_indicators(self):
        self.data["Chg"] = self.data.Close.pct_change() + 1
        self.data["Chg_12"] = self.data.Chg.rolling(12).sum()
        self.data["buyprice"] = self.data.Open.shift(-1)
        self.data.dropna(inplace=True)
        self.calc_prof()
    
    def calc_prof(self):
        in_position = False
        profits = []
        self.data["Signal"] = 0

        for index, row in self.data.iterrows():
            if not in_position:
                if row["Chg_12"] > self.change:
                    buyprice = row.buyprice
                    in_position = True
                    self.data.at[index, "Signal"] = 1  # Mettre à jour le signal pour cette ligne
            if in_position:
                if row.High >= buyprice * self.target_profit:
                    sellprice = buyprice * self.target_profit
                    profit = (sellprice - buyprice) / buyprice
                    profits.append(profit)
                    in_position = False
                    self.data.at[index, "Signal"] = -1  # Mettre à jour le signal pour cette ligne
                elif row.Low <= buyprice * self.stop_loss:
                    sellprice = buyprice * self.stop_loss
                    profit = (sellprice - buyprice) / buyprice
                    profits.append(profit)
                    in_position = False
                    self.data.at[index, "Signal"] = -1  # Mettre à jour le signal pour cette ligne

        return ((pd.Series(profits) + 1).prod() - 1)
    
    def stream_candles(self, msg):
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
        }, index=[start_time])

        # Concaténer avec les données existantes
        self.data = pd.concat([self.data, new_data])
        # Recalcule des indicateurs
        self.calculate_indicators()
    
    def execute_trades(self):
        for index, row in self.data.iterrows():
            signal = row["Signal"]

            try:
                if signal == 1:
                    print(f"Achat effectué")
                elif signal == -1:
                    print(f"Vente effectuée")

            except BinanceAPIException as e:
                print(f"Erreur lors de l'envoi de l'ordre de trade à {index}: {e}")
    

bar_length = "1h"
symbol="BTCUSDT"
change = 0.02
target_profit = 1.01
stop_loss = 0.99 
trader = Trader(symbol=symbol, bar_length=bar_length, stop_loss=stop_loss, target_profit=target_profit, change=change)
trader.start_trading()

run_time = 60  # Durée d'exécution en secondes
time.sleep(run_time)

# Arrêt du WebSocket
trader.twm.stop()

filtered_data = trader.data[trader.data["Signal"]!=0]
print(filtered_data)

