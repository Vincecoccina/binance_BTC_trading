import pandas as pd
import pandas_ta as ta
import numpy as np
import plotly.graph_objects as go
import os
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException
from datetime import datetime, timedelta
from dotenv import load_dotenv
import time

load_dotenv()

class Trader():
    def __init__(self, symbol, bar_length, stop_loss, target_profit, change, units):
        self.symbol = symbol
        self.bar_length = bar_length
        self.available_intervals = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"]
        self.stop_loss = stop_loss
        self.target_profit = target_profit
        self.change = change
        self.units = units
        self.trades = pd.DataFrame(columns=['Date',"Symbol", 'Type', 'OrderID', 'Price', 'Quantity','Total', 'Status'])
        
    
    def start_trading(self):

        if self.bar_length in self.available_intervals:
            self.get_recent(symbol=self.symbol, interval=self.bar_length)
            self.execute_trades()

    def get_recent(self, symbol, interval):
        
        start = "2023-01-01"

        df = pd.DataFrame(client.get_historical_klines(symbol=symbol, interval=interval, start_str=start))
        df["Date"] = pd.to_datetime(df.iloc[:,0], unit = "ms")
        df.columns = ["Open Time", "Open", "High", "Low", "Close", "Volume",
                      "Clos Time", "Quote Asset Volume", "Number of Trades",
                      "Taker Buy Base Asset Volume", "Taker Buy Quote Asset Volume", "Ignore", "Date"]
        df = df[["Date", "Open", "High", "Low", "Close", "Volume"]].copy()
        df.set_index("Date", inplace = True)
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
        buyprice = None
        profits = []
        self.data["Signal"] = 0

        for index, row in self.data.iterrows():
            # Vérifier si on doit acheter
            if not in_position and row["Chg_12"] > self.change:
                buyprice = row.buyprice
                in_position = True
                self.data.at[index, "Signal"] = 1
            # Vérifier si on doit vendre
            elif in_position:
                if row.High >= buyprice * self.target_profit:
                    sellprice = buyprice * self.target_profit
                    profit = (sellprice - buyprice) / buyprice
                    profits.append(profit)
                    in_position = False
                    self.data.at[index, "Signal"] = -1
                elif row.Low <= buyprice * self.stop_loss:
                    sellprice = buyprice * self.stop_loss
                    profit = (sellprice - buyprice) / buyprice
                    profits.append(profit)
                    in_position = False
                    self.data.at[index, "Signal"] = -1

        return ((pd.Series(profits) + 1).prod() - 1)

    
    
    def execute_trades(self):
        last_row = self.data.iloc[-1]
        index = last_row.name  # Cela donne l'index de la dernière ligne, c'est-à-dire la date/heure
        signal = last_row["Signal"]

        try:
            if signal == 1:
                order = client.create_order(symbol=self.symbol, side="BUY", type="MARKET", quantity=self.units)
                print(f"Achat effectué : ", order)
                self.record_trade(order, 'BUY')
            elif signal == -1:
                order = client.create_order(symbol=self.symbol, side="SELL", type="MARKET", quantity=self.units)
                print(f"Vente effectuée : ", order)
                self.record_trade(order, 'SELL')
            else:
                print(f"neutre")
        except Exception as e:
                print(f"Erreur: {e}")


    def record_trade(self, order, type):
        price = float(order['fills'][0]['price'])
        quantity = float(order['fills'][0]['qty'])
        time = order['transactTime']
        new_trade = pd.DataFrame({
            "Date": time,
            'Type': type,
            "Symbol": symbol,
            'OrderID': order['orderId'],
            'Price': price,
            'Quantity': quantity,
            'Total': price * quantity,
            'Status': order['status']
        }, index=[order["orderId"]])
        new_trade["Date"] = pd.to_datetime(new_trade.iloc[:,0], unit = "ms")
        self.trades = pd.concat([self.trades, new_trade])


if __name__ == "__main__": # Lance le script seulement si main.py est appelé

    # Initialisation de l'API Binance avec les clés API
    api_key = os.getenv("API_KEY_TEST")
    secret_key = os.getenv("SECRET_KEY_TEST")

    # Création du Client Binance
    client = Client(api_key=api_key, api_secret=secret_key, tld='com', testnet=True)
    account_info = client.get_account()
    btc_price = float(client.get_symbol_ticker(symbol="BTCUSDT")['price'])
    balances = account_info['balances']
    for balance in balances:
        if balance['asset'] == 'USDT':
            usdt_balance = float(balance['free'])
            print("Solde en USDT : ", usdt_balance)
    
    # Variables de trading
    bar_length = "1h"
    symbol = "BTCUSDT"
    capital = usdt_balance
    price = btc_price
    pourcentage_risque_par_trade = 0.01
    montant_risque = capital * pourcentage_risque_par_trade
    precision = 5
    unit = montant_risque / btc_price
    units = round(unit, precision)
    change = 0.02
    target_profit = 1.05
    stop_loss = 0.97

    # Instance de la class Trader
    trader = Trader(symbol=symbol, bar_length=bar_length, stop_loss=stop_loss, target_profit=target_profit, change=change, units=units)

 
    try:
        while True:
            current_time = datetime.utcnow()
            next_hour = current_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            sleep_time = (next_hour - current_time).total_seconds()
            time.sleep(sleep_time)
            trader.start_trading()
    except KeyboardInterrupt:
        print("Arrêt du script...")
        profit = trader.calc_prof()
        print("Profit calculé :", profit)
        filtered_data = trader.data[trader.data["Signal"]!=0]
        print(filtered_data[:])
        print(trader.trades)
   

