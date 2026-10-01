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
        stop_price = 0
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

        close_price = float(df2.Close[-1])
        if len(peaks_idx) < 1 or len(troughs_idx) < 1:
            return 0, close_price, stop_price
        elif int(peaks_idx[-1]) < int(troughs_idx[-1]): # and up_run_length > 0
            stop_price = float(df2.Close[troughs_idx[-1]])
            return 1, close_price, stop_price
        elif int(peaks_idx[-1]) > int(troughs_idx[-1]): # and down_run_length > 0
            stop_price = float(df2.Close[peaks_idx[-1]])
            return -1, close_price, stop_price
        else:
            return 0, close_price, stop_price
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - price_breakOut :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print('Error: - Price BreakOut signal block error - {}'.format(error_log))
    finally:
        del df2
        gc.collect()


def start_trade(symbol, signal_side):
    try:
        username = 'thouship'
        client = Client(config.BINANCE_API_FUTURE_KEY, config.BINANCE_API_FUTURE_SECRET)
        bal_info = client.futures_account_balance()
        usdt_balance = 0.00
        for check_balance in bal_info:
            if check_balance["asset"] == "USDT":
                usdt_balance = round(float(check_balance["balance"]), 2)
        print('Current USDT : {}'.format(usdt_balance))
        if usdt_balance > 5:
            df = download_data(symbol)
            if len(df) > 0:
                buy_signal_value, close_price, stop_price = price_breakout_signal_data(df)
                if (buy_signal_value == 1 and signal_side == 'BUY') or (buy_signal_value == -1 and signal_side == 'SELL'):
                    info = client.futures_symbol_ticker(symbol=replace_future_symbolname(symbol))
                    exchange = ccxt.binance()
                    symbol_info = exchange.fetch_ticker(symbol)['info']
                    price_prec = dbsq.symbol_precision(symbol_info)+3
                    getting_price = 'bidPrice'
                    if signal_side == 'SELL':
                        getting_price = 'askPrice'
                    actual_open_price = round(float(symbol_info[getting_price]), price_prec)
                    '''Live Trade'''
                    ordered_qty = 0
                    orderId = 0
                    orderStatus = 'NEW'
                    qty = int((usdt_balance - 0.5)/actual_open_price)*5
                    is_order_open = True
                    while orderId == 0:
                        try:
                            actual_open_price = round(float(actual_open_price), price_prec)
                            print("{} :: {} :: Quantity:{} , Symbol:{} , price:{}".format(username, signal_side, qty,symbol,actual_open_price))
                            buy_order = client.futures_create_order(symbol=replace_future_symbolname(symbol), side=signal_side, type='LIMIT',
                                                                    quantity=qty, price=actual_open_price, timeinforce='GTC')
                            time.sleep(2)
                            orderId = int(buy_order['orderId'])
                            orderStatus = buy_order['status']
                            actual_open_price = round(float(buy_order['avgPrice']), price_prec)
                            if actual_open_price <= 0:
                                actual_open_price = round(float(buy_order['price']), price_prec)
                        except Exception as ex:
                            error_log = symbol + ' -- ' + str(ex).replace('\'', '\'\'') + " - trade_logic :: line ::" \
                                        + str(sys.exc_info()[2].tb_lineno)
                            time.sleep(2)
                            if str(ex).endswith('Precision is over the maximum defined for this asset.'):
                                print(symbol + ' - ' + str(actual_open_price) + ' - ' + str(price_prec) + ' - ' + error_log)
                                price_prec = price_prec - 1
                            elif str(ex).endswith('Invalid symbol.') or str(ex).endswith('Invalid symbol status for opening position.'):
                                break
                            else:
                                print(symbol + ' - ' + error_log)
                            continue
                    
                    while orderStatus != 'FILLED' and orderStatus != 'CANCELLED':
                        try:
                            buy_order = client.futures_get_order(symbol=replace_future_symbolname(symbol), orderId=orderId)
                            orderStatus = buy_order['status']
                            symbol_info = exchange.fetch_ticker(symbol)['info']
                            cur_ask_price = round(float(symbol_info[getting_price]), price_prec)
                            current_percent = round(float((cur_ask_price - actual_open_price) / (actual_open_price / 100)), 2)
                            if signal_side == 'SELL':
                                current_percent = -1*current_percent
                            print("{} :: {} :: Quantity:{} , Symbol:{} , Open_price:{} , Current_price:{} ({}%)".format(username, signal_side, qty,symbol,actual_open_price,cur_ask_price,current_percent))
                            if current_percent > 1 and orderStatus == 'NEW':
                                break
                            time.sleep(30)
                        except Exception as ex:
                            error_log = symbol + ' -- ' + str(ex).replace('\'', '\'\'') + " - trade_logic :: line ::" \
                                        + str(sys.exc_info()[2].tb_lineno)
                            print(symbol + ' - ' + error_log)
                            time.sleep(30)

                    buy_order = client.futures_get_order(symbol=replace_future_symbolname(symbol), orderId=orderId)
                    buy_status = buy_order['status']
                    if buy_status == 'FILLED':
                        sell_order = None
                        stop_order = None
                        sell_orderId = 0
                        stop_orderId = 0
                        trailing_stoploss = 0.5
                        sell_orderStatus = 'NEW'
                        stop_orderStatus = 'NEW'
                        ordered_qty = int(float(buy_order['executedQty']))
                        actual_open_price = round(float(buy_order['avgPrice']), price_prec)
                        cur_ask_price = actual_open_price
                        closed_order_type = 'SELL'
                        if signal_side == 'SELL':
                            closed_order_type = 'BUY'
                        getting_price = 'bidPrice'
                        if closed_order_type == 'SELL':
                            getting_price = 'askPrice'
                        while is_order_open:
                            df = download_data(symbol)
                            if len(df) > 0:
                                signal_value, close_price, stop_price = price_breakout_signal_data(df)
                                close_price = round(float(close_price), price_prec)
                                stop_price = round(float(stop_price), price_prec)
                                try:
                                    symbol_info = exchange.fetch_ticker(symbol)['info']
                                    cur_ask_price = round(float(symbol_info[getting_price]), price_prec)
                                except:
                                    continue
                                current_percent = round(float((cur_ask_price - actual_open_price) / (actual_open_price / 100)), 2)
                                if closed_order_type == 'BUY':
                                    current_percent = -1*current_percent
                                print("{} :: {} :: Quantity:{} , Symbol:{} , open_price:{} , close_price:{} , stop_price:{} , current_price:{} ({}%)".format(username, closed_order_type, ordered_qty,symbol, actual_open_price, close_price, stop_price, cur_ask_price, current_percent))
                                if stop_orderId > 0:
                                    stop_order = client.futures_get_order(symbol=replace_future_symbolname(symbol), orderId=stop_orderId, side=closed_order_type)
                                    stop_orderStatus = stop_order['status']
                                if stop_orderId > 0 and stop_orderStatus == 'FILLED':
                                   break
                                if (signal_value == 1 and closed_order_type == 'BUY') or (signal_value == -1 and closed_order_type == 'SELL') or (current_percent > trailing_stoploss and stop_orderId == 0):
                                    while sell_orderId == 0 and stop_orderId == 0:
                                        try:
                                            if (signal_value == 1 and closed_order_type == 'BUY') or (signal_value == -1 and closed_order_type == 'SELL'):
                                                close_price = round(float(cur_ask_price + (cur_ask_price * 0.2 / 100)), price_prec)
                                                if closed_order_type == 'BUY':
                                                    close_price = round(float(cur_ask_price - (cur_ask_price * 0.2 / 100)), price_prec)
                                                if sell_orderId > 0:
                                                    client.futures_cancel_order(orderId=sell_orderId)
                                                sell_orderId = 0
                                                sell_order = client.futures_create_order(symbol=replace_future_symbolname(symbol), side=closed_order_type,
                                                                                         type='TAKE_PROFIT_MARKET'
                                                                                         , quantity=ordered_qty, stopprice=round(close_price,price_prec),
                                                                                         closePosition='true')
                                                time.sleep(5)
                                                sell_orderId = int(sell_order['orderId'])
                                                sell_orderStatus = sell_order['status']
                                                print("{} :: {} :: Quantity:{} , Symbol:{} , open_price:{} , close_price:{} , current_price:{} ({}%) --- Done".format(username, closed_order_type, ordered_qty,symbol,actual_open_price,close_price,cur_ask_price,current_percent))
                                            if current_percent > trailing_stoploss:
                                                if stop_orderId > 0:
                                                    client.futures_cancel_order(orderId=stop_orderId)
                                                stop_orderId = 0
                                                if current_percent > trailing_stoploss:
                                                    stop_price = round(float(actual_open_price + (actual_open_price * (trailing_stoploss - 0.5) / 100)), price_prec)
                                                stop_order = client.futures_create_order(symbol=replace_future_symbolname(symbol), side=closed_order_type,
                                                                                         type='STOP_MARKET'
                                                                                         , quantity=ordered_qty, stopprice=round(stop_price,price_prec),
                                                                                         closePosition='true')
                                                time.sleep(5)
                                                stop_orderId = int(stop_order['orderId'])
                                                stop_orderStatus = stop_order['status']
                                                trailing_stoploss = current_percent
                                                print("{} :: {} :: Quantity:{} , Symbol:{} , open_price:{} , stop_price:{} , current_price:{} ({}%) --- Done".format(username, closed_order_type, ordered_qty,symbol,actual_open_price,stop_price,cur_ask_price,current_percent))
                                        except Exception as ex:
                                            error_log = str(ex).replace('\'', '\'\'') + " - trade_logic :: line ::" \
                                                        + str(sys.exc_info()[2].tb_lineno)
                                            time.sleep(5)
                                            if str(ex).endswith('Precision is over the maximum defined for this asset.'):
                                                print(symbol + ' - ' + str(close_price) + ' - ' + str(price_prec) + ' - ' + error_log)
                                                price_prec = price_prec - 1
                                            else:
                                                print(symbol + ' - ' + error_log)
                                                close_price = round(float(close_price + (close_price * 0.05 / 100)), price_prec)
                                                if closed_order_type == 'BUY':
                                                    close_price = round(float(close_price - (close_price * 0.05 / 100)), price_prec)
                                            continue
                                    is_order_open = False
                                    time.sleep(120)
                                else:
                                    continue
                        
                        while sell_orderStatus != 'FILLED':
                            stop_order = client.futures_get_order(symbol=replace_future_symbolname(symbol), orderId=stop_orderId, side=closed_order_type)
                            if stop_order['status'] == 'FILLED':
                                sell_orderId = stop_orderId
                            sell_order = client.futures_get_order(symbol=replace_future_symbolname(symbol), orderId=sell_orderId, side=closed_order_type)
                            sell_orderStatus = sell_order['status']
                            print("{} :: {} :: Quantity:{} , Symbol:{} , open_price:{} , close_price:{} , stop_price:{} --- {}".format(username, closed_order_type, ordered_qty,symbol, actual_open_price, close_price, stop_price, sell_orderStatus))
                            time.sleep(30)
                            
                        if sell_orderStatus == 'FILLED':
                            client.futures_cancel_all_open_orders(symbol=replace_future_symbolname(symbol))
                            close_price = round(float(sell_order['avgPrice']), price_prec)    
                            print("Order closed  ===  {} :: {} :: Quantity:{} , Symbol:{} , open_price:{} , close_price:{} --- {}".format(username, closed_order_type, ordered_qty,symbol, actual_open_price, close_price, sell_orderStatus))

                        return
                    else:
                        return
                else:
                    return
            else:
                return
        else:
            return
    except Exception as ex:
        error_log = symbol + ' -- ' + str(ex).replace('\'', '\'\'') + " - price_breakOut :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print('Error: - Price BreakOut signal block error - {}'.format(error_log))
        return
    finally:
        gc.collect()


def start_pbo_tool():
    cur_symbol = ''
    is_trade_position = False
    while True:
        try:
            dt_today = datetime.today()  # Local time
            dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
            current_date = str(datetime.strftime(dt_India, "%d%m%Y"))
            # if start_date != current_date:
                # sys.exit()
            connection = db_util.connect_database()
            if connection.is_connected():
                query = 'SELECT symbol_name, price_breakOut_entry from `ant_cryptotradingbot`.`crypto_symbols_data` where is_active = true and is_Future_Trade = true and `price_breakOut_entry` != 0'
                get_symbol_list = db_util.queryExecution(connection, query, 'select')
                connection.close()
                close_price = 0
                stop_price = 0
                print('Symbols length : {}'.format(len(get_symbol_list)))
                for symbol_name in get_symbol_list:
                    try:
                        print(symbol_name)
                        cur_symbol = symbol_name[0]
                        signal_value = symbol_name[1]
                        if signal_value == 1:
                            signal_data = 'BUY'
                        elif signal_value == -1:
                            signal_data = 'SELL'
                        start_trade(cur_symbol,signal_data)
                    except Exception as e:
                        error_log = str(e).replace('\'', '\'\'') + " - start_pbo_tool :: line ::" \
                                    + str(sys.exc_info()[2].tb_lineno)
                        print('failed on symbol: {} - error ::: {}'.format(symbol_name, error_log))
                    finally:
                        gc.collect()
                    time.sleep(2)
                print('Time sleep for : 5 minutes.....')
                time.sleep(300)
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
            s_interval = '1h'  # valid intervals - 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
            print('BreakOut_Query started...')
            print('Time sleep for : 30 minutes.....')
            time.sleep(1800)
            start_pbo_tool()
        except Exception as ex:
            error_log = str(ex).replace('\'', '\'\'') + " - main :: line ::" \
                        + str(sys.exc_info()[2].tb_lineno)
            print('Error: - Main error - {}'.format(error_log))
            print('Time sleep for : 1 min......')
            time.sleep(60)
            continue
