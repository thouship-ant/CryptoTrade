import pandas as pd
import numpy as np
import talib
from datetime import datetime
import ccxt
#from utils.logger import logger
import time, sys
from pytz import timezone
from binance.client import Client
from utils import config, db_util
from utils import supRes_level as srl
import warnings
warnings.filterwarnings('ignore')


def exchange_init():
    bin_exchange = ccxt.binance()
    return bin_exchange


def get_data_frame(symbol):
    try:
        # request historical candle (or klines) data using timestamp from above. interval either every min, hr, day
        # starttime = '30 minutes ago UTC' for last 30 mins time
        # e.g., client.get_historical_klines(symbol='ETHUSDT', '1m', starttime)
        # starttime = '1 Nov, 2021', '1 Dec, 2021' for last month of 2017
        # e.g., client.get_historical_klines(symbol='BTCUSDT', '1h', '1 Nov, 2021', '1 Dec, 2021')
        starttime = '1 day ago UTC'
        interval = s_interval
        bars = client.get_historical_klines(symbol, interval, starttime)
        for line in bars:
            del line[5:]
        df = pd.DataFrame(bars, columns=['date', 'open', 'high', 'low', 'close'])
        return df
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - get_data_frame :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print(symbol + ' - ' + error_log)


if __name__ == "__main__":
    dt_today = datetime.today()  # Local time
    dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
    start_date = str(datetime.strftime(dt_India, "%d%m%Y"))
    log_filename = "DB_Signal_Query_{}.log".format(start_date)
    s_interval = '15m'  # valid intervals - 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
    RSI_PERIOD = 6
    while True:
        try:
            exchange = exchange_init()
            dt_today = datetime.today()  # Local time
            dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
            current_date = str(datetime.strftime(dt_India, "%d%m%Y"))
            if start_date != current_date:
                sys.exit()
            api_key = config.BINANCE_API_KEY
            api_secret = config.BINANCE_API_SECRET
            client = Client(api_key, api_secret)
            connection = db_util.connect_database()
            if connection.is_connected():
                print('Connection opened... - ')
                """MACD signal"""
                query = """SELECT csd.`symbol_name`, `current_askPrice`, `upper_BBand_price`, `middle_BBand_price`, `lower_BBand_price`, `MACD_dif`, `MACD_dem`, `MACD_macd`, `last_RSI`, `2hrs_ST`, csd.`last_update_DateTime` FROM `ant_cryptotradingbot`.`crypto_symbols_data` as csd 
                INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_macd_st_data` as csmsd on csd.symbol_name = csmsd.symbol_name 
                WHERE (csd.upper_BBand_price > csd.current_askPrice 
                and (csd.middle_BBand_price < csd.current_askPrice or ((csd.middle_BBand_price + csd.lower_BBand_price)/2) < csd.current_askPrice)) 
                and csmsd.sum_dem_macd_current >= 0 and csmsd.sum_dem_macd_prv < csmsd.sum_dem_macd_current and csd.MACD_dif > 0 and csd.MACD_dem <= 0 and csd.MACD_macd > 0 and csd.last_RSI < 55 and csd.`2hrs_ST` = True and csd.is_Active = True;"""
                symbols_list = db_util.queryExecution(connection, query, 'select')
                signal_type = 'MACD'
                if len(symbols_list) == 0:
                    query = query.replace("and csmsd.sum_dem_macd_prv < csmsd.sum_dem_macd_current",
                                          "and csmsd.`2hrs_ST_prv` = False and csmsd.`2hrs_ST_current` = True and csmsd.sum_dem_macd_prv < csmsd.sum_dem_macd_current")
                    symbols_list = db_util.queryExecution(connection, query, 'select')
                    signal_type = 'SuperTrend'
                if len(symbols_list) == 0:
                    query = """SELECT csd.`symbol_name`, `current_askPrice`, `upper_BBand_price`, `middle_BBand_price`, `lower_BBand_price`, `MACD_dif`, `MACD_dem`, `MACD_macd`, `last_RSI`, `2hrs_ST`, csd.`last_update_DateTime`, lps.`PatternName` FROM `ant_cryptotradingbot`.`crypto_symbols_data` as csd 
                    INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_macd_st_data` as csmsd on csd.symbol_name = csmsd.symbol_name 
                    INNER JOIN `ant_cryptotradingbot`.`live_patterns_signal` as lps on csd.symbol_name = lps.symbol_name 
                    WHERE csd.MACD_macd > 0 and csd.last_RSI < 60 and csd.`2hrs_ST` = True and csd.is_Active = True
                    and lps.`PatternName` in ('Inverted Hammer','Hammer','Piercing Pattern','Morning Star','Morning Doji Star','Three Advancing White Soldiers','Engulfing Pattern') and lps.SignalType = 'bullish';"""
                    symbols_list = db_util.queryExecution(connection, query, 'select')
                    signal_type = 'Pattern'

                dt_today = datetime.today()  # Local time
                dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
                trade_date = str(dt_India.strftime('%Y-%m-%d %H:%M:%S'))
                if len(symbols_list) > 0:
                    for symbol in symbols_list:
                        is_entry_point = True
                        ss, rr = srl.main(symbol[0])
                        symbol_info = exchange.fetch_ticker(symbol[0])['info']
                        cur_ask_price = round(float(symbol_info['askPrice']), 8)
                        ss_trim = ss[-2:]
                        rr_trim = rr[-2:]
                        for sup in ss_trim:
                            if sup[1] > cur_ask_price:
                                is_entry_point = False
                        if is_entry_point:
                            for res in rr_trim:
                                if res[1] > cur_ask_price:
                                    is_entry_point = True
                                else:
                                    is_entry_point = False

                        symbol_df = get_data_frame(symbol[0])
                        closes = symbol_df['close'].tolist()
                        icloses = [float(c) for c in closes]
                        np_closes = np.array(icloses)
                        rsi = talib.RSI(np_closes, RSI_PERIOD)
                        last_rsi = rsi[-1]
                        if last_rsi <= 60 or is_entry_point:
                            update_date = str(symbol[10].strftime('%Y-%m-%d %H:%M:%S'))
                            new_signal_type = signal_type
                            if signal_type == "Pattern":
                                new_signal_type = signal_type + '-' + symbol[11]
                            insert_query = """INSERT `ant_cryptotradingbot`.`db_query_data` (`track_date`, `symbol_name`, `signal_type`, 
                            `current_askPrice`, `upper_BBand_price`, `middle_BBand_price`, `lower_BBand_price`, `MACD_dif`, 
                            `MACD_dem`, `MACD_macd`, `last_RSI`, `15mins_ST`, `30mins_ST`, `2hrs_ST`, `1d_ST`, `update_date`)  
                            VALUES ('{}','{}','{}',{},{},{},{},{},{},{},{},0,0,{},0,'{}');""" \
                                .format(trade_date, symbol[0], new_signal_type, symbol[1], symbol[2], symbol[3], symbol[4],
                                        symbol[5], symbol[6], symbol[7], symbol[8], symbol[9], update_date)
                            is_insert = db_util.queryExecution(connection, insert_query, 'insert')
                            print('Symbol ::: {} , Signal ::: {} , Is_Inserted ::: {}'
                                             .format(symbol[0], new_signal_type, is_insert))
            print('Time sleep for : 15 minutes......')
            time.sleep(898)
        except Exception as ex:
            error_log = str(ex).replace('\'', '\'\'') + " - main :: line ::" \
                        + str(sys.exc_info()[2].tb_lineno)
            print('Error: - Main error - {}'.format(error_log))
            print('Time sleep for : 1 min......')
            time.sleep(60)
            continue
