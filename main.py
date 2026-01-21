import yfinance as yf
import pandas as pd
import numpy as np
import argparse
from snaptrade_client import SnapTrade
from pprint import pprint
from dotenv import load_dotenv
from colorama import init, Fore, Style

import json

import os
from datetime import datetime

# Load environment variables from .env file (if present)
load_dotenv()


# Configuration
STOCK_FILE = 'stocks.json'
DEFAULT_STOCKS = ['TD.TO', 'CNQ.TO', 'CAR.UN', 'BMO.TO', 'REI-UN.TO', 'SRU-UN.TO', 'EIF.TO', 'GRT-UN.TO', 'NPI.TO', 'SIA.TO'] # Major Canadian stocks + Monthly Payers

def get_snaptrade_client():
    client_id = os.getenv("SNAPTRADE_CLIENT_ID")
    consumer_key = os.getenv("SNAPTRADE_CONSUMER_KEY")
    user_id = os.getenv("SNAPTRADE_USER_ID")
    
    if not all([client_id, consumer_key, user_id]):
        print("Error: SNAPTRADE_CLIENT_ID, SNAPTRADE_CONSUMER_KEY, and SNAPTRADE_USER_ID must be set in environment variables.")
        return None, None
        
    try:
        client = SnapTrade(consumer_key=consumer_key, client_id=client_id)
        return client, user_id
    except Exception as e:
        print(f"Failed to initialize SnapTrade client: {e}")
        return None, None

def execute_trade(client, user_id, ticker, action):
    try:
        # 1. Get User Account (Using the first one for simplicity or look for a specific one)
        accounts = client.account_information.list_user_accounts(user_id=user_id)
        if not accounts:
            print("No accounts found for user.")
            return

        account_id = accounts[0]['id'] # Use first account
        
        # 2. Place Order (Market Order)
        # Note: SnapTrade uses 'UniversalSymbolId' preferably, but Ticker support varies by brokerage-connector.
        # Often we need to search for the symbol first to get the ID.
        
        symbols = client.reference_data.get_symbols(query=ticker) 
        # Ideally filter for TSX/Canadian exchange if possible, but taking first exact match might work
        # For simplicity in this demo, we assume the first match is correct or pass the string if supported by the specific broker connector.
        
        # NOTE: Real SnapTrade flow often requires getting a Universal Symbol Object.
        target_symbol = None
        if symbols:
            # Simple heuristic: find exact ticker match (case insensitive)
            for s in symbols:
                if s['symbol'] == ticker or s['symbol'] == ticker.replace('.TO', ''): # .TO handling varies
                     target_symbol = s
                     break
            if not target_symbol:
                 target_symbol = symbols[0] # Fallback
        
        if not target_symbol:
             print(f"Could not resolve symbol {ticker} on SnapTrade.")
             return

        # Prepare Order
        # Action needs to be 'BUY' or 'SELL'
        # OrderType 'Market'
        # TimeInForce 'Day'
        
        print(f"Placing {action} order for 1 share of {ticker}...")
        
        # This is the standard v1 structure, might vary by SDK version slightly
        # Check SDK method signature if possible. Assuming standard generated SDK based on docs.
        
        order_response = client.trading.place_order(
            user_id=user_id,
            account_id=account_id,
            body={
                "action": action,
                "order_type": "Market",
                "price": None, # Market order
                "stop": None,
                "time_in_force": "Day",
                "units": 1,
                "universal_symbol_id": target_symbol['id'],
                "notional_value": None
            }
        )
        
        pprint(order_response)

    except Exception as e:
        print(f"Error executing trade for {ticker}: {e}")

def load_data():

    if not os.path.exists(STOCK_FILE):
        return {'stocks': DEFAULT_STOCKS, 'history': []}
    with open(STOCK_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(STOCK_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_forecast(series, days_ahead=7):
    # Simple linear regression on last 30 days
    if len(series) < 30:
        return None
    
    recent_data = series.tail(30)
    x = np.arange(len(recent_data))
    y = recent_data.values
    
    # polyfit returns [slope, intercept] for deg=1
    slope, intercept = np.polyfit(x, y, 1)
    
    # Predict for t + days_ahead (t is strictly the next index logic, so we project out)
    # The last point is x=29, so we want 29 + days_ahead
    forecast_value = slope * (29 + days_ahead) + intercept
    return forecast_value

def analyze_stock(ticker):
    try:
        stock = yf.Ticker(ticker)
        # Fetch 1 year of data to calculate 200 SMA
        hist = stock.history(period="1y")
        
        if hist.empty:
            print(f"No data found for {ticker}")
            return None

        current_price = hist['Close'].iloc[-1]
        
        # Yesterday's price (if available) - safely get 2nd last
        yesterday_price = hist['Close'].iloc[-2] if len(hist) > 1 else current_price

        # Forecast
        forecast_7d = calculate_forecast(hist['Close'])
        
        # Calculate Indicators
        hist['SMA_50'] = hist['Close'].rolling(window=50).mean()
        hist['SMA_200'] = hist['Close'].rolling(window=200).mean()
        hist['RSI'] = calculate_rsi(hist['Close'])

        sma_50 = hist['SMA_50'].iloc[-1]
        sma_200 = hist['SMA_200'].iloc[-1]
        rsi = hist['RSI'].iloc[-1]

        # Recommendation Logic
        recommendation = "HOLD"
        reason = []

        if current_price > sma_50 and sma_50 > sma_200:
            recommendation = "BUY"
            reason.append("Golden Cross / Bullish Trend (Price > 50 > 200)")
        elif current_price < sma_50 and sma_50 < sma_200:
            recommendation = "SELL"
            reason.append("Death Cross / Bearish Trend (Price < 50 < 200)")

        if rsi < 30:
            if recommendation == "SELL": recommendation = "HOLD" # Oversold, might bounce
            reason.append(f"RSI Oversold ({rsi:.2f})")
        elif rsi > 70:
            if recommendation == "BUY": recommendation = "HOLD" # Overbought, might pull back
            reason.append(f"RSI Overbought ({rsi:.2f})")

        return {
            "ticker": ticker,
            "date": datetime.now().isoformat(),
            "price":  round(current_price, 2),
            "yesterday_price": round(yesterday_price, 2),
            "forecast_7d": round(forecast_7d, 2) if forecast_7d else None,
            "sma_50": round(sma_50, 2) if pd.notna(sma_50) else None,
            "sma_200": round(sma_200, 2) if pd.notna(sma_200) else None,
            "rsi": round(rsi, 2) if pd.notna(rsi) else None,
            "recommendation": recommendation,
            "reason": "; ".join(reason)
        }

    except Exception as e:
        print(f"Error analyzing {ticker}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Canadian Stock Advisor')
    parser.add_argument('--trade', action='store_true', help='Execute trades using SnapTrade based on recommendations')
    args = parser.parse_args()
    
    # Initialize colorama
    init()

    print(f"Running Canadian Stock Advisor at {datetime.now()}")
    
    trade_client = None
    trade_user_id = None
    
    if args.trade:
        print("Trading Mode ENABLED. Attempting to connect to SnapTrade...")
        trade_client, trade_user_id = get_snaptrade_client()
        if not trade_client:
            print("Trading initialization failed. Proceeding with analysis only.")

    data = load_data()
    stocks = data.get('stocks', [])
    history = data.get('history', [])

    new_results = []
    print(f"Analyzing {len(stocks)} stocks...")
    
    for ticker in stocks:
        # print(f"Processing {ticker}...") # Reduced noise
        result = analyze_stock(ticker)
        if result:
            new_results.append(result)
            
            # Execute Trade if enabled and Client valid
            if args.trade and trade_client and result['recommendation'] in ['BUY', 'SELL']:
                execute_trade(trade_client, trade_user_id, ticker, result['recommendation'])


        print("\n" + "="*120)
        # Header with fixed widths
        # Ticker(8) | Yesterday(10) | Price(10) | Forecast(14) | Action(8) | RSI(8) | Reason
        header = f"{'Ticker':<8} {'Yesterday':>10} {'Price':>10} {'Forecast (14d)':>14} {'Action':^8} {'RSI':>8}   {'Reason'}"
        print(f"Analysis Results - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("="*120)
        print(header)
        print("-" * 120)

        for res in new_results:
            ticker = res['ticker']
            y_price = f"{res['yesterday_price']:.2f}" if res.get('yesterday_price') else "N/A"
            price = f"{res['price']:.2f}"
            
            fcast = res.get('forecast_7d')
            fcast_str = f"{fcast:.2f}" if fcast else "N/A"
            
            # Action formatting with manual color handling
            action = res['recommendation']
            color = Fore.WHITE
            if action == 'BUY': color = Fore.GREEN
            elif action == 'SELL': color = Fore.RED
            elif action == 'HOLD': color = Fore.BLUE
            
            # Center action in 8 chars
            # We pad the bare string, then wrap in color
            # e.g. "  BUY   "
            padded_action = f"{action:^8}"
            colored_action = f"{color}{padded_action}{Style.RESET_ALL}"
            
            rsi_val = res.get('rsi')
            rsi_str = f"{rsi_val:.2f}" if rsi_val else "N/A"
            
            reason = res.get('reason', '')

            print(f"{ticker:<8} {y_price:>10} {price:>10} {fcast_str:>14} {colored_action} {rsi_str:>8}   {reason}")

        print("="*120 + "\n")
    else:
        print("No results generated.")

    # Append new batch of results to history
    history.extend(new_results)
    
    # Keep history manageable? (Optional: maybe limit to last 1000 entries)
    if len(history) > 5000:
        history = history[-5000:]

    data['history'] = history
    save_data(data)
    print("Analysis complete. Data saved.")

if __name__ == "__main__":
    main()
