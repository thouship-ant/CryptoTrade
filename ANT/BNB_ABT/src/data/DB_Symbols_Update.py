import pandas as pd
import numpy as np
import talib
from talib import MA_Type
from datetime import datetime
from pytz import timezone
from binance.client import Client
import time, sys, gc, os
import ccxt
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from src.utils import config, db_util
from src.utils.logger import logger
import warnings
warnings.filterwarnings('ignore')
pd.set_option('display.max_rows', None)


global symbol, exclude_symbols, qty, in_position


def exchange_init():
    bin_exchange = ccxt.binance()
    return bin_exchange


def get_symbol():
    try:
        print('getting symbols...')
        connection = db_util.connect_database()
        if connection.is_connected():
            lstsymbol = client.get_symbol_ticker()
            for ls in lstsymbol:
                if ls['symbol'].find("USDT") > 1 and ls['symbol'].find("UPUSDT") == -1 \
                         and ls['symbol'].find("DOWNUSDT") == -1 and (0.9 > float(ls['price']) > 0 or 80 > float(ls['price']) > 1.1):
                    info = client.get_symbol_info(ls['symbol'])
                    if info is not None:
                        if info['quoteAsset'] == "USDT" and info['status'] == 'TRADING' and (info['isSpotTradingAllowed'] or info['isMarginTradingAllowed']):
                            sel_query_symbol = "SELECT count(symbol_name) from `ant_cryptotradingbot`.`crypto_symbols_data` where `symbol_name` = '{}'"\
                                .format(info['symbol'])
                            select_result = db_util.queryExecution(connection, sel_query_symbol, 'select')
                            symbol_count = int(select_result[0][0])
                            if symbol_count == 0:
                                query_symbol = """INSERT INTO `ant_cryptotradingbot`.`crypto_symbols_data` (`symbol_name`) VALUES ('{}');"""\
                                    .format(info['symbol'])
                                is_insert = db_util.queryExecution(connection, query_symbol, 'insert')
                                if is_insert:
                                    query_symbol = """INSERT INTO `ant_cryptotradingbot`.`crypto_symbols_macd_st_data` (`symbol_name`) VALUES ('{}');"""\
                                        .format(info['symbol'])
                                    is_insert = db_util.queryExecution(connection, query_symbol, 'insert')
                                    if is_insert:
                                        query_symbol = """INSERT `ant_cryptotradingbot`.`crypto_symbols_name` (symbol_name, symbol_full_name) VALUES ('{}', '_{}');""" \
                                            .format(info['symbol'].replace('USDT', ''), info['symbol'].replace('USDT', ''))
                                        is_insert = db_util.queryExecution(connection, query_symbol, 'insert')
                                        print('New Symbol {} ::: DBInsert ::: {}'.format(info['symbol'], is_insert))
                            elif symbol_count == 1:
                                query_symbol = """UPDATE `ant_cryptotradingbot`.`crypto_symbols_data` SET `is_Active` = True, `is_Margin_Trade` = {}, `quote_precision` = {} where `symbol_name` = '{}';""" \
                                    .format(info['isMarginTradingAllowed'],info['quotePrecision'],info['symbol'])
                                is_update = db_util.queryExecution(connection, query_symbol, 'update')
                                if is_update:
                                    print('Symbol {} ::: DBUpdate ::: {}'.format(info['symbol'], is_update))
                            logger.writeLogs(str(ls), 'info', log_filename)
                            logger.writeLogs(str(info), 'info', log_filename)
                            time.sleep(1)
                        else:
                            query_active = """UPDATE `ant_cryptotradingbot`.`crypto_symbols_data` SET `is_Active` = False where `symbol_name` not like '1000%' and `symbol_name`='{}';""" \
                                .format(info['symbol'])
                            is_update = db_util.queryExecution(connection, query_active, 'update')
                            if is_update:
                                print('Symbol {} ::: DBInActive ::: {}'.format(info['symbol'], is_update))
                    else:
                        query_active = """UPDATE `ant_cryptotradingbot`.`crypto_symbols_data` SET `is_Active` = False where `symbol_name` not like '1000%' and `symbol_name`='{}';""" \
                            .format(info['symbol'])
                        is_update = db_util.queryExecution(connection, query_active, 'update')
                        if is_update:
                            print('Symbol {} ::: DBInActive ::: {}'.format(info['symbol'], is_update))
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - get_symbol :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        logger.writeLogs(error_log, 'error', log_filename)
    finally:
        gc.collect()


def start_ta_tool():
    try:
        get_symbol()  # get dynamic symbols from binance exchange
        gc.collect()
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - start_ta_tool :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print('Error: - Start TA tool block error - {}'.format(error_log))


if __name__ == '__main__':
    dt_today = datetime.today()  # Local time
    dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
    start_date = str(datetime.strftime(dt_India, "%d%m%Y"))
    log_filename = "DB_Sym_Upd_{}.log".format(start_date)
    try:
        api_key = config.BINANCE_API_KEY
        api_secret = config.BINANCE_API_SECRET
        client = Client(api_key, api_secret)
        print('Connection opened... - ')
        start_ta_tool()
        sys.exit()
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - main :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print('Error: - Main error - {}'.format(error_log))
        print('Time sleep for : 1 min......')
        time.sleep(60)
