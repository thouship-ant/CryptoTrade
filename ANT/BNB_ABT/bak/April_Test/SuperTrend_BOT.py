import sys
import time
from datetime import datetime
import ccxt
import schedule
import pandas as pd
import pywhatkit as pw
import config
import warnings
warnings.filterwarnings('ignore')
from logger import logger


def exchange_init():
    bin_exchange = ccxt.binance({
        'apiKey': config.BINANCE_API_KEY,
        'secret': config.BINANCE_API_SECRET
    })
    return bin_exchange


def check_supertrend(exchange, symbol, time_frame='15m', limit=31):
    try:
        pd.set_option('display.max_rows', None)
        pd.options.mode.chained_assignment = None  # default='warn'
        bars = exchange.fetch_ohlcv(symbol, timeframe=time_frame, limit=limit)
        df = pd.DataFrame(bars[:-1], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = supertrend(df)
        return df['in_uptrend'], df['close']
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - trade_logic :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        logger.writeLogs(':: Error: - Main error - ' + error_log, 'error', log_filename)
        return [], []


def tr(df):
    df['previous_close'] = df['close'].shift(1)
    df['high-low'] = abs(df['high'] - df['low'])
    df['high-pc'] = abs(df['high'] - df['previous_close'])
    df['low-pc'] = abs(df['low'] - df['previous_close'])
    tr = df[['high-low', 'high-pc', 'low-pc']].max(axis=1)
    return tr


def atr(df, period):
    df['tr'] = tr(df)
    # logger.writeLogs('calculating average true range', 'info', log_filename)
    atr = df['tr'].rolling(period).mean()
    return atr


def supertrend(df, period=7, multiplier=3):
    # logger.writeLogs('calculating supertrend', 'info', log_filename)
    hl2 = (df['high'] + df['low']) / 2
    df['atr'] = atr(df, period=period)
    df['upperband'] = hl2 + (multiplier * df['atr'])
    df['lowerband'] = hl2 - (multiplier * df['atr'])
    df['in_uptrend'] = True

    for current in range(1, len(df.index)):
        previous = current - 1
        if df['close'][current] > df['upperband'][previous]:
            df['in_uptrend'][current] = True
        elif df['close'][current] < df['lowerband'][previous]:
            df['in_uptrend'][current] = False
        else:
            previous_up_trend = df['in_uptrend'][previous]
            df['in_uptrend'][current] = previous_up_trend

            if df['in_uptrend'][current] and df['lowerband'][current] < df['lowerband'][previous]:
                df['lowerband'][current] = df['lowerband'][previous]

            if not df['in_uptrend'][current] and df['upperband'][current] > df['upperband'][previous]:
                df['upperband'][current] = df['upperband'][previous]
    return df


def check_buy_sell_signal(exchange, symbol, buy_sell_signal, qty, cur_price):
    global in_position
    start_time = str(datetime.strftime(datetime.now(), "%d%m%Y_%H%M%S"))
    curr_hrs = int(datetime.strftime(datetime.now(), "%H"))
    curr_min = int(datetime.strftime(datetime.now(), "%M"))
    whats_msg = ''
    if buy_sell_signal == 'buy':
        # order_buy = exchange.create_market_buy_order(symbol, qty)
        # logger.writeLogs(order_buy, 'info', log_filename)
        in_position = True
        logger.writeLogs('{} is bought successfully at {} == qty : {}'.format(symbol, str(cur_price), str(qty)), 'info', log_filename)
        whats_msg = 'Dummy - Bought {} at {} == qty : {}'.format(symbol, str(cur_price), str(qty))
        try:
            pw.sendwhatmsg('+919600249294', whats_msg, curr_hrs, (curr_min + 2), 20, True, 5)
            time.sleep(145)
        except:
            pass
    else:
        # order_sell = exchange.create_market_buy_order(symbol, qty)
        # logger.writeLogs(order_sell, 'info', log_filename)
        in_position = False
        logger.writeLogs('{} is sold successfully at {} == qty : {}'.format(symbol, str(cur_price), str(qty)), 'info', log_filename)
        whats_msg = 'Dummy - Sold {} at {} == qty : {}'.format(symbol, str(cur_price), str(qty))
        try:
            pw.sendwhatmsg('+919600249294', whats_msg, curr_hrs, (curr_min + 2), 20, True, 5)
            time.sleep(145)
        except:
            pass
    if whats_msg != '':
        with open('supertrend_buy_sell_log.txt', 'a') as f:
            log = str(start_time) + ':: ' + whats_msg + '\n'
            f.write(log)


def main(exchange, symbol):
    global qty, time_interval
    is_uptrend_lst, close_price_lst = check_supertrend(exchange, symbol, '1h', 60)
    if exchange is None:
        logger.writeLogs('exchange error!!!', 'error', log_filename)
        return
    last_row_index = len(is_uptrend_lst.index) - 1
    previous_row_index = last_row_index - 1
    cur_price = close_price_lst[last_row_index]
    logger.writeLogs('{} - current price is {} ==== In position : {} ==== Is Uptrend : {}'
                     .format(symbol, str(cur_price), str(in_position), str(is_uptrend_lst[last_row_index])), 'info', log_filename)
    # usdt_balance = float([d['free'] for d in exchange.fetch_balance()['info']['balances'] if d['asset'] == 'USDT'][0])
    usdt_balance = 500.2805
    if usdt_balance >= 100 or in_position:
        logger.writeLogs('Current USDT balance is {}'.format(str(usdt_balance)), 'info', log_filename)
        buy_amount = usdt_balance / 2
        if not is_uptrend_lst[previous_row_index] and is_uptrend_lst[last_row_index] and not in_position:
            print('changed to uptrend -- Buy signal')
            qty = int(buy_amount / cur_price)
            check_buy_sell_signal(exchange, symbol, 'buy', qty, cur_price)
        elif is_uptrend_lst[previous_row_index] and not is_uptrend_lst[last_row_index] and in_position:
            print('changed to downtrend -- Sell signal')
            check_buy_sell_signal(exchange, symbol, 'sell', qty, cur_price)
            time_interval = 10
    else:
        if usdt_balance < 100:
            logger.writeLogs('Current USDT balanace is less than 100.....', 'info', log_filename)


if __name__ == "__main__":
    in_position = False
    time_interval = 250
    start_time = str(datetime.strftime(datetime.now(), "%d%m%Y_%H%M%S"))
    log_filename = "SuperTrend_BOT_{}.log".format(start_time)
    # print(check_supertrend('ALPACAUSDT', '1h', 31))
    exchange = exchange_init()
    symbols = ['ACA', 'AGLD', 'BETA', 'FTM', 'API3', 'CELO', 'CHZ', 'DAR', 'DREP', 'GALA', 'INJ', 'LOKA', 'MANA',
               'MBOX', 'PEOPLE', 'POND', 'SLP', 'STMX', 'STORJ', 'TLM', 'TVK', 'UTK', 'VOXEL', 'CFX']
    while True:
        for symbol in symbols:
            symbol += 'USDT'
            main(exchange, symbol)
            schedule.every(15).minutes.do(main(exchange, symbol))

            while in_position:
                schedule.run_pending()
                time.sleep(2)
        time.sleep(time_interval)
