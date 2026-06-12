# Binance Futures Testnet — Trading Bot 🤖

A clean, production-style Python CLI application that places **MARKET**, **LIMIT**, and **STOP\_MARKET** orders on the [Binance Futures Testnet (USDT-M)](https://testnet.binancefuture.com).

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py          # Package marker
│   ├── client.py            # Binance REST client (signing, HTTP, error handling)
│   ├── orders.py            # Order placement logic + OrderResult dataclass
│   ├── validators.py        # CLI input validation helpers
│   └── logging_config.py   # Rotating file + console logger setup
├── cli.py                   # CLI entry point (argparse)
├── logs/
│   └── trading_bot.log      # Auto-created on first run
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Get Testnet API Credentials

1. Go to [https://testnet.binancefuture.com](https://testnet.binancefuture.com)
2. Log in with your GitHub account
3. Click **API Key** → generate a key pair
4. Copy your **API Key** and **Secret Key** — the secret is shown only once

### 2. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/trading-bot.git
cd trading-bot

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Set Credentials

```bash
# Linux / macOS
export BINANCE_API_KEY="your_api_key_here"
export BINANCE_API_SECRET="your_api_secret_here"

# Windows (PowerShell)
$env:BINANCE_API_KEY="your_api_key_here"
$env:BINANCE_API_SECRET="your_api_secret_here"
```

Alternatively, pass credentials as CLI flags on each command:

```bash
python cli.py place ... --api-key YOUR_KEY --api-secret YOUR_SECRET
```

---

## How to Run

### Place a MARKET order

```bash
# Buy 0.001 BTC at market price
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

# Sell 0.001 BTC at market price
python cli.py place --symbol BTCUSDT --side SELL --type MARKET --quantity 0.001
```

### Place a LIMIT order

```bash
# Sell limit at $95,000
python cli.py place --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 95000

# Buy limit at $60,000 with IOC time-in-force
python cli.py place --symbol BTCUSDT --side BUY --type LIMIT --quantity 0.001 --price 60000 --time-in-force IOC
```

### Place a STOP_MARKET order (bonus)

```bash
# Stop-market sell triggered at $60,000 (acts as a stop-loss)
python cli.py place --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.001 --price 60000
```

### Check Account Balance

```bash
python cli.py account
```

### Get Current Mark Price

```bash
python cli.py price --symbol BTCUSDT
python cli.py price --symbol ETHUSDT
```

### Adjust Log Verbosity

```bash
python cli.py place ... --log-level DEBUG   # shows raw request/response bodies
python cli.py place ... --log-level WARNING # quiet mode
```

---

## Example Output

```
╔══════════════════════════════════════════════════╗
║    Binance Futures Testnet — Trading Bot 🤖       ║
╚══════════════════════════════════════════════════╝

──────────────────────────────────────────────────────
  ORDER REQUEST SUMMARY
──────────────────────────────────────────────────────
  Symbol        : BTCUSDT
  Side          : BUY
  Type          : MARKET
  Quantity      : 0.001
──────────────────────────────────────────────────────

════════════════════════════════════════════════════
  ORDER RESPONSE
════════════════════════════════════════════════════
  Order ID      : 3847291056
  Symbol        : BTCUSDT
  Side          : BUY
  Type          : MARKET
  Status        : FILLED
  Orig Qty      : 0.001
  Executed Qty  : 0.001
  Avg Price     : 67432.10
════════════════════════════════════════════════════

✔  Order placed successfully! (orderId=3847291056)
```

---

## Log File Location

All logs are written to `logs/trading_bot.log` (auto-created, rotates at 5 MB).

```
2026-06-11 13:00:39 | INFO     | trading_bot | Order request | symbol=BTCUSDT | side=BUY | type=MARKET | qty=0.001
2026-06-11 13:00:39 | INFO     | trading_bot | MARKET order placed | orderId=3847291056 | status=FILLED | avgPrice=67432.10
2026-06-11 13:00:39 | INFO     | trading_bot | Order SUCCESS | orderId=3847291056 | status=FILLED
```

Use `--log-level DEBUG` to log raw request and response bodies (useful for debugging).

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Missing required flag (`--price` for LIMIT) | Validation error printed, exits with code 1 |
| Invalid quantity (negative / non-numeric) | Validation error printed, exits with code 1 |
| Binance API error (e.g. insufficient margin) | API error code + message printed, logged |
| Network timeout / connection refused | Network error message printed, logged |
| Invalid API credentials | Binance error -1102 / -2014 printed clearly |

---

## Assumptions

- Only **USDT-M Futures** (linear perpetuals) are supported.
- The bot uses `timeInForce=GTC` for LIMIT orders by default (configurable via `--time-in-force`).
- Quantity precision must match the symbol's `stepSize` — use values that Binance accepts (e.g. `0.001` for BTCUSDT).
- The testnet occasionally resets balances; if you get "insufficient balance" errors, re-check the testnet dashboard.
- `colorama` is an optional dependency; the CLI degrades gracefully to plain text if it is not installed.

---

## Bonus Features Implemented

- **STOP\_MARKET order type** — third order type beyond MARKET and LIMIT
- **Coloured terminal output** via `colorama` — green for success, red for errors, yellow for warnings
- **Mark price lookup** (`python cli.py price --symbol BTCUSDT`)
- **Account balance summary** (`python cli.py account`)
- **Rotating log file** — automatically rolls over at 5 MB, keeps 3 backups

---

## Dependencies

```
requests>=2.31.0   # HTTP client for Binance REST API
colorama>=0.4.6    # Cross-platform coloured terminal output
```

No `python-binance` library is used — all API calls are raw REST requests with HMAC-SHA256 signing, giving full transparency and control.
