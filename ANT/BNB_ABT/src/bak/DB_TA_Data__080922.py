import pandas as pd
import numpy as np
import talib
from talib import MA_Type
from datetime import datetime
from pytz import timezone
from binance.client import Client
from utils import config, db_util
import time, sys, gc
#from utils.logger import logger
import ccxt
import warnings
warnings.filterwarnings('ignore')
pd.set_option('display.max_rows', None)


global symbol, exclude_symbols, qty, in_position


def exchange_init():
    bin_exchange = ccxt.binance()
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
        print(':: Error: - Main error - ' + error_log)
        return [], []
    finally:
        gc.collect()


def tr(df):
    df['previous_close'] = df['close'].shift(1)
    df['high-low'] = abs(df['high'] - df['low'])
    df['high-pc'] = abs(df['high'] - df['previous_close'])
    df['low-pc'] = abs(df['low'] - df['previous_close'])
    tr = df[['high-low', 'high-pc', 'low-pc']].max(axis=1)
    return tr


def atr(df, period):
    df['tr'] = tr(df)
    # print('calculating average true range')
    atr = df['tr'].rolling(period).mean()
    return atr


def supertrend(df, period=7, multiplier=3):
    # print('calculating supertrend')
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
                                        if is_insert:
                                            lst_symbols.append(ls['symbol'])
                                    print('New Symbol {} ::: DBInsert ::: {}'.format(info['symbol'], is_insert))
        return lst_symbols
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - get_symbol :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print(symbol + ' - ' + error_log)
        return []
    finally:
        gc.collect()


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
    finally:
        gc.collect()


def get_ta_data(symbol):
    update_query = ''
    try:
        exchange = exchange_init()
        symbol_df = get_data_frame(symbol)

        # calculate short and long EMA mostly using close values
        shortEMA = symbol_df['close'].ewm(span=12, adjust=False).mean()
        longEMA = symbol_df['close'].ewm(span=26, adjust=False).mean()

        # Calculate MACD and signal line
        MACD = shortEMA - longEMA
        signal = MACD.ewm(span=9, adjust=False).mean()

        symbol_df['MACD'] = MACD
        symbol_df['signal'] = signal

        # To Print in human readable date and time (from timestamp)
        symbol_df.set_index('date', inplace=True)
        symbol_df.index = pd.to_datetime(symbol_df.index, unit='ms')  # index set to first column = date_and_time

        symbol_df['Trigger'] = np.where(symbol_df['MACD'] > symbol_df['signal'], 1, 0)
        symbol_df['Position'] = symbol_df['Trigger'].diff()

        # Add buy and sell columns
        symbol_df['Buy'] = np.where(symbol_df['Position'] == 1, symbol_df['close'], np.NAN)
        symbol_df['Sell'] = np.where(symbol_df['Position'] == -1, symbol_df['close'], np.NAN)

        # MACD value for last closing
        PRV_MACD_DIF = round(float(symbol_df['MACD'][-3]), 8)
        PRV_MACD_DEM = round(float(symbol_df['signal'][-3]), 8)
        PRV_MACD_MACD = round(float((-1 * PRV_MACD_DEM + PRV_MACD_DIF)), 8)
        MACD_DIF = round(float(symbol_df['MACD'][-2]), 8)
        MACD_DEM = round(float(symbol_df['signal'][-2]), 8)
        MACD_MACD = round(float((-1 * MACD_DEM + MACD_DIF)), 8)
        # SUM_MACD_DEM = MACD_DEM + MACD_MACD

        # RSI value for last closing
        closes = symbol_df['close'].tolist()
        icloses = [float(c) for c in closes]
        np_closes = np.array(icloses)
        rsi = talib.RSI(np_closes, RSI_PERIOD)
        symbol_df['rsi'] = rsi
        last_rsi = round(float(rsi[-1]), 2)

        # Bolinger Bands (upper, middle, lower) value for last closing
        np_close = np.array(icloses, dtype=float)
        upper_bands, middle_bands, lower_bands = talib.BBANDS(np_close, matype=MA_Type.T3)
        f_upper_bands = round(float(upper_bands[-1]), 8)
        f_middle_bands = round(float(middle_bands[-1]), 8)
        f_lower_bands = round(float(lower_bands[-1]), 8)

        # Stochastic (K, D)
        STOCH = 0
        mystochrsi = talib.STOCH(symbol_df.high, symbol_df.low, symbol_df.close, slowk_period=3, slowd_period=3, fastk_period=14)
        # mystochrsi = Stoch(symbol_df.close.astype(float), symbol_df.high.astype(float), symbol_df.low.astype(float), 3, 3, 14)
        symbol_df['StochrsiK'], symbol_df['StochrsiD'] = mystochrsi
        # print(k_values)
        # print(d_values)
        # d_values = k_values.rolling(3).mean()
        symbol_df["trigger"] = np.where(stoch_get_trigger(symbol_df), 1, 0)
        # print(symbol_df)
        trigger_val = np.where(
            symbol_df.trigger & (symbol_df.StochrsiK.between(25, 75)) & (symbol_df.StochrsiD.between(25, 75)), 1, 0)
        last_k = symbol_df.StochrsiK.astype(str).iloc[-1]
        last_d = symbol_df.StochrsiD.astype(str).iloc[-1]
        print("{} :: lastK : {} :: lastD : {} :: triggerVal : {}".format(symbol, round(float(last_k), 4), round(float(last_d), 4),
                                                                   trigger_val[-1]))
        if trigger_val[-1] == 1:
            STOCH = 1

        symbol_info = exchange.fetch_ticker(symbol)['info']
        cur_ask_price = round(float(symbol_info['askPrice']), 8)
        cur_bid_price = round(float(symbol_info['bidPrice']), 8)
        price_cng = round(float(symbol_info['priceChange']), 8)
        percent_cng = round(float(symbol_info['priceChangePercent']), 2)
        volumes = int(float(symbol_info['volume']))
        is_uptrend_lst, close_price_lst = check_supertrend(exchange, symbol, '2h', 1000)
        last_row_index = len(is_uptrend_lst.index) - 1
        previous_row_index = last_row_index - 1
        Two_hrs_st_prev = is_uptrend_lst[previous_row_index]
        Two_hrs_st = is_uptrend_lst[last_row_index]
        is_uptrend_lst_15m, close_price_lst_15m = check_supertrend(exchange, symbol, '15m', 1000)
        last_row_index_15m = len(is_uptrend_lst_15m.index) - 1
        Fifteen_mins_st = is_uptrend_lst_15m[last_row_index_15m]

        dt_today = datetime.today()  # Local time
        dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
        update_date = str(dt_India.strftime('%Y-%m-%d %H:%M:%S'))

        # update_query = """UPDATE `ant_cryptotradingbot`.`crypto_symbols_macd_st_data` INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_data` on `crypto_symbols_data`.`symbol_name` = `crypto_symbols_macd_st_data`.`symbol_name` SET `sum_dem_macd_prv` = (`crypto_symbols_data`.`MACD_dem` + `crypto_symbols_data`.`MACD_macd`), `sum_dem_macd_current`={}, `2hrs_ST_prv`={}, `2hrs_ST_current`={}, `crypto_symbols_macd_st_data`.`last_update_DateTime`='{}' WHERE `crypto_symbols_macd_st_data`.`symbol_name`='{}';\n"""\
        #     .format(MACD_MACD, str(Two_hrs_st_prev), str(Two_hrs_st), update_date, symbol)
        update_query = """UPDATE `ant_cryptotradingbot`.`crypto_symbols_macd_st_data` SET `sum_dem_macd_prv` = {}, `sum_dem_macd_current`={}, `2hrs_ST_prv`={}, `2hrs_ST_current`={}, `crypto_symbols_macd_st_data`.`last_update_DateTime`='{}' WHERE `crypto_symbols_macd_st_data`.`symbol_name`='{}';\n""" \
            .format(PRV_MACD_MACD, MACD_MACD, str(Two_hrs_st_prev), str(Two_hrs_st), update_date, symbol)
        update_query_1 = """UPDATE `ant_cryptotradingbot`.`crypto_symbols_data` SET `current_askPrice`={}, `current_bidPrice`={}, `24hrs_price_change`={}, `24hrs_change`={}, `upper_BBand_price`={}, `middle_BBand_price`={}, `lower_BBand_price`={}, `MACD_dif`={}, `MACD_dem`={}, `MACD_macd`={}, `last_RSI`={}, `15mins_ST`={}, `2hrs_ST`={}, `Volumes`={}, stoch={}, `last_update_DateTime`='{}' WHERE `symbol_name`='{}';\n"""\
            .format(cur_ask_price, cur_bid_price, price_cng, percent_cng, f_upper_bands, f_middle_bands, f_lower_bands, MACD_DIF, MACD_DEM, MACD_MACD, last_rsi, str(Fifteen_mins_st), str(Two_hrs_st), volumes, STOCH, update_date, symbol)
        is_update_ta_data = False
        connection = db_util.connect_database()
        if connection.is_connected():
            is_update_ta_data = db_util.queryExecution(connection, update_query, 'update')
            if is_update_ta_data:
                is_update_ta_data = db_util.queryExecution(connection, update_query_1, 'update')
        print('{} ::: DIF: {} , DEM: {}, MACD: {} :: RSI: {} :: KD: {} :: DB Update : {}'
                         .format(symbol, str(MACD_DIF), str(MACD_DEM), str(MACD_MACD), str(last_rsi), str(last_k)+':'+str(last_d), str(is_update_ta_data)))
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - get_ta_data :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print(symbol + ' - ' + error_log)
    finally:
        gc.collect()


# StochasticRSI Function
def Stoch(close,high,low, smoothk, smoothd, n):
    lowestlow = pd.Series.rolling(low,window=n,center=False).min()
    highesthigh = pd.Series.rolling(high, window=n, center=False).max()
    K = pd.Series.rolling(100*((close-lowestlow)/(highesthigh-lowestlow)), window=smoothk).mean()
    D = pd.Series.rolling(K, window=smoothd).mean()
    return K, D


def stoch_get_trigger(df):
    dfx = pd.DataFrame()
    for i in range(72, 97):
        mask = (df["StochrsiK"].shift(i) < 25) & (df["StochrsiD"].shift(i) < 25)
        dfx = dfx.append(mask, ignore_index=True)
    return dfx.sum(axis=0)


def start_ta_tool():
    try:
        while True:
            dt_today = datetime.today()  # Local time
            dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
            current_date = str(datetime.strftime(dt_India, "%d%m%Y"))
            if start_date != current_date:
                sys.exit()
            symbols = []
            exclude_symbols = ['SHIBUSDT', 'VENUSDT', 'FETUSDT', 'ERDUSDT', 'NPXSUSDT', 'STORMUSDT', 'HCUSDT', 'STRATUSDT',
                               'LENDUSDT', 'BKRWUSDT', 'BTTUSDT', 'BZRXUSDT', 'NUUSDT', 'KEEPUSDT', 'AUDUSDT', 'BTTCUSDT']
            connection = db_util.connect_database()
            if connection.is_connected():
                query = 'SELECT symbol_name from `ant_cryptotradingbot`.`crypto_symbols_data` where is_active = true order by `symbol_id` asc'
                get_symbol_list = db_util.queryExecution(connection, query, 'select')
                if len(get_symbol_list) > 0:
                    for exclude_symbol in get_symbol_list:
                        if not (exclude_symbol[0] in exclude_symbols):
                            symbols.append(exclude_symbol[0])
                            exclude_symbols.append(exclude_symbol[0])
                lst_symbols = get_symbol(symbols, exclude_symbols)  # get dynamic symbols from binance exchange

                if len(lst_symbols) > 0:
                    for idx, symbol in enumerate(lst_symbols):
                        get_ta_data(symbol)
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
        error_log = str(ex).replace('\'', '\'\'') + " - start_ta_tool :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print('Error: - Start TA tool block error - {}'.format(error_log))


if __name__ == '__main__':
    while True:
        dt_today = datetime.today()  # Local time
        dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
        start_date = str(datetime.strftime(dt_India, "%d%m%Y"))
        log_filename = "DB_TA_Data_{}.log".format(start_date)
        try:
            api_key = config.BINANCE_API_KEY
            api_secret = config.BINANCE_API_SECRET
            client = Client(api_key, api_secret)
            print('Connection opened... - ')
            s_interval = '15m'  # valid intervals - 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
            RSI_PERIOD = 6
            RSI_OVERBOUGHT = 70
            RSI_OVERSOLD = 30
            start_ta_tool()
        except Exception as ex:
            error_log = str(ex).replace('\'', '\'\'') + " - main :: line ::" \
                        + str(sys.exc_info()[2].tb_lineno)
            print('Error: - Main error - {}'.format(error_log))
            print('Time sleep for : 1 min......')
            time.sleep(60)
            continue
