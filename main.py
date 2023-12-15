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
client = Client(api_key=api_key, api_secret=secret_key, tld='com', testnet=True)