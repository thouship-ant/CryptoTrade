# ANT Crypto Robo Trade 2.0

Next.js 16 frontend + FastAPI/MySQL backend for the ANT crypto trading bot (Binance, USDT pairs).
Same architecture as `StockTrade/.../ANT_ROBO_trade_2.0`, with a gold & black theme and the
crypto domain ported from the 1.0 Flask app (`ANT_ROBO_trade`): Binance API keys, USDT wallet,
15/10/5% three-level referral, long/short positions, coin-wise P&L.

## Run it

```bash
# 1. database (MySQL 8) - tables are also created automatically at backend start
mysql < database/schema.sql

# 2. backend
cd backend
python -m venv venv && venv/Scripts/pip install -r requirements.txt   # venv/bin/pip on Linux
cp .env.example .env        # fill in DB_*, SMTP_*, API_ENCRYPTION_KEY
venv/Scripts/uvicorn main:app --port 8000

# 3. frontend
npm install
npm run dev                 # http://localhost:3000  (talks to http://localhost:8000 on localhost)
```

Production: set `NEXT_PUBLIC_API_URL` (and `NEXT_PUBLIC_SUPPORT_EMAIL`) when running `npm run build`.

`API_ENCRYPTION_KEY` is required - Binance API secrets are Fernet-encrypted before being stored
(`ALLOW_PLAINTEXT_SECRETS=1` disables that for local development only). Generate one with
`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.

## Money model (all USDT)

| Balance | Funded by | Spent on / withdrawable |
|---|---|---|
| `activation_balance` | approved deposits, transfers from earnings | bot & power plans; **not** withdrawable |
| `ant_wallet_balance` (earnings) | referral commissions | on-chain withdrawal, or transfer to activation |

Deposits are manual: the user sends USDT (BEP20) to the admin address, submits the tx hash, an admin
verifies it on BscScan and approves (Admin > Deposits). Withdrawals are likewise paid manually
(Admin > Withdrawals). Trading capital never passes through the app - it stays on the user's Binance account.

## Contract with the trading engine (BNB_ABT)

The engine must be pointed at this schema. It reads `ant_user_data` (`api_key`, `api_secret`,
`single_trade_amount`, `max_trade`, `leverage`, `stoploss_percent`, `target_percent`, `trade_long`,
`trade_short`, `is_trading_active`, `energy_power`) and writes:

* `crypto_signal_data` - one row per position: insert on entry (`is_Active=1`), keep `current_price` fresh,
  on exit set `exit_price`, `commission`, `sell_reason`, `is_Active=0`, `last_update_DateTime`.
  `side` is `LONG` or `SHORT`; P&L = (exit - entry) x qty x (+1 long / -1 short) - commission.
* `ant_user_wallet.binance_exchange_usdt` / `available_funds` - Binance balance, refreshed each cycle.
* `daily_profit_report` - optional; the backend backfills missing days hourly.
* `crypto_symbols_data` - optional market table for the Top Movers card (falls back to Binance public tickers).

`api_secret` values start with `enc:`; decrypt with `Fernet(API_ENCRYPTION_KEY).decrypt(value[4:].encode())`.
Stop new entries when `is_trading_active = 0` or `energy_power < 500`, but keep managing open positions.

## Differences from the stock app

Removed: Indian brokers (Zerodha/Upstox/Dhan/AliceBlue/5paisa) + OAuth + IP pool, trading holidays,
Cashfree/UPI/bank accounts (replaced by USDT), copy trading, manual F&O signals, Super Admin process
control, APK distribution, Telegram promo. Added: Binance key verification (rejects withdraw-enabled keys),
USDT deposit/withdraw flow, encrypted secrets, public Binance market data (candles, movers).

## Known gaps

* Like the stock app, API endpoints identify the caller by the `user_id` in the URL - there are no session
  tokens, so anyone who learns a user id can read/act as them. Add token auth before exposing this publicly.
* `terms/` and `privacy/` are templates - have them reviewed for your jurisdiction.
* Plan prices/seed rows live in `database/schema.sql`.
