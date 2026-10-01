import pandas as pd
import numpy as np
import talib
from datetime import datetime
import ccxt
#from utils.logger import logger
import time, sys, os
import threading
from pytz import timezone
from binance.client import Client
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from src.utils import config, db_util
from src.utils import supRes_level as srl
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

        connection = db_util.connect_database()
        if connection.is_connected():
            del_qry = "UPDATE `ant_cryptotradingbot`.`crypto_symbols_data` SET `is_Active` = False WHERE `symbol_name`='{}';" \
                .format(symbol)
            db_util.queryExecution(connection, del_qry, 'insert')
            connection.close()
        return None
        

def symbol_precision(symbol_info_open, symbol_name=''):
    if symbol_name != '' and symbol_info_open is None:
        exchange = exchange_init()
        symbol_info_open = exchange.fetch_ticker(symbol_name)['info']        
    price_prec = 8
    high_price = str(symbol_info_open['highPrice'])
    low_price_prec = 8
    low_price = str(symbol_info_open['lowPrice'])
    while high_price.endswith("0"):
        high_price = high_price[0:len(high_price)-1]
        price_prec -= 1
    while low_price.endswith("0"):
        low_price = low_price[0:len(low_price)-1]
        low_price_prec -= 1
    if len(high_price) < len(low_price):
        price_prec = low_price_prec
    return price_prec


def check_open_entry(trade_id, trade_date, symbol_name, signal_type, signal_side, entry_price):
    i = 0
    isEntry_check = False
    while True:
        try:
            connection_open_entry = db_util.connect_database()
            if connection_open_entry.is_connected():
                demo_trade_done_query = """SELECT `trade_id`,`trade_date`,`symbol_name`,`entry_signal_type`,`signal_side`,`entry_price`,`entry_date`,`exit_price` 
                FROM `ant_cryptotradingbot`.`db_demo_trade` where `trade_id`={} and `entry_date` is not null and `exit_date` is null;"""\
                    .format(trade_id)
                demo_trade_done = db_util.queryExecution(connection_open_entry, demo_trade_done_query, 'select')
                connection_open_entry.close()
                if len(demo_trade_done) == 1:
                    print('=== Entry === Symbol ::: {} , Signal ::: {} - {} ===='
                          .format(demo_trade_done[0][2], demo_trade_done[0][3], demo_trade_done[0][4]))
                    check_open_exit(demo_trade_done[0][0], demo_trade_done[0][1], demo_trade_done[0][2], demo_trade_done[0][3], demo_trade_done[0][4], demo_trade_done[0][5], demo_trade_done[0][7])
                    break
            symbol_info_open = exchange.fetch_ticker(symbol_name)['info']
            price_prec = symbol_precision(symbol_info_open)
            entry_price = round(float(entry_price), price_prec)
            current_price = round(float(symbol_info_open['askPrice']), price_prec)
            if signal_side == 'SELL':
                current_price = round(float(symbol_info_open['bidPrice']), price_prec)
            current_percent = round(float((current_price - entry_price) / (entry_price / 100)), 2)
            if signal_side == 'SELL':
                current_percent = -1 * current_percent
            print('Symbol ::: {} , Signal ::: {} - {} , entry_price ::: {} , current_price ::: {} , current_percent ::: {}%'
                  .format(symbol_name, signal_type, signal_side, entry_price, current_price, current_percent))

            if (signal_side == 'BUY' and current_price <= entry_price) or (signal_side == 'SELL' and current_price >= entry_price) or i >= 15 or current_percent <= 1 or isEntry_check or signal_type == 'TELEGRAM':
                isEntry_check = True
                dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
                update_date = str(dt_India.strftime('%Y-%m-%d %H:%M:%S'))
                connection_open_entry = db_util.connect_database()
                if connection_open_entry.is_connected():
                    demo_trade_entry_check = """SELECT DISTINCT dbdt.`symbol_name`, csema.ema_7 FROM `ant_cryptotradingbot`.`db_demo_trade` as dbdt
                        INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_data` as csd on dbdt.symbol_name = csd.symbol_name 
                        INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_ema_data` as csema on dbdt.symbol_name = csema.symbol_name 
                        WHERE ((dbdt.signal_side = 'BUY' and csema.ema_7 < csd.current_askPrice and csd.MACD_macd > 0  
                        and ((csd.MACD_dem < 0 and csd.MACD_dif > 0) or ((csema.ema_200 < csema.ema_7 and (csema.ema_200 > csema.ema_25 or csema.ema_200 > csema.ema_99)) or 
                        (csema.ema_7 > csema.ema_25 and ((csema.ema_7 < csema.ema_99 and  csema.ema_7 < csema.ema_200) or csema.ema_7 < csema.ema_200)))))
                        or (dbdt.signal_side = 'SELL' and csema.ema_7 > csd.current_bidPrice and csd.MACD_macd < 0 
                        and ((csd.MACD_dem > 0 and csd.MACD_dif < 0) or ((csema.ema_200 > csema.ema_7 and (csema.ema_200 > csema.ema_25 or csema.ema_200 > csema.ema_99)) or 
                        (csema.ema_7 > csema.ema_25 and ((csema.ema_7 < csema.ema_99 and csema.ema_7 < csema.ema_200) or csema.ema_7 < csema.ema_200))))))
                        and dbdt.`trade_id`={} and dbdt.`entry_date` is null and dbdt.`exit_date` is null;"""\
                        .format(trade_id)
                    demo_trade_list = db_util.queryExecution(connection_open_entry, demo_trade_entry_check, 'select')
                    symbol_info_open = exchange.fetch_ticker(symbol_name)['info']
                    current_price = round(float(symbol_info_open['askPrice']), price_prec)
                    if signal_side == 'SELL':
                        current_price = round(float(symbol_info_open['bidPrice']), price_prec)
                    current_percent = round(float((current_price - entry_price) / (entry_price / 100)), 2)
                    if signal_side == 'SELL':
                        current_percent = -1 * current_percent
                    print('=== Waiting === Symbol ::: {} , Signal ::: {} - {} , Entry price ::: {} , , Current price ::: {} , Current percent ::: {}% ===='
                                     .format(symbol_name, signal_type, signal_side, entry_price, current_price, current_percent))
                    if (len(demo_trade_list) > 0 or signal_type == 'TELEGRAM') and current_percent <= 1:
                        qty_per_usdt = round(float(1/current_price), 2)
                        exit_price = current_price + (current_price / 100)
                        if signal_side == 'SELL':
                            exit_price = current_price - (current_price / 100)
                        exit_price = round(float(exit_price), price_prec)
                        upd_qry = """UPDATE `ant_cryptotradingbot`.`db_demo_trade` SET `qty_per_usdt` = {}, `entry_price`={}, `entry_date`='{}', `exit_price`={}, `stop_price`={} 
                        WHERE `trade_id`={} and `entry_date` is null and `exit_price` is null and `exit_date` is null"""\
                            .format(qty_per_usdt, current_price, update_date, exit_price, exit_price, trade_id)  
                        is_updated = db_util.queryExecution(connection_open_entry, upd_qry, 'insert')
                        if is_updated:
                            insert_query = """INSERT `ant_cryptotradingbot`.`db_live_trade_signals` (`trade_id`, `trade_date`, `symbol_name`, `signal_type`, `signal_side`, 
                            `entry_price`, `exit_price`, `stop_price`)  
                            VALUES ({},'{}','{}','{}','{}',{},{},{});""" \
                                .format(trade_id, trade_date, symbol_name, signal_type, signal_side, current_price, exit_price, exit_price)
                            db_util.queryExecution(connection_open_entry, insert_query, 'insert')
                            if signal_type == 'TELEGRAM':
                                telegram_signal = 'LONG'
                                if signal_side == 'SELL':
                                    telegram_signal = 'SHORT'
                                insert_query = """UPDATE `ant_cryptotradingbot`.`db_telegram_trade_signals` SET `trade_id`={} WHERE `trade_date`='{}' and `symbol_name`='{}' and `signal_side`='{}' and trade_closed = False and is_tradeable = True;""" \
                                    .format(trade_id, trade_date, symbol_name, telegram_signal)
                                db_util.queryExecution(connection_open_entry, insert_query, 'insert')
                            print('=== Entry === Symbol ::: {} , Signal ::: {} - {} , Is_Inserted ::: {} ===='
                                             .format(symbol_name, signal_type, signal_side, is_updated))
                            check_open_exit(trade_id, trade_date, symbol_name, signal_type, signal_side, current_price, exit_price)
                            break
                    elif len(demo_trade_list) == 0 and i >= 15 and (current_percent <= -1 or current_percent >= 1):
                        upd_qry = """DELETE FROM `ant_cryptotradingbot`.`db_demo_trade` WHERE `trade_id`={} 
                        and `entry_date` is null and `exit_price` is null and `exit_date` is null"""\
                            .format(trade_id)  
                        is_updated = db_util.queryExecution(connection_open_entry, upd_qry, 'insert')
                        print('=== Deleted === Symbol ::: {} , Signal ::: {} - {} , Is_Deleted ::: {} ===='
                              .format(symbol_name, signal_type, signal_side, is_updated))
                        break
                    elif len(demo_trade_list) > 0 and i >= 15:
                        entry_price = round(float(demo_trade_list[0][1]), price_prec)
                        upd_qry = """UPDATE `ant_cryptotradingbot`.`db_demo_trade` SET `entry_price`={} 
                        WHERE `trade_date`='{}' and `symbol_name`='{}' and `entry_signal_type`='{}' 
                        and `signal_side`='{}' and `entry_date` is null and `exit_price` is null and `exit_date` is null""" \
                            .format(entry_price, trade_date, symbol_name, signal_type, signal_side)
                        db_util.queryExecution(connection_open_entry, upd_qry, 'insert')
                        i = -1
                    connection_open_entry.close()
            i = i + 1
            time.sleep(60)
        except Exception as ex:
            error_log = str(ex).replace('\'', '\'\'') + " - main :: line ::" \
                        + str(sys.exc_info()[2].tb_lineno)
            print('Error: - check_entry_order - {}'.format(error_log))
            print('Time sleep for : 5 sec......')
            time.sleep(5)
            continue


def check_open_exit(trade_id, trade_date, symbol_name, signal_type, signal_side, entry_price, exit_price):
    n = 0
    while True:
        try:
            connection_open_exit = db_util.connect_database()
            if connection_open_exit.is_connected():
                demo_trade_exit_query = """SELECT * FROM `ant_cryptotradingbot`.`db_demo_trade` where `trade_id`={}
                 and `entry_date` is not null and `exit_date` is null;"""\
                    .format(trade_id)
                demo_trade_list = db_util.queryExecution(connection_open_exit, demo_trade_exit_query, 'select')
                if len(demo_trade_list) == 0:
                    break
                isExit = False
                symbol_info_open = exchange.fetch_ticker(symbol_name)['info']
                price_prec = symbol_precision(symbol_info_open)
                current_price = round(float(symbol_info_open['bidPrice']), price_prec)
                if signal_side == 'SELL':
                    current_price = round(float(symbol_info_open['askPrice']), price_prec)
                entry_price = round(float(entry_price), price_prec)
                upd_qry = """UPDATE `ant_cryptotradingbot`.`crypto_symbols_data` SET `current_bidPrice` = {} WHERE `symbol_name`='{}'"""\
                    .format(current_price, symbol_name)  
                if signal_side == 'SELL':
                    upd_qry = """UPDATE `ant_cryptotradingbot`.`crypto_symbols_data` SET `current_askPrice` = {} WHERE `symbol_name`='{}'"""\
                        .format(current_price, symbol_name)  
                db_util.queryExecution(connection_open_exit, upd_qry, 'insert')
                exit_trade_list = None
                connection_open_exit_sp = db_util.connect_database()
                if connection_open_exit_sp.is_connected():
                    demo_trade_exit_query = """call `ant_cryptotradingbot`.`db_signal_query_exit`({}, '{}')""" \
                        .format(trade_id, symbol_name)
                    exit_trade_list = db_util.queryExecution(connection_open_exit_sp, demo_trade_exit_query, 'select')
                    connection_open_exit_sp.close()
                if len(exit_trade_list) > 0 and exit_trade_list is not None:
                    exit_price = round(float(exit_trade_list[0][6]), price_prec)
                    stop_price = round(float(exit_trade_list[0][7]), price_prec)
                    demo_trade_tradeable_query = """SELECT * FROM `ant_cryptotradingbot`.`db_live_trade_signals` 
                    where `trade_id`={} and `trade_closed` = False and `is_tradeable` = True;"""\
                        .format(trade_id)
                    demo_trade_tradeable = db_util.queryExecution(connection_open_exit, demo_trade_tradeable_query, 'select')
                    if len(demo_trade_tradeable) == 0 and ((current_price >= exit_price and signal_side == 'BUY') or (current_price <= exit_price and signal_side == 'SELL')):
                        exit_price = round(float(current_price + (current_price * 0.15 / 100)), price_prec)
                        stop_price = round(float(current_price - (current_price * 0.15 / 100)), price_prec)
                        if signal_side == 'SELL':
                            exit_price = round(float(current_price - (current_price * 0.15 / 100)), price_prec)
                            stop_price = round(float(current_price + (current_price * 0.15 / 100)), price_prec)
                    upd_qry = """UPDATE `ant_cryptotradingbot`.`db_demo_trade` SET `exit_price` = {} WHERE `trade_id`={} 
                     and `exit_date` is null;"""\
                        .format(exit_price, trade_id)
                    db_util.queryExecution(connection_open_exit, upd_qry, 'update')
                    connection_open_exit.close()
                    prev_stop_price = stop_price
                    isStopLossActive = False
                    while isExit == False:
                        try:
                            connection_open_exit_lp = db_util.connect_database()
                            if connection_open_exit_lp.is_connected():
                                symbol_info_open_new = exchange.fetch_ticker(symbol_name)['info']
                                current_price = round(float(symbol_info_open_new['bidPrice']), price_prec)
                                current_percent = round(float((current_price - entry_price) / (entry_price / 100)), 2)
                                target_percent = round(float((exit_price - entry_price) / (entry_price / 100)), 2)
                                if signal_side == 'SELL':
                                    current_price = round(float(symbol_info_open_new['askPrice']), price_prec)
                                    current_percent = -1 * current_percent
                                    target_percent = -1 * target_percent
                                if target_percent > 1 and current_percent > (target_percent / 2):
                                    stop_price = round(float(entry_price + ((entry_price * (target_percent / 3)) / 100)), price_prec)
                                    if signal_side == 'SELL':
                                        stop_price = round(float(entry_price - ((entry_price * (target_percent / 3)) / 100)), price_prec)
                                stop_current_percent = round(float((stop_price - entry_price) / (entry_price / 100)), 2)
                                if signal_side == 'SELL':
                                    stop_current_percent = -1 * stop_current_percent
                                if stop_price != prev_stop_price:
                                    upd_qry = """UPDATE `ant_cryptotradingbot`.`db_demo_trade` SET `stop_price` = {} WHERE `trade_id`={} 
                                     and `exit_date` is null;"""\
                                        .format(stop_price, trade_id)
                                    db_util.queryExecution(connection_open_exit_lp, upd_qry, 'update')
                                    stop_price = prev_stop_price
                                upd_qry = """UPDATE `ant_cryptotradingbot`.`crypto_symbols_data` SET `current_bidPrice` = {} WHERE `symbol_name`='{}'"""\
                                    .format(current_price, symbol_name)
                                if signal_side == 'SELL':
                                    upd_qry = """UPDATE `ant_cryptotradingbot`.`crypto_symbols_data` SET `current_askPrice` = {} WHERE `symbol_name`='{}'"""\
                                        .format(current_price, symbol_name)
                                db_util.queryExecution(connection_open_exit_lp, upd_qry, 'insert')
                                query_sp = """call `ant_cryptotradingbot`.`db_signal_query_exit`({}, '{}')""" \
                                    .format(trade_id, symbol_name)
                                symbols_list = db_util.queryExecution(connection_open_exit_lp, query_sp, 'select')
                                connection_open_exit_lp.close()
                                exit_price = round(float(symbols_list[0][6]), price_prec)
                                stop_price = round(float(symbols_list[0][7]), price_prec)
                                if ((signal_side == 'BUY' and current_price > stop_price and entry_price < stop_price) or (signal_side == 'SELL' and current_price < stop_price and entry_price > stop_price)):
                                    isStopLossActive = True
                                print('Symbol ::: {} , Signal ::: {} - {} , entry_price ::: {} , exit_price ::: {} , stop_price ::: {} , current_price ::: {} , current_percent ::: {} , target_percent ::: {} , stop_percent ::: {}'
                                      .format(symbol_name, signal_type, signal_side, entry_price, exit_price, stop_price, current_price, current_percent, target_percent, stop_current_percent))
                                if (((signal_side == 'BUY' and (current_price >= exit_price or (current_price <= stop_price and entry_price < stop_price and isStopLossActive)))
                                    or (signal_side == 'SELL' and (current_price <= exit_price or (current_price >= stop_price and entry_price > stop_price and isStopLossActive))))) and current_percent > 0:
                                    dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
                                    update_date = str(dt_India.strftime('%Y-%m-%d %H:%M:%S'))
                                    exit_price = current_price
                                    pnl = exit_price - entry_price
                                    if signal_side == 'SELL':
                                        pnl = entry_price - exit_price
                                    qty_per_usdt = round(float(1/entry_price), 2)
                                    pnl_per_usdt = round(float(qty_per_usdt * pnl), 4)
                                    connection_open_exit_lp_new = db_util.connect_database()
                                    if connection_open_exit_lp_new.is_connected():
                                        update_query = """UPDATE `ant_cryptotradingbot`.`db_demo_trade` 
                                        set `exit_price`={}, `pnl_per_usdt`={},`exit_signal_type`='{}',`exit_date`='{}'  
                                            where `trade_id`= {} and `exit_date` is null;""" \
                                                .format(exit_price, pnl_per_usdt, signal_type, update_date, trade_id)
                                        db_util.queryExecution(connection_open_exit_lp_new, update_query, 'update')
                                        update_query = """UPDATE `ant_cryptotradingbot`.`db_live_trade_signals` 
                                        set `exit_price` = {}, `trade_closed` = True
                                        where `trade_id`='{}' and `trade_closed` = False;""" \
                                            .format(exit_price, trade_id)
                                        is_updated = db_util.queryExecution(connection_open_exit_lp_new, update_query, 'update')
                                        if is_updated:
                                            isExit = True
                                            print("""=== Exit ===  Symbol ::: {} , Signal ::: {} - {} , Entry_price ::: {} ,
                                                   Exit_Price ::: {} , Qty ::: {} , PnL ::: {} , Is_Updated ::: {}  ===="""
                                                  .format(symbol_name, signal_type, signal_side, entry_price, exit_price,
                                                          qty_per_usdt, pnl_per_usdt, is_updated))
                                    connection_open_exit_lp_new.close()
                                time.sleep(60)
                        except:
                            continue

                    if isExit:
                        break
                else:
                    break
        except Exception as ex:
            error_log = str(ex).replace('\'', '\'\'') + " - main :: line ::" \
                        + str(sys.exc_info()[2].tb_lineno)
            print('Error: - check_exit_order - {}'.format(error_log))
            print('Time sleep for : 5 sec......')
            time.sleep(5)
            check_open_exit(trade_id, trade_date, symbol_name, signal_type, signal_side, entry_price, exit_price)


if __name__ == "__main__":
    dt_today = datetime.today()  # Local time
    dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
    start_date = str(datetime.strftime(dt_India, "%d%m%Y"))
    log_filename = "DB_Signal_Query_{}.log".format(start_date)
    s_interval = '15m'  # valid intervals - 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
    RSI_PERIOD = 6
    IS_FIRST = True
    OPEN_EXIT = False
    print('Signal_Query started...')
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
            if connection.is_connected() and IS_FIRST:
                upd_qry = """DELETE FROM `ant_cryptotradingbot`.`db_demo_trade` WHERE `entry_date` is null and `exit_price` is null and `exit_date` is null;"""
                db_util.queryExecution(connection, upd_qry, 'insert')
                upd_qry = """UPDATE `ant_cryptotradingbot`.`db_telegram_trade_signals` SET `is_tradeable` = False where `is_tradeable` = True and `trade_closed` = False"""
                db_util.queryExecution(connection, upd_qry, 'insert')
                IS_FIRST = False
                connection.close()
                #print('Time sleep for : 15 minutes......')
                #time.sleep(900)
            
            connection_open_exit_lts = db_util.connect_database()
            if connection_open_exit_lts.is_connected():
                update_query = """UPDATE `ant_cryptotradingbot`.`db_live_trade_signals` as dblts 
                                INNER JOIN `ant_cryptotradingbot`.`db_demo_trade` as dbdt on dblts.trade_id = dbdt.trade_id 
                                SET dblts.is_tradeable = False 
                                WHERE ((dbdt.exit_date is null AND ADDTIME(dbdt.entry_date, "10000") < ADDTIME(CONCAT(CURDATE(), ' ', CURRENT_TIME()), "43000")) OR dbdt.exit_date is not null);"""
                db_util.queryExecution(connection_open_exit_lts, update_query, 'update')
                connection_open_exit_lts.close()
                
            connection = db_util.connect_database()
            if connection.is_connected():
                if OPEN_EXIT == False:
                    demo_trade_open_query = "SELECT `trade_id`,`trade_date`,`symbol_name`,`entry_signal_type`,`signal_side`,`entry_price`,`entry_date`,`exit_price` FROM `ant_cryptotradingbot`.`db_demo_trade` where `exit_date` is null;"
                    demo_trade_list = db_util.queryExecution(connection, demo_trade_open_query, 'select')
                    connection.close()
                    for demo_trade in demo_trade_list:
                        if demo_trade[6] is None:
                            n = threading.Thread(target=check_open_entry, args=(demo_trade[0], demo_trade[1], demo_trade[2], demo_trade[3], demo_trade[4], demo_trade[5],))
                            n.start()
                        else:
                            x = threading.Thread(target=check_open_exit, args=(demo_trade[0], demo_trade[1], demo_trade[2], demo_trade[3], demo_trade[4], demo_trade[5], demo_trade[7],))
                            x.start()
                    OPEN_EXIT = True

            connection_sp = db_util.connect_database()
            if connection_sp.is_connected():
                query = """call `ant_cryptotradingbot`.`db_signal_query_entry`(null)"""
                symbols_list = db_util.queryExecution(connection_sp, query, 'select')
                connection_sp.close()
                dt_today = datetime.today()  # Local time
                dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
                trade_date = str(dt_India.strftime('%Y-%m-%d'))
                if len(symbols_list) > 0:
                    for symbol in symbols_list:
                        try:
                            symbol_name = symbol[0]
                            entry_price = symbol[2]
                            signal_type = symbol[3]
                            signal_side = symbol[4]
                            update_date = str(symbol[6].strftime('%Y-%m-%d %H:%M:%S'))
                            is_entry_point = True
                            is_exit_point = False
                            ss, rr = srl.main(symbol_name)
                            symbol_info = exchange.fetch_ticker(symbol_name)['info']
                            cur_ask_price = round(float(symbol_info['askPrice']), 8)
                            ss_trim = ss[-2:]
                            rr_trim = rr[-2:]
                            for sup in ss_trim:
                                if sup[1] > cur_ask_price:
                                    is_entry_point = False
                                    is_exit_point = True
                            if is_entry_point and not(is_exit_point):
                                for res in rr_trim:
                                    if res[1] > cur_ask_price:
                                        is_entry_point = True
                                        is_exit_point = False
                                    else:
                                        is_entry_point = False
                                        is_exit_point = True

                            connection = db_util.connect_database()
                            if connection.is_connected():
                                demo_trade_query = """SELECT `signal_side`, `entry_price` FROM `ant_cryptotradingbot`.`db_demo_trade` where `symbol_name` = '{}' and `exit_date` is null;""" \
                                    .format(symbol_name)
                                demo_trade = db_util.queryExecution(connection, demo_trade_query, 'select')
                                connection.close()
                                if len(demo_trade) == 0:
                                    last_rsi = 100
                                    try:
                                        symbol_df = get_data_frame(symbol_name)
                                        if symbol_df is not None:
                                            closes = symbol_df['close'].tolist()
                                            icloses = [float(c) for c in closes]
                                            np_closes = np.array(icloses)
                                            rsi = talib.RSI(np_closes, RSI_PERIOD)
                                            last_rsi = rsi[-1]
                                    except:
                                        continue
                                    if ((last_rsi <= 60 or is_entry_point) and signal_side == 'BUY') or ((last_rsi < 90 or is_exit_point) and signal_side == 'SELL'):
                                        connection = db_util.connect_database()
                                        if connection.is_connected():
                                            symbol_info_open = exchange.fetch_ticker(symbol_name)['info']
                                            price_prec = symbol_precision(symbol_info_open)
                                            entry_price = round(float(entry_price), price_prec)
                                            demo_trade_query_id = """SELECT `trade_id` FROM `ant_cryptotradingbot`.`db_demo_trade` order by `trade_id` desc limit 1;"""
                                            demo_trade_id = db_util.queryExecution(connection, demo_trade_query_id, 'select')
                                            trade_id = 1
                                            if len(demo_trade_id) > 0:
                                                trade_id = int(demo_trade_id[0][0])+1
                                            insert_query = """INSERT `ant_cryptotradingbot`.`db_demo_trade` (`trade_id`, `trade_date`, `symbol_name`, `entry_signal_type`, `signal_side`, 
                                            `entry_price`)  
                                            VALUES ({},'{}','{}','{}','{}',{});""" \
                                                .format(trade_id, trade_date, symbol_name, signal_type, signal_side, entry_price)
                                            is_insert = db_util.queryExecution(connection, insert_query, 'insert')
                                            connection.close()
                                            nw = threading.Thread(target=check_open_entry, args=(trade_id, trade_date, symbol_name, signal_type, signal_side, entry_price,))
                                            nw.start()
                        except:
                            continue

            print('Time sleep for : 5 minutes......')
            time.sleep(298)
        except Exception as ex:
            error_log = str(ex).replace('\'', '\'\'') + " - main :: line ::" \
                        + str(sys.exc_info()[2].tb_lineno)
            print('Error: - Main error - {}'.format(error_log))
            print('Time sleep for : 1 min......')
            time.sleep(60)
            continue
