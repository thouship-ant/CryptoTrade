#%matplotlib inline
import os, sys, time, gc
import ccxt
import talib
import pandas as pd
import pandas_ta as ta
import matplotlib.pyplot as plt
import threading
from matplotlib.animation import FuncAnimation
from scipy.signal import savgol_filter
from scipy.signal import find_peaks
from datetime import datetime, timedelta
from pytz import timezone
from binance.client import Client
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from src.data import DB_Signal_Query as dbsq
from src.utils import db_util
from src.utils import config
import warnings
warnings.filterwarnings('ignore')
#pd.set_option('mode.chained_assignment', None)
global is_trade_position


def download_data(symbol, limit=800):
    try:
        pd.set_option('display.max_rows', None)
        pd.options.mode.chained_assignment = None  # default='warn'
        exchange = ccxt.binance()
        bars = exchange.fetch_ohlcv(symbol.replace('1000', ''), timeframe=s_interval, limit=limit)
        df = pd.DataFrame(bars, columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df['Date'] = pd.to_datetime(df['Date'], unit='ms')
        df["Open"] = df.Open.astype(float)
        df["High"] = df.Open.astype(float)
        df["Low"] = df.Open.astype(float)
        df["Close"] = df.Open.astype(float)

        df["atr"] = ta.atr(high=df.High, low=df.Low, close=df.Close)
        df["atr"] = df.atr.rolling(window=30).mean()

        # df['Adj Close'] = df['Close']
        last_date = str(df['Date'][df.index[-1]].strftime('%Y-%m-%d'))
        dt_yesterday = datetime.today() - timedelta(days=1)
        dt_India_yesterday = dt_yesterday.astimezone(timezone('Asia/Kolkata'))
        trade_date_yesterday = str(dt_India_yesterday.strftime('%Y-%m-%d'))
        dt_today = datetime.today()
        dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
        trade_date = str(dt_India.strftime('%Y-%m-%d'))
        time.sleep(4)
        if last_date == trade_date_yesterday or last_date == trade_date:
            df.set_index("Date", inplace= True)
            return df
        else:
            return []
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - download_data :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print('Error: - Download data block error - {} - for {}'.format(error_log, symbol.replace('1000', '')))
        return []
    finally:
        gc.collect()



def price_breakout_signal_data(df2):
    try:
        df2["close_smooth"] = savgol_filter(df2.Close, 49, 5)
        buy_price = 0
        sell_price = 0
        # fig, ax = plt.subplots()
        # plt.xticks(rotation =-30)
        # price = ax.plot(df2.index, df2.close,c='grey', lw=2, alpha=0.5, zorder=5)
        # price_smooth, = ax.plot(df2.index, df2.close_smooth, c='b', lw=2, zorder=5)

        atr = df2.atr.iloc[-1]

        peaks_idx, _ = find_peaks(df2.close_smooth, distance = 15,
                                 width = 3, prominence=atr)
        troughs_idx, _ = find_peaks(-1*df2.close_smooth, distance = 15,
                                 width = 3, prominence=atr)

        up_run_length = 0
        up_run = True
        while up_run:
            if 2 + up_run_length > len(peaks_idx) or 2 + up_run_length > len(troughs_idx):
                break
            if df2.close_smooth.iloc[peaks_idx[-1 - up_run_length]] > df2.close_smooth.iloc[peaks_idx[-2 - up_run_length]] and \
                df2.close_smooth.iloc[troughs_idx[-1 - up_run_length]] > df2.close_smooth.iloc[troughs_idx[-2 - up_run_length]]:
                up_run_length += 1
            else:
                up_run = False
        
        down_run_length = 0
        down_run = True
        while down_run:
            if 2 + down_run_length > len(peaks_idx) or 2 + down_run_length > len(troughs_idx):
                break
            if df2.close_smooth.iloc[peaks_idx[-1 - down_run_length]] > df2.close_smooth.iloc[peaks_idx[-2 - down_run_length]] and \
                df2.close_smooth.iloc[troughs_idx[-1 - down_run_length]] > df2.close_smooth.iloc[troughs_idx[-2 - down_run_length]]:
                down_run_length += 1
            else:
                down_run = False

        if len(peaks_idx) < 1 or len(troughs_idx) < 1:
            return 0, buy_price, sell_price
        elif int(peaks_idx[-1]) < int(troughs_idx[-1]):  # and up_run_length > 0
            buy_price = float(df2.High[peaks_idx[-1]])
            sell_price = float(df2.High[troughs_idx[-1]])
            return 1, buy_price, sell_price
        elif int(peaks_idx[-1]) > int(troughs_idx[-1]): # and down_run_length > 0
            buy_price = float(df2.Low[peaks_idx[-1]])
            sell_price = float(df2.Low[troughs_idx[-1]])
            return -1, buy_price, sell_price
        else:
            return 0, buy_price, sell_price
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - price_breakOut :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print('Error: - Price BreakOut signal block error - {}'.format(error_log))
    finally:
        del df2
        gc.collect()


def start_pbo_tool():
    cur_symbol = ''
    is_trade_position = False
    while True:
        try:
            dt_today = datetime.today()  # Local time
            dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
            current_date = str(datetime.strftime(dt_India, "%d%m%Y"))
            if start_date != current_date:
                sys.exit()
            connection = db_util.connect_database()
            if connection.is_connected():
                query = 'SELECT symbol_name from `ant_cryptotradingbot`.`crypto_symbols_data` where is_active = true order by `symbol_id` asc limit {} offset {}'\
                    .format(limit, offset)
                get_symbol_list = db_util.queryExecution(connection, query, 'select')
                buy_price = 0
                sell_price = 0
                if len(get_symbol_list) > 0:
                    symbols_count = 0
                    insert_count = 0
                    for symbol_name in get_symbol_list:
                        try:
                            symbols_count += 1
                            cur_symbol = symbol_name[0]
                            df = download_data(cur_symbol)
                            if len(df) > 0:
                                signal_data = 'No signal'
                                exchange = ccxt.binance()
                                symbol_info = exchange.fetch_ticker(cur_symbol)['info']
                                price_prec = dbsq.symbol_precision(symbol_info)+1
                                current_price = round(float(symbol_info['askPrice']), price_prec)
                                ema_7 = round(talib.EMA(df['Close'], 7)[(len(df)-1)], price_prec)
                                ema_21 = round(talib.EMA(df['Close'], 21)[(len(df)-1)], price_prec)
                                ema_99 = round(talib.EMA(df['Close'], 99)[(len(df)-1)], price_prec)
                                ema_200 = round(talib.EMA(df['Close'], 200)[(len(df)-1)], price_prec)
                                signal_value, buy_price, sell_price = price_breakout_signal_data(df)
                                buy_price = round(float(buy_price), price_prec)
                                sell_price = round(float(sell_price), price_prec)
                                query_check = "SELECT symbol_name from `ant_cryptotradingbot`.`crypto_symbols_data` where `price_breakOut` != {} and `symbol_name`='{}';"\
                                    .format(signal_value, cur_symbol)
                                get_symbol_check = db_util.queryExecution(connection, query_check, 'select')
                                if (signal_value == 1 or signal_value == -1) and len(get_symbol_check) == 1:
                                    is_break_out = False
                                    if signal_value == 1 and ema_200 > ema_99 > ema_7 > ema_21:
                                        signal_data = 'BUY'
                                        is_break_out = True
                                    elif signal_value == -1 and ema_200 < ema_99 < ema_7 < ema_21:
                                        signal_data = 'SELL'
                                        is_break_out = True
                                    
                                    if is_break_out:
                                        upd_qry = "UPDATE `ant_cryptotradingbot`.`crypto_symbols_data` SET `price_breakOut` = {}, `price_breakOut_entry` = {} WHERE `symbol_name`='{}';" \
                                            .format(signal_value, signal_value, cur_symbol)
                                        db_util.queryExecution(connection, upd_qry, 'insert')
                                    else:
                                        upd_qry = "UPDATE `ant_cryptotradingbot`.`crypto_symbols_data` SET `price_breakOut_entry` = {} WHERE `symbol_name`='{}';" \
                                            .format(0, cur_symbol)
                                        db_util.queryExecution(connection, upd_qry, 'insert')
                                    insert_count += 1
                                    print('====Symbol :: {} - breakOut Signal :: {} - EMA7 Price :: {} - EMA21 Price :: {} - EMA99 Price :: {} - EMA200 Price :: {} - Current Price :: {} - Buy Price :: {} - Sell Price :: {} ===='.format(cur_symbol, signal_data, ema_7, ema_21, ema_99, ema_200, current_price, buy_price, sell_price))
                                else:
                                    upd_qry = "UPDATE `ant_cryptotradingbot`.`crypto_symbols_data` SET `price_breakOut_entry` = {} WHERE `symbol_name`='{}';" \
                                        .format(0, cur_symbol)
                                    db_util.queryExecution(connection, upd_qry, 'insert')
                                    insert_count += 1
                                    signal_data_val = 'Close'
                                    close_price = current_price
                                    if buy_price < current_price and buy_price > sell_price:
                                        signal_data_val = 'Buy'
                                        close_price = buy_price
                                    elif sell_price > current_price and buy_price < sell_price:
                                        signal_data_val = 'Sell'
                                        close_price = sell_price
                                    print('====Symbol :: {} breakOut entry Signal :: {} - EMA7 Price :: {} - EMA21 Price :: {} - EMA99 Price :: {} - EMA200 Price :: {} - Current Price :: {} - {} Price :: {} ===='.format(cur_symbol, signal_data, ema_7, ema_21, ema_99, ema_200, current_price, signal_data_val, close_price))
                        except Exception as e:
                            error_log = str(e).replace('\'', '\'\'') + " - start_pbo_tool :: line ::" \
                                        + str(sys.exc_info()[2].tb_lineno)
                            print('failed on symbol: {} - error ::: {}'.format(symbol_name, error_log))
                        finally:
                            del df
                            gc.collect()
                        time.sleep(2)
                    print('====Total Symbols are {} ({} entries inserted) ===='.format(symbols_count, insert_count))
            connection.close()
        except Exception as ex:
            error_log = str(ex).replace('\'', '\'\'') + " - start_pbo_tool :: line ::" \
                        + str(sys.exc_info()[2].tb_lineno)
            print('Error: - start_pbo_tool error - {}'.format(error_log))
            print('Time sleep for : 1 min......')
            time.sleep(60)
            continue


def replace_future_symbolname(symbol):
    if symbol == 'LUNAUSDT':
        return 'LUNA2USDT'
    elif symbol == 'BONKUSDT':
        return '1000BONKUSDT'
    elif symbol == 'FLOKIUSDT':
        return '1000FLOKIUSDT'
    elif symbol == 'LUNCUSDT':
        return '1000LUNCUSDT'
    elif symbol == 'PEPEUSDT':
        return '1000PEPEUSDT'
    elif symbol == 'RATSUSDT':
        return '1000RATSUSDT'
    elif symbol == 'SATSUSDT':
        return '1000SATSUSDT'
    elif symbol == 'SHIBUSDT':
        return '1000SHIBUSDT'
    elif symbol == 'XECUSDT':
        return '1000XECUSDT'
    else:
        return symbol


if __name__ == "__main__":
    while True:
        try:
            dt_today = datetime.today()  # Local time
            dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
            start_date = str(datetime.strftime(dt_India, "%d%m%Y"))
            log_filename = "DB_BreakOut_Query_{}.log".format(start_date)
            s_interval = '5m'  # valid intervals - 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
            print('BreakOut_Query started...')
            is_trade_position = False
            limit = sys.argv[1]
            offset = sys.argv[2]
            start_pbo_tool()
        except Exception as ex:
            error_log = str(ex).replace('\'', '\'\'') + " - main :: line ::" \
                        + str(sys.exc_info()[2].tb_lineno)
            print('Error: - Main error - {}'.format(error_log))
            print('Time sleep for : 1 min......')
            time.sleep(60)
            continue
