import pandas as pd
import requests
import numpy as np
import talib
from binance.client import Client
import ccxt
import threading
from utils import config, db_util
from random import randint
from datetime import datetime #, timedelta
from utils.logger import logger
import time, sys, os, gc
from pytz import timezone
from utils import supRes_level as srl
import warnings
warnings.filterwarnings('ignore')
pd.set_option('display.max_rows', None)


global symbol, exclude_symbols, qty, in_position
TIME_PERIOD = "15m"


def exchange_init():
    bin_exchange = ccxt.binance()
    return bin_exchange


def get_data(symbol):
    starttime = '1 day ago UTC'
    bars = client.get_historical_klines(symbol.replace('1000', ''), TIME_PERIOD, starttime)
    for line in bars:
        del line[5:]
    df = pd.DataFrame(bars, columns=['date', 'open', 'high', 'low', 'close'])
    return df


def get_symbol(lst_symbols, exclude_symbols):
    try:
        print('getting symbols...')
        query_symbol = ''
        lstsymbol = client.get_symbol_ticker()
        for ls in lstsymbol:
            if ls['symbol'].find("USDT") > 1 and ls['symbol'].find("UPUSDT") == -1 \
                    and ls['symbol'].find("DOWNUSDT") == -1 and 0.9 > float(ls['price']) > 0:
                if not (ls['symbol'] in exclude_symbols):
                    info = client.get_symbol_info(ls['symbol'])
                    if info['quoteAsset'] == "USDT" and info['status'] == 'TRADING' and info['isSpotTradingAllowed']:
                        connection = db_util.connect_database()
                        if connection.is_connected():
                            sel_query_symbol = "SELECT count(symbol_name) from `ant_cryptotradingbot`.`crypto_symbols_ema_data` where `symbol_name` = '{}' and `time_period` = '{}'" \
                                .format(info['symbol'], TIME_PERIOD)
                            select_result = db_util.queryExecution(connection, sel_query_symbol, 'select')
                            symbol_count = int(select_result[0][0])
                            if symbol_count == 0:
                                query_symbol = """INSERT `ant_cryptotradingbot`.`crypto_symbols_ema_data` (symbol_name, time_period) VALUES ('{}', '{}');""" \
                                    .format(info['symbol'], TIME_PERIOD)
                                is_insert = db_util.queryExecution(connection, query_symbol, 'insert')
                                if is_insert:
                                    lst_symbols.append(ls['symbol'])
                                print('New Symbol {} ::: DBInsert ::: {}'.format(info['symbol'], is_insert))
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - get_symbol :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print(symbol + ' - ' + error_log)
    finally:
        gc.collect()
        return lst_symbols


def main():
    try:
        itr = 0
        while True:
            itr += 1
            dt_today = datetime.today()  # Local time
            dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
            current_date = str(datetime.strftime(dt_India, "%d%m%Y"))
            if start_date != current_date:
                sys.exit()
            symbols = []
            exclude_symbols = []
            connection = db_util.connect_database()
            if connection.is_connected():
                query = """SELECT symbol_name from `ant_cryptotradingbot`.`crypto_symbols_ema_data` where time_period = '{}' order by `symbol_id` asc"""\
                    .format(TIME_PERIOD)
                get_symbol_list = db_util.queryExecution(connection, query, 'select')
                if len(get_symbol_list) > 0:
                    for exclude_symbol in get_symbol_list:
                        if not (exclude_symbol[0] in exclude_symbols):
                            symbols.append(exclude_symbol[0])
                            exclude_symbols.append(exclude_symbol[0])
                lst_symbols = get_symbol(symbols, exclude_symbols)  # get dynamic symbols from binance exchange

                if len(lst_symbols) > 0:
                    for idx, symbol in enumerate(lst_symbols):
                        if start_ema_tool(symbol, itr, idx) == False:
                            exclude_symbols.append(symbol)
                        time.sleep(2)
                    # timesleep = 150 - ((len(lst_symbols)-180) * 2)
                    timesleep = 2
                    if timesleep > 0:
                        print('Time sleep for : {} seconds.....'.format(str(timesleep)))
                        time.sleep(timesleep)
                    else:
                        print('Time sleep for : 1 seconds.....')
                        time.sleep(1)
                else:
                    print('Time sleep for : 1 min......')
                    time.sleep(60)
            gc.collect()
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - start_ema_tool :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print('Error: - Start EMA tool block error - {}'.format(error_log))


def start_ema_tool(symbol, itr, idx):
    try:
        closing_data = get_data(symbol)
        shortEMA = closing_data['close'].ewm(span=7, adjust=False).mean()
        midEMA = closing_data['close'].ewm(span=25, adjust=False).mean()
        longEMA = closing_data['close'].ewm(span=99, adjust=False).mean()
        vlongEMA = closing_data['close'].ewm(span=200, adjust=False).mean()
        ema_7 = round(shortEMA[95], 8)
        ema_25 = round(midEMA[95], 8)
        ema_99 = round(longEMA[95], 8)
        ema_200 = round(vlongEMA[95], 8)
        signal_7_25 = None
        signal_7_99 = None
        signal_7_200 = None
        connection = db_util.connect_database()
        if connection.is_connected():
            update_query = """UPDATE `ant_cryptotradingbot`.`crypto_symbols_ema_data` SET `last_ema_7` = `ema_7`, `last_ema_25`=`ema_25`, `last_ema_99`=`ema_99`, `last_ema_200`=`ema_200` WHERE `symbol_name`='{}' and `time_period`='{}';""" \
                .format(symbol, TIME_PERIOD)
            is_update_ta_data = db_util.queryExecution(connection, update_query, 'update')
            if is_update_ta_data:
                symbol_info = exchange.fetch_ticker(symbol)['info']
                cur_ask_price = round(float(symbol_info['askPrice']), 8)
                update_query = """UPDATE `ant_cryptotradingbot`.`crypto_symbols_ema_data` SET `ema_7` = {}, `ema_25`={}, `ema_99`={}, `ema_200`={}, `current_price`={} WHERE `symbol_name`='{}' and `time_period`='{}';""" \
                    .format(ema_7, ema_25, ema_99, ema_200, cur_ask_price, symbol, TIME_PERIOD)
                is_update_ta_data = db_util.queryExecution(connection, update_query, 'update')
                if is_update_ta_data:
                    sel_query_symbol = """SELECT CASE WHEN ema_7 > ema_25 and last_ema_7 <= last_ema_25 and last_ema_7 > current_price THEN 'BUY' WHEN ema_7 < ema_25 and last_ema_7 >= last_ema_25 and last_ema_7 < current_price THEN 'SELL' ELSE 'None' END as `signal_7_25`, CASE WHEN ema_25 > ema_99 and ema_7 > ema_25 and last_ema_7 <= last_ema_25 and last_ema_7 > current_price THEN 'BUY' WHEN ema_7 < ema_99 and ema_99 < ema_25 and ema_7 < ema_25 and last_ema_7 >= last_ema_99 and last_ema_7 < current_price THEN 'SELL' ELSE 'None' END as `signal_7_99`, CASE WHEN ((ema_99 < ema_200 and ema_25 > ema_99 and ema_7 > ema_200 and last_ema_7 <= last_ema_200) or (ema_7 > ema_99 and ema_25 > ema_7 and ema_7 > ema_200 and last_ema_7 <= last_ema_200)) and last_ema_7 > current_price THEN 'BUY' WHEN ema_99 > ema_200 and ema_25 > ema_99 and ema_7 < ema_200 and last_ema_7 >= last_ema_200 and last_ema_7 > current_price THEN 'SELL' ELSE 'None' END as `signal_7_200` FROM `ant_cryptotradingbot`.`crypto_symbols_ema_data` where symbol_name = '{}' and time_period = '{}'""" \
                        .format(symbol, TIME_PERIOD)
                    select_result = db_util.queryExecution(connection, sel_query_symbol, 'select')
                    signal_7_25 = select_result[0][0]
                    signal_7_99 = select_result[0][1]
                    signal_7_200 = select_result[0][2]
                    update_query = """UPDATE `ant_cryptotradingbot`.`crypto_symbols_ema_data` SET `signal_7_25`='{}', `signal_7_99`='{}', `signal_7_200`='{}' WHERE `symbol_name`='{}' and `time_period`='{}';""" \
                        .format(str(signal_7_25), str(signal_7_99), str(signal_7_200),
                                symbol, TIME_PERIOD)
                    is_update_ta_data = db_util.queryExecution(connection, update_query, 'update')
                    if is_update_ta_data:
                        print(itr , " - ", idx, " - Data updated for SYMBOL : ", symbol, " --- EMA 7 :", ema_7, ", EMA 25 :", ema_25, ", EMA 99 :", ema_99,
                          ", EMA 200 :", ema_200)
                        print(itr , " - ", idx, " - Signal for SYMBOL : ", symbol, " --- signal_7_25 :", signal_7_25, ", signal_7_99 :", signal_7_99, ", signal_7_200 :",
                              signal_7_200)
            timesleep = 1
#            print('Time sleep for : {} seconds.....'.format(str(timesleep)))
            time.sleep(timesleep)
        return True
    except Exception as ex:
        error_log = "Symbol :: " + symbol + " --- " + str(ex).replace('\'', '\'\'') + " - start_ema_tool :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print('Error: - Start EMA tool block error - {}'.format(error_log))
        return False


def place_order(order_type, symbol):
    if order_type == "buy":
        order = client.create_order(symbol=symbol, side="buy", quantity=QNTY, type="MARKET")
    else:
        order = client.create_order(symbol=symbol, side="sell", quantity=QNTY, type="MARKET")
    print("order placed successfully!!!")
    print(order)
    return


if __name__ == "__main__":
    while True:
        dt_today = datetime.today()  # Local time
        dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
        start_date = str(datetime.strftime(dt_India, "%d%m%Y"))
        log_filename = "DB_EMA_Data_{}.log".format(start_date)
        try:
            exchange = exchange_init()
            api_key = config.BINANCE_API_KEY
            api_secret = config.BINANCE_API_SECRET
            client = Client(api_key, api_secret)
            client = Client(config.BINANCE_API_KEY, config.BINANCE_API_SECRET)
            print('Connection opened... - ')
            s_interval = '15m'  # valid intervals - 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
            main()
        except Exception as ex:
            error_log = str(ex).replace('\'', '\'\'') + " - main :: line ::" \
                        + str(sys.exc_info()[2].tb_lineno)
            print('Error: - Main error - {}'.format(error_log))
            print('Time sleep for : 1 min......')
            time.sleep(60)
            continue

