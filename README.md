# Canadian Stock Advisor

A simple Python script to track and analyze Canadian stocks (TSX) periodically.

## Features
- Fetches daily data for configured stocks using `yfinance`.
- Calculates Moving Averages (50, 200) and RSI (14).
- Generates BUY/SELL/HOLD recommendations based on simple trend following logic:
    - **BUY**: Price > SMA50 > SMA200 (Uptrend).
    - **SELL**: Price < SMA50 < SMA200 (Downtrend).
    - **RSI adjustments**: Warns if Overbought (>70) or Oversold (<30).
- Persists history and recommendations to `stocks.json`.

## How the Logic Works (ELI5)

Imagine you own a lemonade stand. This script acts like a robot advisor that tells you when to buy more lemons (stock) or sell them.

### 1. The Trend Lines (SMAs)
The robot watches two averages to see the "weather":
- **Slow Line (SMA 200)**: The long-term trend (average price over last 200 days).
- **Fast Line (SMA 50)**: The short-term trend (average price over last 50 days).

### 2. When to BUY 🟢
The robot says **BUY** when the price is going UP and looks strong.
- **Rule**: Price > Fast Line > Slow Line.
- **Meaning**: *"Everyone is excited about lemonade right now (Price is high), and the excitement is growing compared to last year. Join the party!"*

### 3. When to SELL 🔴
The robot says **SELL** when the price is crashing.
- **Rule**: Price < Fast Line < Slow Line.
- **Meaning**: *"Nobody wants lemonade anymore, and it's worse than it has been in a long time. Run away!"*

### 4. The Speed Limit (RSI) ⚠️
Sometimes the robot calculates a "Buy" or "Sell" but changes its mind to **HOLD** because of the **RSI** (speedometer).
- **Overbought (>70)**: The price went up TOO fast, like a car speeding. It might crash soon. (HOLD instead of BUY).
- **Oversold (<30)**: The price went down TOO fast. It might bounce back a bit. (HOLD instead of SELL).

## Best Time to Run

Since this script relies on **Daily Closing Prices**, the best time to run it is:

**Daily after 4:00 PM EST (Market Close)**

- **Why?** The mathematical lines (SMA 50/200) settle at the end of the day. Running it in the evening gives you the final signal for the next morning.
- **Action**: Read the report in the evening, place your orders for the market open the next day.

## Setup
1.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage
Run the script manually:
```bash
python main.py
```

## Periodic Scheduling (Windows Task Scheduler)
To have this run automatically (e.g., daily at 6 PM):

1.  Open **Task Scheduler**.
2.  **Create Basic Task** -> Name: "Canadian Stock Advisor".
3.  **Trigger**: Daily.
4.  **Action**: Start a program.
    -   **Program/script**: `python` (or full path to python.exe, e.g., `C:\Python39\python.exe`)
    -   **Add arguments**: `main.py`
    -   **Start in**: `c:\Users\hMirza\Documents\_code\_personal\CanadianStockAdvisor`
5.  Finish.
## Automated Trading (SnapTrade)
This script supports automated trading via [SnapTrade](https://snaptrade.com/).

### Setup
1.  Obtain your `CLIENT_ID`, `CONSUMER_KEY`, and `USER_ID` from SnapTrade.
2.  Create a `.env` file in the project folder (use `.env.example` as a template).
3.  Add your credentials to `.env`:
    ```ini
    SNAPTRADE_CLIENT_ID=your_client_id
    SNAPTRADE_CONSUMER_KEY=your_consumer_key
    SNAPTRADE_USER_ID=your_user_id
    ```

### Usage
To enable trading, add the `--trade` flag:
```bash
python main.py --trade
```
**WARNING**: This will attempt to place real MARKET orders (1 share) for any stock with a BUY or SELL recommendation.
