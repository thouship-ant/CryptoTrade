-- ANT Robo Trade (Crypto) 2.0 - MySQL schema.
-- Run once against an empty database (default name: ant_cryptotradingbot_v2).
-- backend/main.py also runs the idempotent CREATE TABLE IF NOT EXISTS statements at
-- startup (ensure_schema), so this file is mainly for DBAs and for the trading engine
-- (BNB_ABT) to know exactly which tables/columns it must read and write.

CREATE DATABASE IF NOT EXISTS ant_cryptotradingbot_v2 CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE ant_cryptotradingbot_v2;

CREATE USER 'ahyan'@'106.192.70.43' IDENTIFIED BY 'Ahyan@1811';
GRANT ALL PRIVILEGES ON ant_cryptotradingbot_v2.* TO 'ahyan'@'187.127.154.130';
GRANT SELECT, INSERT, UPDATE, DELETE ON ant_cryptotradingbot_v2.* TO 'ahyan'@'187.127.154.130';
FLUSH PRIVILEGES;
GRANT ALL PRIVILEGES ON `ant_cryptotradingbot_v2`.* TO 'ahyan'@'106.192.70.43';
GRANT SELECT, INSERT, UPDATE, DELETE ON ant_cryptotradingbot_v2.* TO 'ahyan'@'106.192.70.43';
-- Apply the changes
FLUSH PRIVILEGES;

-- Users. password is a bcrypt hash. user_id is a UUID string.
CREATE TABLE IF NOT EXISTS ant_user_data (
  user_id VARCHAR(36) PRIMARY KEY,
  full_name VARCHAR(100) NOT NULL,
  username VARCHAR(50) NOT NULL UNIQUE,
  password VARCHAR(100) NOT NULL,
  mobile_number VARCHAR(20) NULL,
  email_id VARCHAR(100) NOT NULL UNIQUE,
  role VARCHAR(20) NOT NULL DEFAULT 'User',            -- User | Admin | Demo
  exchange_name VARCHAR(30) NOT NULL DEFAULT 'Binance',
  api_key VARCHAR(128) NULL,                            -- Binance API key (trade-only, no withdrawal permission)
  api_secret VARCHAR(512) NULL,                         -- Fernet-encrypted ("enc:" prefix), see API_ENCRYPTION_KEY
  usdt_address VARCHAR(100) NULL,                       -- user's own BEP20 withdrawal address
  referal_code VARCHAR(20) NOT NULL,
  referal_by VARCHAR(36) NOT NULL,
  current_plan VARCHAR(50) NOT NULL DEFAULT '',
  energy_power DECIMAL(15,2) NOT NULL DEFAULT 0,
  total_investment_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
  single_trade_amount DECIMAL(15,2) NOT NULL DEFAULT 50,
  max_trade INT NOT NULL DEFAULT 5,                     -- max simultaneous open positions
  leverage INT NOT NULL DEFAULT 1,
  stoploss_percent DECIMAL(6,2) NOT NULL DEFAULT 5,
  target_percent DECIMAL(6,2) NOT NULL DEFAULT 2,
  trade_long TINYINT(1) NOT NULL DEFAULT 1,
  trade_short TINYINT(1) NOT NULL DEFAULT 0,
  is_trading_active TINYINT(1) NOT NULL DEFAULT 1,
  is_tool_running TINYINT(1) NOT NULL DEFAULT 0,
  is_Active TINYINT(1) NOT NULL DEFAULT 1,
  is_verified TINYINT(1) NOT NULL DEFAULT 1,
  total_profit_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
  last_otp_login_at DATETIME NULL,
  created_date DATETIME NOT NULL,
  updated_date DATETIME NULL,
  INDEX idx_referal_code (referal_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

LOCK TABLES `ant_user_data` WRITE;
/*!40000 ALTER TABLE `ant_user_data` DISABLE KEYS */;
INSERT IGNORE INTO `ant_user_data` VALUES ('053378d6-348b-11f1-845c-bcfce7480294','ANT Admin','Admin','$2b$12$v0Mk6jJtcy1skxqeabialOOY.2YqXt9PRA.vGoc/xzFK/3rTTa3AS','+918807069691','mdthouship1988@gmail.com','Admin','binance','mock','mock','','admin_ant_1','admin_ant_1','5MP',4991566,1000,20,50,20,20,20,1,1,1,0,1,1,0,NULL,'2022-04-02 10:15:00',NULL),('fa8736e9-2281-4cd9-80e1-5f4d4c546630','Mohamed Thouship','thouship','$2b$12$v0Mk6jJtcy1skxqeabialOOY.2YqXt9PRA.vGoc/xzFK/3rTTa3AS','+919600249294','thouship@gmail.com','User','binance','nFkI0vXIipJcEfvBTO6gdaDNpB7QdQozi961siYY3Mnuga5dPpcXZx8UZhfPFO4W','xPVDaPsJ8wH2G732UWYL2CaegmfUpn5XEOhGJY987BxOQEi3J5keEXKSruWC5kLu','','thouship_ant_2','admin_ant_1','1MP',995200,500,5,25,20,20,20,1,1,0,0,1,1,0,NULL,'2022-04-05 15:10:20',NULL); /*nFkI0vXIip$*/ /**/
/*!40000 ALTER TABLE `ant_user_data` ENABLE KEYS */;
UNLOCK TABLES;

-- All wallet figures are USDT.
CREATE TABLE IF NOT EXISTS ant_user_wallet (
  wallet_seq_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  user_id VARCHAR(36) NOT NULL UNIQUE,
  initial_investment DECIMAL(15,2) NOT NULL DEFAULT 0,
  current_investment DECIMAL(15,2) NOT NULL DEFAULT 0,  -- day-to-day compounding baseline for daily_profit_report
  binance_exchange_usdt DECIMAL(15,2) NOT NULL DEFAULT 0, -- Binance futures/spot USDT balance, refreshed by the engine
  available_funds DECIMAL(15,2) NULL,
  binance_spot_usdt DECIMAL(15,2) NULL,                  -- last synced Spot wallet USDT (set by Verify & sync)
  binance_futures_usdt DECIMAL(15,2) NULL,               -- last synced USDT-M Futures wallet USDT
  ant_wallet_balance DECIMAL(15,2) NOT NULL DEFAULT 0,
  activation_balance DECIMAL(15,2) NOT NULL DEFAULT 0,
  total_deposit DECIMAL(15,2) NOT NULL DEFAULT 0,
  total_withdrawal DECIMAL(15,2) NOT NULL DEFAULT 0,
  referal_income DECIMAL(15,2) NOT NULL DEFAULT 0,
  referal_income_transferred DECIMAL(15,2) NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS wallet_transactions (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  user_id VARCHAR(36) NOT NULL,
  transaction_type VARCHAR(30) NOT NULL,   -- deposit | withdrawal | transfer | bot_purchase | points_activation | referal_income
  amount DECIMAL(15,2) NOT NULL,
  status VARCHAR(15) NOT NULL DEFAULT 'pending',   -- pending | completed | failed
  payment_method VARCHAR(30) NOT NULL DEFAULT 'Internal',
  description VARCHAR(255) NULL,
  transaction_id VARCHAR(200) NOT NULL,
  source_user_id VARCHAR(36) NULL,
  txn_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_wt_user (user_id, txn_date),
  INDEX idx_wt_txid (transaction_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS master_bot_plan (
  bot_id INT AUTO_INCREMENT PRIMARY KEY,
  bot_name VARCHAR(60) NOT NULL UNIQUE,
  bot_description VARCHAR(500) NULL,
  bot_price DECIMAL(12,2) NOT NULL,
  discount_price DECIMAL(12,2) NULL,
  max_invest DECIMAL(12,2) NOT NULL DEFAULT 0,
  current_status VARCHAR(30) NULL           -- NULL/'ACTIVE' or 'COMING SOON'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS master_power_plan (
  power_id INT AUTO_INCREMENT PRIMARY KEY,
  power_name VARCHAR(60) NOT NULL UNIQUE,
  power_value DECIMAL(15,2) NOT NULL,       -- energy points granted
  power_price DECIMAL(12,2) NOT NULL,       -- USDT
  discount_price DECIMAL(12,2) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ant_user_bot_purchase (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  user_id VARCHAR(36) NOT NULL,
  bot_name VARCHAR(60) NOT NULL,
  purchased_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ant_user_power_purchase (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  user_id VARCHAR(36) NOT NULL,
  energy_power DECIMAL(15,2) NOT NULL,
  purchased_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- One row per position (open: is_Active=1, exit_price NULL; closed: is_Active=0).
-- This is the table the trading engine writes. For SHORT positions entry_price is the
-- sell-to-open price and exit_price the buy-to-close price; P&L = (exit-entry)*qty*dir
-- where dir = +1 for LONG, -1 for SHORT.
CREATE TABLE IF NOT EXISTS crypto_signal_data (
  signal_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  user_id VARCHAR(36) NOT NULL,
  symbol_name VARCHAR(20) NOT NULL,         -- e.g. BTCUSDT
  side VARCHAR(5) NOT NULL DEFAULT 'LONG',  -- LONG | SHORT
  signal_type VARCHAR(100) NULL,
  quantity DECIMAL(24,8) NOT NULL,
  entry_price DECIMAL(24,8) NOT NULL,
  current_price DECIMAL(24,8) NULL,
  exit_price DECIMAL(24,8) NULL,
  target_price DECIMAL(24,8) NULL,
  stoploss_price DECIMAL(24,8) NULL,
  leverage INT NOT NULL DEFAULT 1,
  commission DECIMAL(18,8) NOT NULL DEFAULT 0,
  buy_reason VARCHAR(255) NULL,
  sell_reason VARCHAR(255) NULL,
  binance_order_id VARCHAR(40) NULL,
  is_Active TINYINT(1) NOT NULL DEFAULT 1,
  created_DateTime DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_update_DateTime DATETIME NULL,
  INDEX idx_csd_user_active (user_id, is_Active),
  INDEX idx_csd_user_created (user_id, created_DateTime),
  INDEX idx_csd_user_updated (user_id, last_update_DateTime)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS daily_profit_report (
  s_no BIGINT AUTO_INCREMENT PRIMARY KEY,
  `date` DATE NOT NULL,
  user_id VARCHAR(36) NOT NULL,
  start_amount DECIMAL(15,4) NOT NULL,
  end_amount DECIMAL(15,4) NULL,
  profit_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
  profit_percent DECIMAL(10,2) NOT NULL DEFAULT 0,
  commission_price DECIMAL(15,2) NOT NULL DEFAULT 0,
  update_date DATETIME NULL,
  UNIQUE KEY uq_dpr_user_date (user_id, `date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Market data, refreshed by the engine (same shape as the 1.0 crypto_symbols_data).
CREATE TABLE IF NOT EXISTS crypto_symbols_name (
  symbol_seq_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  symbol_name VARCHAR(20) NOT NULL UNIQUE,  -- base asset, e.g. BTC
  symbol_full_name VARCHAR(100) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS crypto_symbols_data (
  symbol_name VARCHAR(20) PRIMARY KEY,      -- pair, e.g. BTCUSDT
  current_askPrice DECIMAL(24,8) NULL,
  `24hrs_price_change` DECIMAL(24,8) NULL,
  `24hrs_change` DECIMAL(10,2) NULL,        -- percent
  Volumes DECIMAL(30,4) NULL,
  is_Active TINYINT(1) NOT NULL DEFAULT 1,
  updated_at DATETIME NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Crypto deposits: the user sends USDT (BEP20) to the admin address shown in the wallet,
-- then submits the transaction hash. An admin verifies it on-chain and approves it.
CREATE TABLE IF NOT EXISTS deposit_settings (
  id INT AUTO_INCREMENT PRIMARY KEY,
  usdt_address VARCHAR(100) NOT NULL,
  network VARCHAR(30) NOT NULL DEFAULT 'BEP20 (BSC)',
  qr_image LONGTEXT NULL,
  note VARCHAR(255) NULL,
  is_enabled TINYINT(1) NOT NULL DEFAULT 1,
  uploaded_by VARCHAR(36) NULL,
  uploaded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS deposit_requests (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id VARCHAR(36) NOT NULL,
  transaction_id VARCHAR(200) NOT NULL,
  amount DECIMAL(15,2) NOT NULL,
  tx_hash VARCHAR(100) NOT NULL UNIQUE,
  network VARCHAR(30) NOT NULL DEFAULT 'BEP20 (BSC)',
  status ENUM('pending','approved','rejected') NOT NULL DEFAULT 'pending',
  admin_note VARCHAR(500) NULL,
  requested_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  processed_at DATETIME NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS withdrawal_requests (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id VARCHAR(36) NOT NULL,
  transaction_id VARCHAR(200) NOT NULL,
  amount DECIMAL(15,2) NOT NULL,
  fee DECIMAL(15,2) NOT NULL DEFAULT 0,
  usdt_address VARCHAR(100) NOT NULL,
  network VARCHAR(30) NOT NULL DEFAULT 'BEP20 (BSC)',
  status ENUM('pending','completed','rejected') NOT NULL DEFAULT 'pending',
  tx_hash VARCHAR(100) NULL,
  admin_note VARCHAR(500) NULL,
  requested_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  processed_at DATETIME NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS email_otp_verifications (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id VARCHAR(36) NOT NULL,
  otp_code CHAR(6) NOT NULL,
  purpose VARCHAR(20) NOT NULL DEFAULT 'verify_email',  -- verify_email | password_reset | monthly_login
  expires_at DATETIME NOT NULL,
  attempts INT NOT NULL DEFAULT 0,
  is_used TINYINT(1) NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS scheduled_emails (
  id INT AUTO_INCREMENT PRIMARY KEY,
  admin_user_id VARCHAR(36),
  target_user_id VARCHAR(36),
  to_email VARCHAR(255) NOT NULL,
  subject VARCHAR(255) NOT NULL,
  body TEXT NOT NULL,
  send_at DATETIME NULL,
  status ENUM('pending','sent','failed') NOT NULL DEFAULT 'pending',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  sent_at DATETIME NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Seed plans (USDT). Adjust prices freely; the backend never hardcodes them.
INSERT IGNORE INTO master_bot_plan (bot_name, bot_description, bot_price, discount_price, max_invest, current_status) VALUES
  ('Crypto Spot Bot',    'Automated long-only spot trading on Binance USDT pairs (billed yearly)', 150, 100, 500,  NULL),
  ('Crypto Futures Bot', 'Automated long/short USDT-M futures trading with leverage (billed yearly)', 300, 200, 1500, NULL),
  ('Crypto Grid Bot',    'Grid trading for ranging markets', 200, 150, 1000, 'COMING SOON');

INSERT IGNORE INTO master_power_plan (power_name, power_value, power_price, discount_price) VALUES
  ('2.5K Power', 2500,  25,   25),
  ('5K Power',   5000,  50,   50),
  ('10K Power',  10000, 100,  100),
  ('100K Power', 100000, 1000, 1000);
