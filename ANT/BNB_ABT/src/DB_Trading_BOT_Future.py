import pandas as pd
import numpy as np
import talib
from binance.client import Client
import ccxt
import threading
from utils import config, db_util
from random import randint
from datetime import datetime #, timedelta
#from utils.logger import logger
import time, sys, os, gc, math
from pytz import timezone
from utils import supRes_level as srl
from data import DB_Signal_Query as dbsq


def exchange_init():
    bin_exchange = ccxt.binance()
    return bin_exchange


def getBalance(symbol):
    info = client.futures_account_balance()
    usdt_balance = 0.00
    for check_balance in info:
        if check_balance["asset"] == "USDT":
            usdt_balance = check_balance["balance"]
            print(usdt_balance)  # Prints 0.0000
    return round(float(usdt_balance), 2)


def get_data_frame(symbol):
    try:
        # request historical candle (or klines) data using timestamp from above. interval either every min, hr, day
        # starttime = '30 minutes ago UTC' for last 30 mins time
        # e.g., client.get_historical_klines(symbol='ETHBUSD', '1m', starttime)
        # starttime = '1 Nov, 2021', '1 Dec, 2021' for last month of 2017
        # e.g., client.get_historical_klines(symbol='BTCBUSD', '1h', '1 Nov, 2021', '1 Dec, 2021')
        starttime = '1 day ago UTC'
        interval = s_interval
        bars = client.get_historical_klines(symbol, interval, starttime)
        # pprint.pprint(bars)

        for line in bars:
            del line[5:]

        df = pd.DataFrame(bars, columns=['date', 'open', 'high', 'low', 'close'])
        return df
    except:
        pass
    finally:
        gc.collect()


def trade_logic(select_query_result, nthread):
    symbol = ''
    order_type = ''
    try:
        exchange = exchange_init()
        print(select_query_result)
        order_id = 0
        stop_orderID = 0
        if len(select_query_result) > 0:
            symbol = select_query_result[0][0]
            #client.futures_cancel_all_open_orders(symbol=replace_future_symbolname(symbol))
            signal_type = select_query_result[0][1]
            ordered_qty = float(select_query_result[0][2])
            buy_price = 0
            buy_orderID = select_query_result[0][5]
            sell_orderID = select_query_result[0][6]
            stop_orderID = select_query_result[0][7]
            if select_query_result[0][3] is not None:
                buy_price = float(select_query_result[0][3])
                order_type = 'BUY'
                order_id = sell_orderID
            if buy_price == 0 and select_query_result[0][4] is not None:
                buy_price = float(select_query_result[0][4])
                order_type = 'SELL'
                order_id = buy_orderID
            in_position = True
        else:
            in_position = False
            buy_price = 0.00
            order_id = 0
            ordered_qty = 0
            signal_type = ''
        quantity = ordered_qty

        if not(in_position):
            connection = db_util.connect_database()
            if connection.is_connected():
                query = """SELECT dblts.symbol_name, dblts.signal_type, dblts.signal_side, dblts.entry_price, dbdt.exit_price, dbdt.stop_price, dbdt.qty_per_usdt, dblts.trade_id FROM `ant_cryptotradingbot`.`db_live_trade_signals` as dblts
                    INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_data` as csd on csd.symbol_name = dblts.symbol_name 
                    INNER JOIN `ant_cryptotradingbot`.`db_demo_trade` as dbdt on dblts.trade_id = dbdt.trade_id 
                    LEFT OUTER JOIN `ant_cryptotradingbot`.`current_buy_order_report_future` as cborf on dblts.symbol_name = cborf.symbol_name and cborf.signal_type = concat(dblts.signal_type, ' - ', dblts.signal_side) and cborf.username = '{}'
                    WHERE dblts.trade_closed=False and dblts.is_tradeable=True and csd.`is_Future_Trade` = True and cborf.symbol_name is null and (((csd.current_askPrice <= dblts.entry_price or csd.price_breakOut = 1) and dblts.signal_side = 'BUY') or ((csd.current_bidPrice >= dblts.entry_price or csd.price_breakOut = -1) and dblts.signal_side = 'SELL'));"""\
                    .format(username)
                symbols_list = db_util.queryExecution(connection, query, 'select')
                if len(symbols_list) > 0:
                    # symbols_count = len(symbols_list)
                    # selected_symbol = symbols_list[randint(0, symbols_count-1)]
                    for selected_symbol in symbols_list:
                        symbol = selected_symbol[0]
                        signal_type = selected_symbol[1] + ' - ' + selected_symbol[2]
                        order_type = selected_symbol[2]
                        entry_price = selected_symbol[3]
                        exit_price = selected_symbol[4]
                        stop_price = selected_symbol[5]
                        quantity = selected_symbol[6] * 100
                        info = None
                        try:
                            info = client.futures_symbol_ticker(symbol=replace_future_symbolname(symbol))
                            print(info)
                        except Exception as ex:
                            error_log = str(ex).replace('\'', '\'\'') + " - trade_logic :: line ::" \
                                        + str(sys.exc_info()[2].tb_lineno)
                            print(symbol + ' - ' + error_log)
                            query_1 = """UPDATE `ant_cryptotradingbot`.`crypto_symbols_data` SET `is_Future_Trade`={} 
                            WHERE `symbol_name`='{}';""" \
                                .format(0, symbol)
                            query_result = db_util.queryExecution(connection, query_1, 'update')
                        if info is not None:
                            trade_id = selected_symbol[7]
                            symbol_df = get_data_frame(symbol)
                            closes = symbol_df['close'].tolist()
                            icloses = [float(c) for c in closes]
                            np_closes = np.array(icloses)
                            rsi = talib.RSI(np_closes, RSI_PERIOD)
                            last_rsi = round(float(rsi[-1]), 2)
                            if replace_future_symbolname_price(symbol, entry_price) == float(float(entry_price) * 1000):
                                quantity = quantity / 1000
                                entry_price = replace_future_symbolname_price(symbol, entry_price)
                                exit_price = replace_future_symbolname_price(symbol, exit_price)
                                stop_price = replace_future_symbolname_price(symbol, stop_price)
                                print('quantity : {}'.format(str(quantity)))
                            if ((last_rsi <= 80 and order_type == 'BUY') or (last_rsi >= 20 and order_type == 'SELL')) and not(in_position): # and is_entry_point
                                in_position, exit_price, ordered_qty, order_id, signal_type = buy_or_sell(symbol, order_type, signal_type, in_position, nthread, qty=quantity, open_price=entry_price, close_price=exit_price, stop_price=stop_price, trade_id=trade_id)
                                if in_position:
                                    connection.close()
                                    break
                            else:
                                print('Symbol :: {} - OrderType :: {} - Last RSI :: {}'.format(symbol, order_type, last_rsi))
                        print('Time sleep for : {} seconds.....'.format(str(10)))
                        time.sleep(10)
                    connection.close()
                else:
                    connection.close()
                    return

        if in_position:
            target_percent = 1
            if order_type == 'SELL':
                target_percent = -1 * target_percent
            f_current_price = 0.00
            current_percent = 0
            target_price = 0
            stop_price = 0
            prev_order_price = 0
            orderStatus = 'NEW'
            while in_position:
                dt_today = datetime.today()  # Local time
                dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
                current_date = str(datetime.strftime(dt_India, "%d%m%Y"))
                if start_date != current_date:
                    break
                connection = db_util.connect_database()
                if connection.is_connected():
                    query = """call `ant_cryptotradingbot`.`db_future_trade_exit`('{}', '{}');"""\
                        .format(symbol, username)
                    symbols_list = db_util.queryExecution(connection, query, 'select')
                    symbol_info = exchange.fetch_ticker(symbol)['info']
                    price_prec = dbsq.symbol_precision(symbol_info)
                    f_current_price = round(float(symbol_info['bidPrice']), price_prec)
                    if order_type == 'SELL':
                        f_current_price = round(float(symbol_info['askPrice']), price_prec)
                    buy_price = round(float(buy_price), price_prec)
                    if order_id > 0:
                        closed_order_type = 'SELL'
                        if order_type == 'SELL':
                            closed_order_type = 'BUY'
                        sell_order = client.futures_get_order(symbol=replace_future_symbolname(symbol), side=closed_order_type, orderId=int(order_id))
                        prev_order_price = round(float(sell_order['avgPrice']), price_prec)
                        orderStatus = sell_order['status']
                    if stop_orderID > 0:
                        closed_order_type = 'SELL'
                        if order_type == 'SELL':
                            closed_order_type = 'BUY'
                        sell_order = client.futures_get_order(symbol=replace_future_symbolname(symbol), side=closed_order_type, orderId=int(stop_orderID))
                        prev_order_price = round(float(sell_order['avgPrice']), price_prec)
                        orderStatus = sell_order['status']

                    priceBreakOut = False
                    if len(symbols_list) == 1:
                        ordered_qty = symbols_list[0][12] * 100
                        buy_price = round(float(symbols_list[0][4]), price_prec)
                        target_price = round(float(symbols_list[0][6]), price_prec)
                        stop_price = round(float(symbols_list[0][7]), price_prec)
                        if (int(symbols_list[0][16]) < 0 and  order_type == 'BUY' and f_current_price > round(float(symbols_list[0][4]), price_prec)) or (int(symbols_list[0][16]) > 0 and  order_type == 'SELL' and f_current_price < round(float(symbols_list[0][4]), price_prec)):
                            priceBreakOut = True

                    if len(symbols_list) == 0 or priceBreakOut:
                        target_price = round(float(f_current_price + (f_current_price * 0.2 / 100)), price_prec)
                        stop_price = round(float(f_current_price - (f_current_price * 0.2 / 100)), price_prec)
                        if order_type == 'SELL':
                            target_price = round(float(f_current_price - (f_current_price * 0.2 / 100)), price_prec)
                            stop_price = round(float(f_current_price + (f_current_price * 0.2 / 100)), price_prec)

                    current_percent = round(float((f_current_price - buy_price) / (buy_price / 100)), 2)
                    target_percent = round(float((target_price - buy_price) / (buy_price / 100)), 2)
                    if order_type == 'SELL':
                        current_percent = round(float((buy_price - f_current_price) / (buy_price / 100)), 2)
                        target_percent = round(float((buy_price - target_price) / (buy_price / 100)), 2)

                    if prev_order_price != target_price and orderStatus != 'FILLED':
                        order_id = 0

                    dt_today = datetime.today()  # Local time
                    dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
                    trade_date = str(dt_India.strftime('%Y-%m-%d'))
                    if replace_future_symbolname_price(symbol, buy_price) == float(float(buy_price) * 1000):
                        ordered_qty = ordered_qty / 1000
                        buy_price = replace_future_symbolname_price(symbol, buy_price)
                        target_price = replace_future_symbolname_price(symbol, target_price)
                        stop_price = replace_future_symbolname_price(symbol, stop_price)
                    print('{} :::: {} :: {} - {} ==::== {} ::: qty : {} :: avg price : {} -- current price : {} ({} %) - Target : {} ({} %)'\
                          .format(order_type, trade_date, username, nthread, symbol, ordered_qty, buy_price, f_current_price, current_percent,
                                  target_price, target_percent))
                    in_position, prev_order_price, ordered_qty, order_id, signal_type = buy_or_sell(symbol, order_type, signal_type, in_position, nthread, ordered_qty, order_id=order_id, stop_id=stop_orderID, open_price= buy_price, close_price= target_price, stop_price = stop_price)

                    if trade_type == 'live':
                        '''Live Trade'''
                        currnt_busd_bal = float(getBalance('USDT'))
                    else:
                        '''Mock Trade'''
                        with open(busd_bal_txt, 'r') as busd:
                            currnt_busd_bal = float(busd.readline())
                            busd.close()
                    connection.close()
                    time.sleep(60)
            gc.collect()
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - trade_logic :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print(symbol + ' - ' + error_log)
    finally:
        gc.collect()


def buy_or_sell(symbol, buy_sell, signal_type, in_position_entry, order_seq, qty=0, order_id=0, stop_id=0, open_price=0, close_price=0, stop_price=0, trade_id=0):
    exchange = exchange_init()
    symbol_info = exchange.fetch_ticker(symbol)['info']
    price_prec = dbsq.symbol_precision(symbol_info) + 3
    cur_price = round(float(symbol_info['askPrice']), price_prec)
    ordered_qty = 0
    is_ordered = False
    try:
        log = ''
        dt_today = datetime.today()  # Local time
        dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
        trade_date = str(dt_India.strftime('%Y-%m-%d %H:%M:%S'))
        buy_order = {'commisionPrice': 0.0000}
        sell_order = {'commisionPrice': 0.0000}
        buy_status = ''
        getting_price = 'bidPrice'
        if buy_sell == 'SELL':
            getting_price = 'askPrice'
        if trade_type == 'live':
            '''Live Trade'''
            currnt_busd_bal = float(getBalance('USDT'))
        else:
            '''Mock Trade'''
            with open(busd_bal_txt, 'r') as busd:
                currnt_busd_bal = float(busd.readline())
                busd.close()

        if currnt_busd_bal > BUY_AMT and not(in_position_entry):
            symbol_info = exchange.fetch_ticker(symbol)['info']
            cur_price = round(float(symbol_info[getting_price]), price_prec)
            actual_open_price = round(float(open_price), price_prec)
            cur_bid_price = round(float(open_price), price_prec)
            connection = db_util.connect_database()
            if connection.is_connected():
                select_query = """SELECT `order_seq_id`,`symbol_name`,`signal_type`,`order_quantity`,`buy_price`,`order_date` FROM `ant_cryptotradingbot`.`current_buy_order_report_future` WHERE `username`='{}' and `symbol_name` = '{}';""" \
                    .format(username, symbol)
                if buy_sell == 'SELL':
                    select_query = """SELECT `order_seq_id`,`symbol_name`,`signal_type`,`order_quantity`,`sell_price`,`order_date` FROM `ant_cryptotradingbot`.`current_buy_order_report_future` WHERE `username`='{}' and `symbol_name` = '{}';""" \
                        .format(username, symbol)
                select_query_result = db_util.queryExecution(connection, select_query, 'select')
                if len(select_query_result) > 0:
                    return False, 0, 0, 0, signal_type
                elif len(select_query_result) == 0:
                    query_1 = """INSERT INTO `ant_cryptotradingbot`.`current_buy_order_report_future` (`order_seq_id`,`symbol_name`,`signal_type`,
                    `order_quantity`,`buy_price`,`current_price`,`profit_percent`,`target_price`,`username`,`order_date`,`trade_id`) 
                    VALUES({},'{}','{}',{},{},null,null,null,'{}','{}',{});""" \
                        .format(order_seq, symbol, signal_type, qty, actual_open_price, username, trade_date,trade_id)
                    if buy_sell == 'SELL':
                        query_1 = """INSERT INTO `ant_cryptotradingbot`.`current_buy_order_report_future` (`order_seq_id`,`symbol_name`,`signal_type`,
                        `order_quantity`,`sell_price`,`current_price`,`profit_percent`,`target_price`,`username`,`order_date`,`trade_id`) 
                        VALUES({},'{}','{}',{},{},null,null,null,'{}','{}',{});""" \
                            .format(order_seq, symbol, signal_type, qty, actual_open_price, username, trade_date,trade_id)

                    query_result = db_util.queryExecution(connection, query_1, 'insert')

                    if trade_type == 'live':
                        '''Live Trade'''
                        orderId = order_id
                        while int(orderId) == 0:
                            try:
                                actual_open_price = round(float(actual_open_price), price_prec)
                                print("{} - {} :: {} :: Quantity:{} , Symbol:{} , price:{}".format(username, order_seq, buy_sell, qty,replace_future_symbolname(symbol),actual_open_price))
                                buy_order = client.futures_create_order(symbol=replace_future_symbolname(symbol), side=buy_sell, type='LIMIT',
                                                                        quantity=qty, price=actual_open_price, timeinforce='GTC')
                                time.sleep(2)
                                orderId = int(buy_order['orderId'])
                                orderStatus = buy_order['status']
                                actual_open_price = round(float(buy_order['avgPrice']), price_prec)
                                if actual_open_price <= 0:
                                    actual_open_price = round(float(buy_order['price']), price_prec)
                            except Exception as ex:
                                error_log = str(ex).replace('\'', '\'\'') + " - trade_logic :: line ::" \
                                            + str(sys.exc_info()[2].tb_lineno)
                                time.sleep(2)
                                if str(ex).endswith('Precision is over the maximum defined for this asset.')and price_prec > 0:
                                    print(replace_future_symbolname(symbol) + ' - ' + str(actual_open_price) + ' - ' + str(price_prec) + ' - ' + error_log)
                                    price_prec = price_prec - 1
                                elif str(ex).endswith('Margin is insufficient.'):
                                    print(replace_future_symbolname(symbol) + ' - ' + str(actual_open_price) + ' - ' + str(price_prec) + ' - ' + error_log)
                                    qty = int(qty / 1000)
                                elif  str(ex).endswith('Price not increased by tick size.') or str(ex).endswith('Invalid symbol.') or str(ex).endswith('Invalid symbol status for opening position.') or (str(ex).endswith('Precision is over the maximum defined for this asset.') and price_prec <= 0):
                                    query_invalid = """UPDATE `ant_cryptotradingbot`.`crypto_symbols_data` SET `is_Future_Trade`={} 
                                    WHERE `symbol_name`='{}';""" \
                                        .format(0, symbol)
                                    db_util.queryExecution(connection, query_invalid, 'update')
                                    query_1 = """DELETE FROM `ant_cryptotradingbot`.`current_buy_order_report_future` WHERE `order_seq_id`={} and `symbol_name`='{}'
                                    and `username`='{}' and `order_date`='{}';""" \
                                    .format(order_seq, symbol, username, trade_date)
                                    query_result = db_util.queryExecution(connection, query_1, 'update')
                                    return False, 0, 0, 0, signal_type
                                else:
                                    print(replace_future_symbolname(symbol) + ' - ' + error_log)
                                continue
                    else:
                        orderId = order_id
                        orderStatus = 'NEW'
                    query_1 = """UPDATE `ant_cryptotradingbot`.`current_buy_order_report_future` SET `buy_orderID`={} 
                    WHERE `symbol_name`='{}' and `username`='{}';""" \
                        .format(orderId, symbol, username, actual_open_price, symbol, trade_id)
                    if buy_sell == 'SELL':
                        query_1 = """UPDATE `ant_cryptotradingbot`.`current_buy_order_report_future` SET `sell_orderID`={} 
                        WHERE `symbol_name`='{}' and `username`='{}';""" \
                            .format(orderId, symbol, username, actual_open_price, symbol, trade_id)

                    query_result = db_util.queryExecution(connection, query_1, 'update')
                    query_2 = """UPDATE `ant_cryptotradingbot`.`db_demo_trade` SET `entry_price`={} 
                    WHERE (`symbol_name`='{}' or `trade_id`={}) and `entry_date` is not null and `exit_date` is null;""" \
                        .format(actual_open_price, symbol, trade_id)
                    query_result_new = db_util.queryExecution(connection, query_2, 'update')
                    waitingTimes = 0
                    while orderStatus != 'FILLED' and orderStatus != 'CANCELLED':
                        dt_today = datetime.today()  # Local time
                        dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
                        current_date = str(datetime.strftime(dt_India, "%d%m%Y"))
                        query_1 = """SELECT count(symbol_name) FROM `ant_cryptotradingbot`.`db_live_trade_signals` WHERE trade_closed=False 
                            AND is_tradeable = True AND symbol_name='{}';"""\
                            .format(symbol)
                        sel_query_result = db_util.queryExecution(connection, query_1, 'select')
                        if (orderStatus == 'NEW') and (start_date != current_date or len(sel_query_result) == 0 or waitingTimes > 15):
                            cancel_order = client.futures_cancel_order(symbol=replace_future_symbolname(symbol), orderId=orderId)
                            query_1 = """DELETE FROM `ant_cryptotradingbot`.`current_buy_order_report_future` 
                            WHERE `symbol_name`='{}' and `signal_type`='{}' and `username`='{}' and `order_quantity`='{}';"""\
                                .format(symbol, signal_type, username, qty)
                            db_util.queryExecution(connection, query_1, 'update')
                            print("{} - {} ==::== {} is cancelled {} === qty: {} ;; price: {} - cancel :: {}"
                                  .format(username, order_seq, replace_future_symbolname(symbol), buy_sell, qty, actual_open_price, cancel_order))
                            orderStatus = 'CANCELED'
                            return False, 0, 0, 0, signal_type
                        print("{} - {} ==::== {} is waiting for {} === qty: {} ;; price: {}"
                              .format(username, order_seq, replace_future_symbolname(symbol), buy_sell, qty, actual_open_price))
                        time.sleep(60)
                        waitingTimes = waitingTimes + 1
                        buy_order = client.futures_get_order(symbol=replace_future_symbolname(symbol), orderId=orderId)
                        orderStatus = buy_order['status']

                    buy_order = client.futures_get_order(symbol=replace_future_symbolname(symbol), orderId=orderId)
                    buy_status = buy_order['status']
                    if buy_status == 'FILLED':
                        # if 'fills' in buy_order:
                            # for buy_order_fills in buy_order['fills']:
                                # buy_order['commisionPrice'] += round(float(buy_order_fills['commission']), 8)
                        ordered_qty = int(float(buy_order['executedQty']))
                        actual_open_price = round(float(buy_order['avgPrice']), price_prec)
                        is_ordered = True
                else:
                    '''Mock Trade'''
                    ordered_qty = float(qty)
                    buy_order = {'cummulativeQuoteQty': float(ordered_qty * cur_price),
                                 'commisionPrice': 0.0000,
                                 'status': 'FILLED'}
                    buy_status = buy_order['status']
                    currnt_busd_bal = round(float(currnt_busd_bal - buy_order['cummulativeQuoteQty']), 2)
                    with open(busd_bal_txt, 'w') as busd:
                        busd.write(str(currnt_busd_bal))
                        busd.close()
                    is_ordered = True

                if buy_status != 'FILLED':
                    query_1 = """DELETE FROM `ant_cryptotradingbot`.`current_buy_order_report_future` WHERE `order_seq_id`={} and `symbol_name`='{}' and `signal_type`='{}'
                                            and `order_quantity`={} and `buy_price`={} and `username`='{}' and `order_date`='{}';""" \
                    .format(order_seq, symbol, signal_type, qty, cur_bid_price, username, trade_date)
                    if buy_sell == 'SELL':
                        query_1 = """DELETE FROM `ant_cryptotradingbot`.`current_buy_order_report_future` WHERE `order_seq_id`={} and `symbol_name`='{}' and `signal_type`='{}'
                                        and `order_quantity`={} and `sell_price`={} and `username`='{}' and `order_date`='{}';""" \
                        .format(order_seq, symbol, signal_type, qty, cur_bid_price, username, trade_date)
                    query_result = db_util.queryExecution(connection, query_1, 'insert')
            connection.close()

            if is_ordered:
                connection = db_util.connect_database()
                if connection.is_connected():
                    dt_today = datetime.today()  # Local time
                    dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
                    trade_date = str(dt_India.strftime('%Y-%m-%d %H:%M:%S'))
                    select_query = """SELECT count(`username`) from `ant_cryptotradingbot`.`order_report_future` WHERE `username`='{}';"""\
                        .format(username)
                    select_query_result = db_util.queryExecution(connection, select_query, 'select')
                    orderSeqId = int(select_query_result[0][0])+1
                    buy_amount = round(float(ordered_qty) * float(actual_open_price), price_prec)
                    buy_order['commisionPrice'] = (buy_amount / 20) / 100
                    query = """INSERT INTO `ant_cryptotradingbot`.`order_report_future` (`order_seq_id`,`symbol_name`,`signal_type`,`order_quantity`,`buy_price`,
                    `buy_amount`,`sell_price`,`sell_amount`,`profit_amount`,`profit_percent`,`username`,`order_date`,`update_date`,`commission_price`) 
                    VALUES ({},'{}','{}',{},{},{},null,null,null,null,'{}','{}',null, {});"""\
                                .format(orderSeqId, symbol, signal_type, ordered_qty, actual_open_price,
                                        buy_amount, username, trade_date, buy_order['commisionPrice'])
                    if buy_sell == 'SELL':
                        query = """INSERT INTO `ant_cryptotradingbot`.`order_report_future` (`order_seq_id`,`symbol_name`,`signal_type`,`order_quantity`,`buy_price`,
                        `buy_amount`,`sell_price`,`sell_amount`,`profit_amount`,`profit_percent`,`username`,`order_date`,`update_date`,`commission_price`) 
                        VALUES ({},'{}','{}',{},null,null,{},{},null,null,'{}','{}',null, {});""" \
                            .format(orderSeqId, symbol, signal_type, ordered_qty, actual_open_price,
                                    buy_amount, username, trade_date, buy_order['commisionPrice'])

                    query_result = db_util.queryExecution(connection, query, 'insert')
                    if query_result:
                        trade_buy_amount = buy_amount / 20
                        w_ins_query = """UPDATE `ant_cryptotradingbot`.`ant_user_wallet` set `binance_exchange_usdt` = `binance_exchange_usdt` - {} WHERE `username` = '{}';""" \
                            .format(trade_buy_amount, username)
                        db_util.queryExecution(connection, w_ins_query, 'update')
                        query_1 = """UPDATE `ant_cryptotradingbot`.`current_buy_order_report_future` SET `buy_orderID`={},`buy_price`={} 
                        WHERE `symbol_name`='{}' and `signal_type`='{}' and `username`='{}';""" \
                            .format(0, actual_open_price, symbol, signal_type, username)
                        if buy_sell == 'SELL':
                            query_1 = """UPDATE `ant_cryptotradingbot`.`current_buy_order_report_future` SET `sell_orderID`={},`sell_price`={}
                            WHERE `symbol_name`='{}' and `signal_type`='{}' and `username`='{}';""" \
                                .format(0, actual_open_price, symbol, signal_type, username)
                        query_result = db_util.queryExecution(connection, query_1, 'update')
                    print(str(buy_order)+' - DB Insert : '+str(query_result))
                    connection.close()
                    open_price = actual_open_price
                log = '{} - {} ==::== {} :: {} :: {} :: qty {}'.format(username, order_seq, 'Buy Order', replace_future_symbolname(symbol), str(actual_open_price), str(qty))
                print(log)
                in_position_entry = True
            else:
                print('{} - {} ==::== Buy ordered not done... for symbol : {}'.format(username, order_seq, replace_future_symbolname(symbol)))
                in_position_entry = False

        if in_position_entry:
            orderId = 0
            stopOrderId = stop_id
            orderStatus = 'NEW'
            stopOrderStatus = 'NEW'
            if buy_sell == 'SELL':
                buy_sell = 'BUY'
            else:
                buy_sell = 'SELL'
            if trade_type == 'live':
                '''Live Trade'''
                symbol_info = exchange.fetch_ticker(symbol)['info']
                price_prec = dbsq.symbol_precision(symbol_info) + 3
                cur_ask_price = round(float(symbol_info[getting_price]), price_prec)
                open_price = round(float(open_price), price_prec)
                close_price = round(float(close_price), price_prec)
                stop_price = round(float(stop_price), price_prec)
                if qty > 0:
                    if order_id > 0:
                        sell_order = client.futures_get_order(symbol=replace_future_symbolname(symbol), side=buy_sell, orderId=int(order_id))
                        orderId = sell_order['orderId']
                        orderStatus = sell_order['status']
                        if orderStatus == 'CANCELLED':
                            order_id = 0
                    if stop_id > 0:
                        stop_order = client.futures_get_order(symbol=replace_future_symbolname(symbol), side=buy_sell, orderId=int(stop_id))
                        stopOrderId = stop_order['orderId']
                        stopOrderStatus = stop_order['status']
                        if stopOrderStatus == 'CANCELLED':
                            stopOrderId = 0

                    if order_id == 0 and stopOrderId == 0:
                        if cur_ask_price < close_price and buy_sell == 'BUY':
                            close_price = round(float(cur_ask_price + (cur_ask_price * 0.15 / 100)), price_prec)
                        elif cur_ask_price > close_price and buy_sell == 'SELL':
                            close_price = round(float(cur_ask_price - (cur_ask_price * 0.15 / 100)), price_prec)
                        sell_order = client.futures_get_open_orders(symbol=replace_future_symbolname(symbol), side=buy_sell)
                        if len(sell_order) > 0:
                            client.futures_cancel_all_open_orders(symbol=replace_future_symbolname(symbol))

                        if len(sell_order) == 0:
                            while int(orderId) == 0:
                                try:
                                    close_price = round(float(close_price), price_prec)
                                    sell_order = client.futures_create_order(symbol=replace_future_symbolname(symbol), side=buy_sell, type='TAKE_PROFIT_MARKET'
                                                                             , quantity=qty, stopprice=close_price, closePosition='true')
                                    time.sleep(5)
                                    orderId = int(sell_order['orderId'])
                                    orderStatus = sell_order['status']
                                except Exception as ex:
                                    error_log = str(ex).replace('\'', '\'\'') + " - trade_logic :: line ::" \
                                                + str(sys.exc_info()[2].tb_lineno)
                                    time.sleep(5)
                                    if str(ex).endswith('Precision is over the maximum defined for this asset.'):
                                        print(replace_future_symbolname(symbol) + ' - ' + str(close_price) + ' - ' + str(price_prec) + ' - ' + error_log)
                                        price_prec = price_prec - 1
                                    else:
                                        close_price = round(float(close_price + (close_price * 0.05 / 100)), price_prec)
                                        if buy_sell == 'BUY':
                                            close_price = round(float(close_price - (close_price * 0.05 / 100)), price_prec)
                                        print(replace_future_symbolname(symbol) + ' - ' + str(close_price) + ' - ' + error_log)
                                    continue
                    connection = db_util.connect_database()
                    if connection.is_connected():
                        dt_today = datetime.today()  # Local time
                        dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
                        trade_date = str(dt_India.strftime('%Y-%m-%d %H:%M:%S'))
                        query_1 = """UPDATE `ant_cryptotradingbot`.`current_buy_order_report_future` SET `sell_orderID`={}, `buy_orderID`=0, `close_orderDate`='{}' 
                        WHERE `symbol_name`='{}' and `signal_type`='{}' and `username`='{}';""" \
                            .format(orderId, trade_date, symbol, signal_type, username)
                        if buy_sell == 'BUY':
                            query_1 = """UPDATE `ant_cryptotradingbot`.`current_buy_order_report_future` SET `buy_orderID`={}, `sell_orderID`=0, `close_orderDate`='{}' 
                            WHERE `symbol_name`='{}' and `signal_type`='{}' and `username`='{}';""" \
                                .format(orderId, trade_date, symbol, signal_type, username)
                        query_result = db_util.queryExecution(connection, query_1, 'update')
                        query = """UPDATE `ant_cryptotradingbot`.`order_report_future` SET `sell_price`={}, `sell_amount`={}  
                        WHERE `symbol_name`='{}' and `signal_type`='{}' and `order_quantity`={} and `update_date` is null and `username`='{}';""" \
                            .format(close_price, (close_price * float(qty)), symbol, signal_type, round(float(qty), 2), username)
                        if buy_sell == 'BUY':
                            query = """UPDATE `ant_cryptotradingbot`.`order_report_future` SET `buy_price`={}, `buy_amount`={}  
                            WHERE `symbol_name`='{}' and `signal_type`='{}' and `order_quantity`={} and `update_date` is null and `username`='{}';""" \
                                .format(close_price, (close_price * float(qty)), symbol, signal_type, round(float(qty), 2), username)
                        query_result = db_util.queryExecution(connection, query, 'update')
                        prevTargetPrice = round(close_price,price_prec)
                        prevStopPrice = round(stop_price,price_prec)
                        is_stop_ordered_done = False
                        while orderStatus != 'FILLED' and orderStatus != 'CANCELLED' and stopOrderStatus != 'FILLED':  # and stopOrderStatus != 'FILLED'
                            symbol_info = exchange.fetch_ticker(symbol)['info']
                            cur_price = round(replace_future_symbolname_price(symbol, float(symbol_info['askPrice'])), price_prec)
                            open_price = round(float(open_price), price_prec)
                            stop_price = round(float(stop_price), price_prec)
                            current_percent = round(float((cur_price - open_price) / (open_price / 100)), 2)
                            target_percent = round(float((close_price - open_price) / (open_price / 100)), 2)
                            if buy_sell == 'BUY':
                                current_percent = -1 * current_percent
                                target_percent = -1 * target_percent
                            if target_percent > 1 and current_percent > (target_percent / 2):
                                stop_price = round(float(open_price + ((open_price * (target_percent / 4)) / 100)), price_prec)
                                if buy_sell == 'BUY':
                                    stop_price = round(float(open_price - ((open_price * (target_percent / 4)) / 100)), price_prec)
                            stop_percent = round(float((stop_price - open_price) / (open_price / 100)), 2)
                            if buy_sell == 'BUY':
                                stop_percent = -1 * stop_percent
                            symbols_exist = None
                            connectionSp = db_util.connect_database()
                            if connectionSp.is_connected():
                                query = """call `ant_cryptotradingbot`.`db_future_trade_exit`('{}', '{}');"""\
                                    .format(symbol, username)
                                symbols_exist = db_util.queryExecution(connectionSp, query, 'select')
                                connectionSp.close()
                            sell_order = client.futures_get_order(symbol=replace_future_symbolname(symbol), orderId=orderId, side=buy_sell)
                            orderId = int(sell_order['orderId'])
                            orderStatus = sell_order['status']
                            if stopOrderId > 0:
                                stop_order = client.futures_get_order(symbol=replace_future_symbolname(symbol), orderId=stopOrderId, side=buy_sell)
                                stopOrderId = int(stop_order['orderId'])
                                stopOrderStatus = stop_order['status']
                            
                            if len(symbols_exist) == 0 and orderStatus == 'NEW' and ((open_price < cur_price and buy_sell == 'SELL') or (open_price > cur_price and buy_sell == 'BUY')):
                                prevTargetPrice = close_price
                                if cur_price < close_price and buy_sell == 'BUY':
                                    close_price = round(float(cur_price + (cur_price * 0.2 / 100)), 8)
                                elif cur_price > close_price and buy_sell == 'SELL':
                                    close_price = round(float(cur_price - (cur_price * 0.2 / 100)), 8)
                                sell_order = client.futures_get_order(symbol=replace_future_symbolname(symbol), orderId=orderId, side=buy_sell)
                                orderId = int(sell_order['orderId'])
                                orderStatus = sell_order['status']
                                if orderStatus != 'FILLED' and prevTargetPrice != close_price:
                                    client.futures_cancel_order(symbol=replace_future_symbolname(symbol), orderId=orderId)
                                    orderId = 0
                                    while orderId == 0:
                                        try:
                                            sell_order = client.futures_create_order(symbol=replace_future_symbolname(symbol), side=buy_sell,
                                                                                     type='TAKE_PROFIT_MARKET'
                                                                                     , quantity=qty, stopprice=round(close_price,price_prec),
                                                                                     closePosition='true')
                                            time.sleep(2)
                                            orderId = int(sell_order['orderId'])
                                            orderStatus = sell_order['status']
                                        except Exception as ex:
                                            error_log = str(ex).replace('\'', '\'\'') + " - trade_logic :: line ::" \
                                                        + str(sys.exc_info()[2].tb_lineno)
                                            time.sleep(2)
                                            if str(ex).endswith('Precision is over the maximum defined for this asset.'):
                                                print(replace_future_symbolname(symbol) + ' - ' + str(close_price) + ' - ' + str(price_prec) + ' - ' + error_log)
                                                price_prec = price_prec - 1
                                            else:
                                                print(replace_future_symbolname(symbol) + ' - ' + error_log)
                                                close_price = round(float(close_price + (close_price * 0.05 / 100)), price_prec)
                                                if buy_sell == 'BUY':
                                                    close_price = round(float(close_price - (close_price * 0.05 / 100)), price_prec)
                                            continue
                            elif len(symbols_exist) > 0:
                                trade_id = int(symbols_exist[0][15])
                                if round(float(replace_future_symbolname_price(symbol, symbols_exist[0][6])), price_prec) != round(float(close_price), price_prec) and (orderStatus != 'NEW' or round(float(prevTargetPrice), price_prec) != round(float(replace_future_symbolname_price(symbol, symbols_exist[0][6])), price_prec)):
                                    open_price = round(replace_future_symbolname_price(symbol, float(symbols_exist[0][13])), price_prec)
                                    close_price = round(replace_future_symbolname_price(symbol, float(symbols_exist[0][6])), price_prec)
                                    stop_price = round(replace_future_symbolname_price(symbol, float(symbols_exist[0][7])), price_prec)
                                    sell_order = client.futures_get_order(symbol=replace_future_symbolname(symbol), orderId=orderId, side=buy_sell)
                                    orderId = int(sell_order['orderId'])
                                    orderStatus = sell_order['status']
                                    if orderStatus != 'FILLED':
                                        if orderId > 0:
                                            client.futures_cancel_order(symbol=replace_future_symbolname(symbol), orderId=orderId)
                                        orderId = 0
                                        is_ordered_done = False
                                    else:
                                        is_ordered_done = True

                                    while is_ordered_done == False:
                                        try:
                                            while orderId == 0:
                                                try:
                                                    sell_order = client.futures_create_order(symbol=replace_future_symbolname(symbol), side=buy_sell,
                                                                                             type='TAKE_PROFIT_MARKET'
                                                                                             , quantity=qty, stopprice=round(close_price,price_prec),
                                                                                             closePosition='true')
                                                    time.sleep(2)
                                                    orderId = int(sell_order['orderId'])
                                                    orderStatus = sell_order['status']
                                                except Exception as ex:
                                                    error_log = str(ex).replace('\'', '\'\'') + " - trade_logic :: line ::" \
                                                                + str(sys.exc_info()[2].tb_lineno)
                                                    time.sleep(2)
                                                    if str(ex).endswith('Precision is over the maximum defined for this asset.'):
                                                        print(replace_future_symbolname(symbol) + ' - ' + str(close_price) + ' - ' + str(price_prec) + ' - ' + error_log)
                                                        price_prec = price_prec - 1
                                                    else:
                                                        print(replace_future_symbolname(symbol) + ' - ' + error_log)
                                                        close_price = round(float(close_price + (close_price * 0.05 / 100)), price_prec)
                                                        if buy_sell == 'BUY':
                                                            close_price = round(float(close_price - (close_price * 0.05 / 100)), price_prec)
                                                    continue
                                            prevTargetPrice = round(close_price,price_prec)
                                            dt_today = datetime.today()  # Local time
                                            dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
                                            trade_date = str(dt_India.strftime('%Y-%m-%d %H:%M:%S'))
                                            query_1 = """UPDATE `ant_cryptotradingbot`.`current_buy_order_report_future` SET `sell_orderID`={}, `close_orderDate`='{}' 
                                            WHERE `symbol_name`='{}' and `signal_type`='{}' and `username`='{}';""" \
                                                .format(orderId, trade_date, symbol, signal_type, username)
                                            if buy_sell == 'BUY':
                                                query_1 = """UPDATE `ant_cryptotradingbot`.`current_buy_order_report_future` SET `buy_orderID`={}, `close_orderDate`='{}' 
                                                WHERE `symbol_name`='{}' and `signal_type`='{}' and `username`='{}';""" \
                                                    .format(orderId, trade_date, symbol, signal_type, username)
                                            query_result = db_util.queryExecution(connection, query_1, 'update')
                                            is_ordered_done = True
                                        except Exception as ex:
                                            error_log = str(ex).replace('\'', '\'\'') + " - Buy_Sell :: line ::" \
                                                        + str(sys.exc_info()[2].tb_lineno)
                                            print('Error: - Buy_Sell block error - {} ; symbol_name - {} ; price - {}'.format(
                                                error_log, symbol, close_price))
                                            close_price = round(float(close_price + (close_price * 0.05 / 100)), price_prec)
                                            if buy_sell == 'BUY':
                                                close_price = round(float(close_price - (close_price * 0.05 / 100)), price_prec)
                                            continue

                            if ((cur_price < stop_price and open_price > stop_price and close_price < stop_price and buy_sell == 'BUY') or (cur_price > stop_price and open_price < stop_price and close_price > stop_price and buy_sell == 'SELL')) and (stopOrderStatus != 'NEW' or prevStopPrice != round(stop_price,price_prec)):
                                is_stop_ordered_done = False
                                if stopOrderId > 0:
                                    stop_order = client.futures_get_order(symbol=replace_future_symbolname(symbol), orderId=stopOrderId, side=buy_sell)
                                    stopOrderId = int(stop_order['orderId'])
                                    stopOrderStatus = stop_order['status']
                                    if stopOrderStatus != 'FILLED':
                                        client.futures_cancel_order(symbol=replace_future_symbolname(symbol), side=buy_sell, orderId=stopOrderId)
                                        stopOrderId = 0
                                    else:
                                        is_stop_ordered_done = True
                                while is_stop_ordered_done == False:
                                    try:
                                        while stopOrderId == 0:
                                            try:
                                                stop_order = client.futures_create_order(symbol=replace_future_symbolname(symbol), side=buy_sell,
                                                                                         type='STOP_MARKET'
                                                                                         , quantity=qty, stopprice=round(stop_price,price_prec),
                                                                                         closePosition='true')
                                                time.sleep(2)
                                                stopOrderId = int(stop_order['orderId'])
                                                stopOrderStatus = stop_order['status']
                                            except Exception as ex:
                                                error_log = str(ex).replace('\'', '\'\'') + " - trade_logic :: line ::" \
                                                            + str(sys.exc_info()[2].tb_lineno)
                                                time.sleep(2)
                                                if str(ex).endswith('Precision is over the maximum defined for this asset.'):
                                                    print(replace_future_symbolname(symbol) + ' - ' + str(close_price) + ' - ' + str(price_prec) + ' - ' + error_log)
                                                    price_prec = price_prec - 1
                                                else:
                                                    print(replace_future_symbolname(symbol) + ' - ' + error_log)
                                                    close_price = round(float(close_price + (close_price * 0.05 / 100)), price_prec)
                                                    if buy_sell == 'BUY':
                                                        close_price = round(float(close_price - (close_price * 0.05 / 100)), price_prec)
                                                continue
                                        is_stop_ordered_done = True
                                        prevStopPrice = round(stop_price,price_prec)
                                        dt_today = datetime.today()  # Local time
                                        dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
                                        trade_date = str(dt_India.strftime('%Y-%m-%d %H:%M:%S'))
                                        query_1 = """UPDATE `ant_cryptotradingbot`.`current_buy_order_report_future` SET `stop_orderID`={}, `close_orderDate`='{}' 
                                        WHERE `symbol_name`='{}' and `signal_type`='{}' and `username`='{}';""" \
                                            .format(orderId, trade_date, symbol, signal_type, username)
                                        query_result = db_util.queryExecution(connection, query_1, 'update')
                                    except Exception as ex:
                                        stop_price = round(float(stop_price + (stop_price * 0.05 / 100)), price_prec)
                                        if buy_sell == 'SELL':
                                            stop_price = round(float(stop_price - (stop_price * 0.05 / 100)), price_prec)
                                        continue
                            dt_today = datetime.today()  # Local time
                            dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
                            current_date = str(datetime.strftime(dt_India, "%d%m%Y"))
                            print("""{} - {} ==::== {} is waiting for {} === qty: {} ;; open price: {} ;; 
                            current price : {} ;;  current percent : {} % ;; 
                            target price  : {} ;;  target percent  : {} % ;;
                            stop price    : {} ;;  stop percent    : {} %"""
                                  .format(username, order_seq, replace_future_symbolname(symbol), buy_sell, qty, open_price, cur_price, current_percent,
                                          close_price, target_percent, stop_price, stop_percent))
                            time.sleep(60)
                            if start_date != current_date:
                                sys.exit()

                        if is_stop_ordered_done:
                            stop_order = client.futures_get_order(symbol=replace_future_symbolname(symbol), orderId=stopOrderId, side=buy_sell)
                            if stop_order['status'] == 'FILLED':
                                orderId = stopOrderId
                        sell_order = client.futures_get_order(symbol=replace_future_symbolname(symbol), orderId=orderId, side=buy_sell)
                        if sell_order['status'] == 'FILLED':
                            client.futures_cancel_all_open_orders(symbol=replace_future_symbolname(symbol))
                            close_price = float(sell_order['avgPrice'])
                            ordered_qty = int(float(sell_order['executedQty']))
                            query_1 = """UPDATE `ant_cryptotradingbot`.`current_buy_order_report_future` SET `sell_orderID`={}, `sell_price`={}
                            WHERE `symbol_name`='{}' and `signal_type`='{}' and `username`='{}';""" \
                                .format(orderId, close_price, symbol, signal_type, username)
                            if buy_sell == 'BUY':
                                query_1 = """UPDATE `ant_cryptotradingbot`.`current_buy_order_report_future` SET `buy_orderID`={}, `buy_price`={}
                                WHERE `symbol_name`='{}' and `signal_type`='{}' and `username`='{}';""" \
                                    .format(orderId, close_price, symbol, signal_type, username)

                            db_util.queryExecution(connection, query_1, 'update')
                            is_ordered = True
                        else:
                            print("sell_order: ", sell_order)
                            query = """UPDATE `ant_cryptotradingbot`.`order_report_future` SET `sell_price`= null  
                            WHERE `symbol_name`='{}' and `signal_type`='{}' and `order_quantity`={} and `update_date` is null and `username`='{}';""" \
                                .format(symbol, signal_type, round(float(qty), 2), username)
                            if buy_sell == 'BUY':
                                query = """UPDATE `ant_cryptotradingbot`.`order_report_future` SET `buy_price`= null  
                                WHERE `symbol_name`='{}' and `signal_type`='{}' and `order_quantity`={} and `update_date` is null and `username`='{}';""" \
                                    .format(symbol, signal_type, round(float(qty), 2), username)

                            query_result = db_util.queryExecution(connection, query, 'insert')
                        connection.close()
            else:
                '''Mock Trade'''
                # df_read = pd.read_csv(trade_report_csv)
                symbol_info = exchange.fetch_ticker(symbol.replace('USDT','BUSD'))['info']
                cur_price = round(float(symbol_info['askPrice']), price_prec)
                ordered_qty = qty
                sell_order = {'commisionPrice': 0.0000, 'cummulativeQuoteQty': round(float(float(ordered_qty) * cur_price),price_prec)}
                # sell_order['orderSeqId'] = str(len(df_read))
                connection = db_util.connect_database()
                if connection.is_connected():
                    select_query = """SELECT `buy_amount` from `ant_cryptotradingbot`.`order_report_future` 
                    WHERE `symbol_name`='{}' and `signal_type`='{}' and `order_quantity`={} and `update_date` is null and `username`='{}';"""\
                        .format(symbol, signal_type, round(float(ordered_qty), 2), username)
                    if buy_sell == 'BUY':
                        select_query = """SELECT `sell_amount` from `ant_cryptotradingbot`.`order_report_future` 
                        WHERE `symbol_name`='{}' and `signal_type`='{}' and `order_quantity`={} and `update_date` is null and `username`='{}';""" \
                            .format(symbol, signal_type, round(float(ordered_qty), 2), username)

                    select_query_result = db_util.queryExecution(connection, select_query, 'select')
                    if len(select_query_result) > 0:
                        currnt_busd_bal = getBalance('USDT')
                        with open(busd_bal_txt, 'w') as busd:
                            busd.write(str(currnt_busd_bal))
                            busd.close()
                        is_ordered = True
                    connection.close()

            if is_ordered:
                connection = db_util.connect_database()
                if connection.is_connected():
                    select_query = """SELECT `buy_amount` from `ant_cryptotradingbot`.`order_report_future` 
                    WHERE `symbol_name`='{}' and `signal_type`='{}' and `order_quantity`={} and `update_date` is null and `username`='{}';"""\
                        .format(symbol, signal_type, round(float(ordered_qty), 2), username)
                    select_query_result = db_util.queryExecution(connection, select_query, 'select')
                    buy_amount = float(select_query_result[0][0])
                    sell_amount = round(float(ordered_qty) * float(close_price), 4)
                    sell_order['commisionPrice'] = (sell_amount / 20) / 100
                    close_amount = sell_amount
                    if buy_sell == 'BUY':
                        select_query = """SELECT `sell_amount` from `ant_cryptotradingbot`.`order_report_future` 
                        WHERE `symbol_name`='{}' and `signal_type`='{}' and `order_quantity`={} and `update_date` is null and `username`='{}';""" \
                            .format(symbol, signal_type, round(float(ordered_qty), 2), username)
                        select_query_result = db_util.queryExecution(connection, select_query, 'select')
                        buy_amount = round(float(ordered_qty) * float(close_price), 4)
                        sell_amount = float(select_query_result[0][0])
                        sell_order['commisionPrice'] = (buy_amount / 20) / 100
                        close_amount = buy_amount

                    profit_loss = round((sell_amount - buy_amount), 2)
                    percentage = round((profit_loss * 100) / buy_amount, 2) * 20

                    dt_today = datetime.today()  # Local time
                    dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
                    trade_date = str(dt_India.strftime('%Y-%m-%d %H:%M:%S'))
                    query = """UPDATE `ant_cryptotradingbot`.`order_report_future` SET `sell_price`={},`sell_amount`={},`profit_amount`={},`profit_percent`={},`update_date`='{}', `sell_reason`='{}', `commission_price`=`commission_price`+{} 
                    WHERE `symbol_name`='{}' and `signal_type`='{}' and `order_quantity`={} and `update_date` is null and `username`='{}';"""\
                        .format(close_price, sell_amount, profit_loss, percentage, trade_date, 'Target reached', sell_order['commisionPrice'], symbol, signal_type, round(float(ordered_qty), 2), username)
                    if buy_sell == 'BUY':
                        query = """UPDATE `ant_cryptotradingbot`.`order_report_future` SET `buy_price`={},`buy_amount`={},`profit_amount`={},`profit_percent`={},`update_date`='{}', `sell_reason`='{}', `commission_price`=`commission_price`+{} 
                        WHERE `symbol_name`='{}' and `signal_type`='{}' and `order_quantity`={} and `update_date` is null and `username`='{}';""" \
                            .format(close_price, buy_amount, profit_loss, percentage, trade_date, 'Target reached',
                                    sell_order['commisionPrice'], symbol, signal_type, round(float(ordered_qty), 2),
                                    username)
                    query_1 = """DELETE FROM `ant_cryptotradingbot`.`current_buy_order_report_future` 
                    WHERE `symbol_name`='{}' and `signal_type`='{}' and `order_quantity`={} and `username`='{}';"""\
                        .format(symbol, signal_type, round(float(ordered_qty), 2), username)
                    query_result = db_util.queryExecution(connection, query, 'update')
                    query_demo_1 = """UPDATE `ant_cryptotradingbot`.`db_demo_trade` SET exit_signal_type = entry_signal_type, `exit_price`={}
                    WHERE (`symbol_name`='{}' or `trade_id`={}) and `exit_date` is null;"""\
                        .format(close_price, symbol, trade_id)
                    db_util.queryExecution(connection, query_demo_1, 'update')
                    query_demo_2 = """UPDATE `ant_cryptotradingbot`.`db_demo_trade` set `pnl_per_usdt`= (CASE WHEN signal_side = 'BUY' THEN exit_price - entry_price ELSE entry_price - exit_price END) * qty_per_usdt, `exit_date`='{}' 
                    WHERE (`symbol_name`='{}' or `trade_id`={}) and `exit_date` is null;"""\
                        .format(trade_date, symbol, trade_id)
                    db_util.queryExecution(connection, query_demo_2, 'update')
                    if query_result:
                        query_result = db_util.queryExecution(connection, query_1, 'update')
                        signal_type_new = signal_type
                        if '-' in signal_type:
                            signal_type_new = signal_type_new.split('-')[0].strip()
                        query_2 = """UPDATE `ant_cryptotradingbot`.`db_live_trade_signals` SET trade_closed = True  
                        WHERE `symbol_name`='{}' and `signal_type`='{}' and trade_closed = False;"""\
                            .format(symbol, signal_type_new)
                        query_result = db_util.queryExecution(connection, query_2, 'update')
                        w_close_amount = close_amount / 20
                        w_ins_query = """UPDATE `ant_cryptotradingbot`.`ant_user_wallet` set `binance_exchange_usdt` = `binance_exchange_usdt`+{} WHERE `username` = '{}';""" \
                            .format(w_close_amount, username)
                        wallet_query_result = db_util.queryExecution(connection, w_ins_query, 'update')
                        if wallet_query_result:
                            comsumption_energy = profit_loss * 30
                            pw_ins_query = """UPDATE `ant_cryptotradingbot`.`ant_user_data` set energy_power = energy_power-{} WHERE `username` = '{}';""" \
                                .format(comsumption_energy, username)
                            pw_query_result = db_util.queryExecution(connection, pw_ins_query, 'update')
                            query_1 = """UPDATE `ant_cryptotradingbot`.`current_buy_order_report_future` SET `sell_orderID`={}, `close_orderDate`=null 
                            WHERE `symbol_name`='{}' and `signal_type`='{}' and `username`='{}';""" \
                                .format(0, symbol, signal_type, username)
                            if buy_sell == 'BUY':
                                query_1 = """UPDATE `ant_cryptotradingbot`.`current_buy_order_report_future` SET `buy_orderID`={}, `close_orderDate`=null 
                                WHERE `symbol_name`='{}' and `signal_type`='{}' and `username`='{}';""" \
                                    .format(0, symbol, signal_type, username)

                            query_result = db_util.queryExecution(connection, query_1, 'update')

                    print(str(sell_order)+' - DB Update : '+str(query_result))
                    connection.close()
                log = '{} - {} ==::== {} :: {} :: {} :: qty {}'.format(username, order_seq, 'Sell Order', replace_future_symbolname(symbol), str(close_price), str(qty))
                print(log)
                in_position_entry = False
            else:
                print('{} - {} ==::== Close ordered not done... for symbol : {}'.format(username, order_seq, replace_future_symbolname(symbol)))
                in_position_entry = True
        else:
            print(replace_future_symbolname(symbol) + ' - ' + 'nothing to do... in buy / sell block...')
        gc.collect()
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - Buy_Sell :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print('Error: - Buy_Sell block error - {} ; qty - {} ; price - {}'.format(error_log, str(qty), close_price))
        if str(ex).endswith('Order does not exist.'):
            gc.collect()
            return in_position_entry, close_price, ordered_qty, 0, signal_type
    finally:
        gc.collect()
        return in_position_entry, close_price, ordered_qty, 0, signal_type


def start_trade(nthread):
    while True:
        try:
            if trade_type == 'live':
                '''Live Trade'''
                curr_busd_bal = round(float(getBalance('USDT')), 2)
            else:
                '''Mock Trade'''
                with open(busd_bal_txt, 'r') as busd:
                    curr_busd_bal = round(float(busd.readline()), 2)
                    busd.close()

            connection = db_util.connect_database()
            if connection.is_connected():
                trade_query = """SELECT count(symbol_name) FROM `ant_cryptotradingbot`.`current_buy_order_report_future` WHERE `username`='{}';"""\
                    .format(username)
                trade_query_result = db_util.queryExecution(connection, trade_query, 'select')
                if trade_query_result[0][0] >= nthread:
                    dt_today = datetime.today()  # Local time
                    dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
                    current_date = str(datetime.strftime(dt_India, "%d%m%Y"))
                    trade_date = str(dt_India.strftime('%Y-%m-%d %H:%M:%S'))
                    drp_trade_date = str(dt_India.strftime('%Y-%m-%d'))
                    wallet_query = """SELECT `initial_investment_future` FROM `ant_cryptotradingbot`.`ant_user_wallet` where `username` = '{}'""" \
                        .format(username)
                    wallet_query_result = db_util.queryExecution(connection, wallet_query, 'select')
                    if wallet_query_result[0][0] == 0:
                        curr_busd_bal = round(float(curr_busd_bal), 2)
                        w_ins_query = """UPDATE `ant_cryptotradingbot`.`ant_user_wallet` set `initial_investment_future`={}, `binance_exchange_usdt`= (`initial_investment_spot` + {}) WHERE `username`='{}';""" \
                            .format(curr_busd_bal, curr_busd_bal, username)
                        wallet_query_result = db_util.queryExecution(connection, w_ins_query, 'update')
                        print('New Wallet DBUpdated :: {}'.format(wallet_query_result))
                    dpr_bal_query = """(select distinct auw.`initial_investment_future` as invest_amount, (auw.`binance_exchange_usdt`+(select sum(buy_amount) from `ant_cryptotradingbot`.`order_report_future` where username = '{}' and sell_amount is null)) as final_amount from `ant_cryptotradingbot`.`order_report_future` as ort inner join `ant_cryptotradingbot`.`ant_user_wallet` as auw on auw.username = ort.username where ort.username = '{}' and ort.sell_amount is null)
                    union all
                    (select distinct auw.`initial_investment_future` as invest_amount, auw.`binance_exchange_usdt` as final_amount from `ant_cryptotradingbot`.`order_report_future` as ort inner join `ant_cryptotradingbot`.`ant_user_wallet` as auw on auw.username = ort.username where ort.username = '{}' and ort.sell_amount is not null
                    and (select count(buy_amount) from `ant_cryptotradingbot`.`order_report_future` where username = '{}' and sell_amount is null) = 0)
                    union all
                    (select distinct auw.`initial_investment_future` as invest_amount, auw.`binance_exchange_usdt` as final_amount from `ant_cryptotradingbot`.`ant_user_wallet` as auw left join `ant_cryptotradingbot`.`order_report_future` as ort on auw.username = ort.username where auw.username = '{}' and ort.username is null)""" \
                        .format(username, username, username, username, username)
                    dpr_bal_query_result = db_util.queryExecution(connection, dpr_bal_query, 'select')
                    drp_start_date = str(datetime.strftime(dt_India, "%Y-%m-%d"))
                    dpr_query = """SELECT `start_amount` FROM `ant_cryptotradingbot`.`daily_profit_report_future` where `date` = '{}' and `username` = '{}'""" \
                        .format(drp_start_date, username)
                    dpr_query_result = db_util.queryExecution(connection, dpr_query, 'select')
                    if len(dpr_query_result) == 0:
                        dpr_start_amount = round(float(dpr_bal_query_result[0][0]), 2)
                        dpr_ins_query = """INSERT `ant_cryptotradingbot`.`daily_profit_report_future` (`date`, `username`, `start_amount`, `end_amount`, `update_date`) VALUES ('{}', '{}', {}, {}, '{}');""" \
                            .format(drp_start_date, username, dpr_start_amount, dpr_start_amount, trade_date)
                        dpr_query_result = db_util.queryExecution(connection, dpr_ins_query, 'insert')
                    profit_amount = 0
                    commission_amount = 0
                    dpr_bal_query = """select sum(orp.profit_amount), sum(orp.commission_price) from 
                                    (select cast(update_date as date) as `date`, profit_amount, commission_price from `ant_cryptotradingbot`.`order_report_future` where `username` = '{}') as orp
                                    where orp.`date`='{}' group by orp.`date`""".format(username, drp_start_date)
                    dpr_bal_query_result = db_util.queryExecution(connection, dpr_bal_query, 'select')
                    if len(dpr_bal_query_result) > 0:
                        profit_amount = round(float(dpr_bal_query_result[0][0]), 2)
                        commission_amount = round(float(dpr_bal_query_result[0][1]), 2)
                    print('Profit select of date ::: {} -- profit ::: {}'.format(drp_start_date, profit_amount))
                    dpr_query = """SELECT `start_amount` FROM `ant_cryptotradingbot`.`daily_profit_report_future` where `date` = '{}' and `username` = '{}'""" \
                        .format(drp_trade_date, username)
                    dpr_query_result = db_util.queryExecution(connection, dpr_query, 'select')
                    if len(dpr_query_result) > 0:
                        dpr_start_amount = round(float(dpr_query_result[0][0]), 2)
                        dpr_end_amount = dpr_start_amount + profit_amount
                        print('{} - {} - {}'.format(dpr_end_amount, commission_amount, dpr_start_amount))
                        profit_percent = round(
                            float((dpr_end_amount - commission_amount - dpr_start_amount) / (dpr_start_amount / 100)), 2)
                        update_query = """UPDATE `ant_cryptotradingbot`.`daily_profit_report_future` 
                        SET `end_amount`={}, profit_amount= {}, profit_percent={}, commission_price={}, update_date = '{}'
                        WHERE `date` = '{}' and `username` = '{}'""" \
                            .format(dpr_end_amount, profit_amount, profit_percent, commission_amount, trade_date,
                                    drp_start_date, username)
                        db_update = db_util.queryExecution(connection, update_query, 'update')
                        print('{} - {} ==::== Profit update of date ::: {} -- profit ::: {} -- DBUpdate ::: {}'.format(username, nthread, start_date, profit_amount, db_update))
                    if start_date != current_date:
                        update_query = """UPDATE `ant_cryptotradingbot`.`ant_user_wallet` 
                        SET `binance_exchange_usdt`={}
                        WHERE `username` = '{}'""" \
                            .format(curr_busd_bal, username)
                        db_update = db_util.queryExecution(connection, update_query, 'update')
                        update_query = """UPDATE `ant_cryptotradingbot`.`ant_user_data` SET `is_tool_running`=False
                        WHERE `is_tool_running` = True and `username` = '{}'"""\
                            .format(username)
                        db_update = db_util.queryExecution(connection, update_query, 'update')
                        print('{} - {} ==::== Trading closed for end of date ::: {} -- DBUpdate ::: {}'.format(username, nthread, start_date, db_update))
                        sys.exit()

                    select_query = """SELECT `symbol_name`,`signal_type`,`order_quantity`,`buy_price`,`sell_price`, `buy_orderID`, `sell_orderID`, `stop_orderID` FROM `ant_cryptotradingbot`.`current_buy_order_report_future` WHERE `username`='{}' and `order_seq_id`={};"""\
                        .format(username, nthread)
                    select_query_result = db_util.queryExecution(connection, select_query, 'select')
                    pw_select_query = """SELECT `energy_power` FROM `ant_cryptotradingbot`.`ant_user_data` WHERE `username`='{}';"""\
                        .format(username)
                    pw_query_result = db_util.queryExecution(connection, pw_select_query, 'select')
                    if (int(curr_busd_bal) >= BUY_AMT or len(select_query_result) > 0) and int(pw_query_result[0][0]) >= 30:
                        trade_logic(select_query_result, nthread)
                        print('Time sleep for : 15 minutes.....')
                        time.sleep(900)
                    elif int(pw_query_result[0][0]) < 30:
                        print('{} - {} ==::== Current Energy balance balance is < 30 (Energy Power {})'.format(username, nthread, str(pw_query_result[0][0])))
                    else:
                        print('{} - {} ==::== Current USDT balance is < {} (USDT {})'.format(username, nthread, str(BUY_AMT), curr_busd_bal))
                else:
                    print('{} - {} ==::== Time sleep for : 1 hour.....'.format(username, nthread))
                    time.sleep(3600)
                connection.close()
            print('{} - {} ==::== Time sleep for : 1 minutes.....'.format(username, nthread))
            gc.collect()
            time.sleep(59)
        except Exception as ex:
            error_log = str(ex).replace('\'', '\'\'') + " - trade_logic :: line ::" \
                        + str(sys.exc_info()[2].tb_lineno)
            print('Error: - Start trade block error - {}'.format(error_log))
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


def replace_future_symbolname_price(symbol, price):
    if symbol == 'BONKUSDT' or symbol == 'FLOKIUSDT' or symbol == 'LUNCUSDT' or symbol == 'PEPEUSDT' or symbol == 'RATSUSDT' or symbol == 'SATSUSDT' or symbol == 'SHIBUSDT' or symbol == 'XECUSDT':
        return float(price*1000)
    else:
        return float(price)


if __name__ == "__main__":
    dt_today = datetime.today() #- timedelta(days=1) # Local time
    dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
    start_date = str(datetime.strftime(dt_India, "%d%m%Y"))
    log_filename = "DB_Trading_BOT_{}_{}.log".format(start_date, str(sys.argv[1]))
    current_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../')
    try:
        username = str(sys.argv[1])
        api_key = str(sys.argv[2])
        api_secret = str(sys.argv[3])
        if username == 'Admin':
            trade_type = 'mock'
            client = Client(config.BINANCE_API_KEY, config.BINANCE_API_SECRET)
        else:
            trade_type = 'live'
            client = Client(api_key, api_secret)
        print('Trading started... for {}'.format(username))
        # pprint.pprint(client.get_account())
        if trade_type == 'live':
            '''Live Trade'''
            busd_bal = getBalance('USDT')
        else:
            '''Mock Trade'''
            # trade_report_csv_path = current_dir + '../candlestick-screener-master/report'
            busd_bal_txt = current_dir + '/usdt_bal.txt'
            with open(busd_bal_txt, 'r') as busd:
                busd_bal = float(busd.readline())
                busd.close()

        print(username, ' ==::== ', str(busd_bal), 'USDT')
        s_interval = '15m'  # valid intervals - 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
        RSI_PERIOD = 6
        RSI_OVERBOUGHT = 70
        RSI_OVERBOUGHT_SELL = 80
        RSI_OVERSOLD = 30
        BUY_AMT = 5
        connection = db_util.connect_database()
        if connection.is_connected():
            current_pos = 0.00
            ba_select_query = """select `single_trade_amount_future` from `ant_cryptotradingbot`.`ant_user_data` where `username`='{}';""" \
                .format(username)
            ba_select_query_result = db_util.queryExecution(connection, ba_select_query, 'select')
            try:
                if ba_select_query_result[0][0] != 50 and len(ba_select_query_result) > 0:
                    BUY_AMT = ba_select_query_result[0][0]
            except:
                pass
            # select_query = """select cbor.symbol_name from `ant_cryptotradingbot`.`current_buy_order_report_future` as cbor
            # left join `ant_cryptotradingbot`.`order_report_future` as ort on ort.symbol_name = cbor.symbol_name
            # and ort.signal_type = cbor.signal_type and ort.order_quantity = cbor.order_quantity
            # and ort.buy_price = cbor.buy_price and ort.order_date = cbor.order_date and ort.username = cbor.username
            # where ort.buy_amount is null and cbor.buy_orderID = 0 and cbor.username = '{}';""" \
            #     .format(username)
            # select_query_result = db_util.queryExecution(connection, select_query, 'select')
            # for rq in select_query_result:
            #     delete_query = """delete from `ant_cryptotradingbot`.`current_buy_order_report_future` where symbol_name = '{}' and username = '{}';""" \
            #         .format(rq[0], username)
            #     update_query_result = db_util.queryExecution(connection, delete_query, 'update')

            select_query = """select cbor.symbol_name, cbor.signal_type, cbor.order_quantity, cbor.buy_price, cbor.order_date 
            from `ant_cryptotradingbot`.`current_buy_order_report_future` as cbor 
            inner join `ant_cryptotradingbot`.`order_report_future` as ort on ort.symbol_name = cbor.symbol_name 
            and ort.signal_type = cbor.signal_type and ort.order_quantity = cbor.order_quantity 
            and ort.buy_price = cbor.buy_price and ort.order_date = cbor.order_date and ort.username = cbor.username
            where ort.sell_amount is null and ort.sell_price is not null and cbor.sell_orderID = 0 and cbor.username = '{}';""" \
                .format(username)
            select_query_result = db_util.queryExecution(connection, select_query, 'select')
            for rq in select_query_result:
                update_query = """update `ant_cryptotradingbot`.`order_report_future` set sell_price = null 
                where symbol_name = '{}' and signal_type = '{}' and order_quantity = {} 
                and buy_price = {} and order_date = '{}' and `update_date` is null and username = '{}';""" \
                    .format(rq[0], rq[1], rq[2], rq[3], rq[4], username)
                update_query_result = db_util.queryExecution(connection, update_query, 'update')

            select_query = """SELECT sum(`buy_price`*`order_quantity`) FROM `ant_cryptotradingbot`.`current_buy_order_report_future` WHERE `username`='{}';"""\
                .format(username)
            select_query_result = db_util.queryExecution(connection, select_query, 'select')
            if select_query_result[0][0] is not None:
                current_pos = float(select_query_result[0][0])
            nthread_count = int((int(float(busd_bal)+current_pos) / 4) / BUY_AMT) + 1
            select_orderseq_query = """select symbol_name from `ant_cryptotradingbot`.`current_buy_order_report_future` WHERE `username`='{}' order by trade_id asc;""" \
                .format(username)
            select_orderseq_query_result = db_util.queryExecution(connection, select_orderseq_query, 'select')
            ord_seq = 0
            for rq in select_orderseq_query_result:
                update_query = """update `ant_cryptotradingbot`.`current_buy_order_report_future` set order_seq_id={} where `username`='{}' and symbol_name='{}';""" \
                    .format(ord_seq, username, rq[0])
                update_query_result = db_util.queryExecution(connection, update_query, 'update')
                ord_seq += 1

            if nthread_count < len(select_orderseq_query_result):
                nthread_count = len(select_orderseq_query_result)

            if nthread_count == len(select_orderseq_query_result) and busd_bal >= 100:
                nthread_count += 1

            query_1 = """UPDATE `ant_cryptotradingbot`.`ant_user_data` SET `max_trade`={} 
            WHERE `username`='{}';""" \
                .format(nthread_count, username)
            query_result = db_util.queryExecution(connection, query_1, 'update')
            query_2 = """UPDATE `ant_cryptotradingbot`.`ant_user_wallet` SET `initial_investment_future`={} 
            WHERE `username`='{}' and `initial_investment_future`=0;""" \
                .format(busd_bal, username)
            query_result = db_util.queryExecution(connection, query_2, 'update')
            connection.close()
            print(username, ' ==::== ', nthread_count)
            for r in range(0, nthread_count):
                x = threading.Thread(target=start_trade, args=(r,))
                x.start()
                if len(select_orderseq_query_result) <= r:
                    print('Waiting for next thread {}.... Time sleep for : 15 minutes......'.format((r+1)))
                    time.sleep(900)
                elif len(select_orderseq_query_result) > r:
                    print('Time sleep for : 10 seconds......')
                    time.sleep(10)
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - main :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print('Error: - Main error - {}'.format(error_log))
        print('Time sleep for : 1 min......')
        time.sleep(60)
