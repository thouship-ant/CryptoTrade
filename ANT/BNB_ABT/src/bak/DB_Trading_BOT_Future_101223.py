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
        if len(select_query_result) > 0:
            symbol = select_query_result[0][0]
            client.futures_cancel_all_open_orders(symbol=symbol)
            signal_type = select_query_result[0][1]
            ordered_qty = float(select_query_result[0][2])
            buy_price = 0
            if select_query_result[0][3] is not None:
                buy_price = float(select_query_result[0][3])
                order_type = 'BUY'
            if buy_price == 0 and select_query_result[0][4] is not None:
                buy_price = float(select_query_result[0][4])
                order_type = 'SELL'
            buy_orderID = float(select_query_result[0][5])
            sell_orderID = float(select_query_result[0][6])
            if buy_orderID > 0:
                order_type = 'SELL'
                order_id = buy_orderID
            elif sell_orderID > 0:
                order_type = 'BUY'
                order_id = sell_orderID
            in_position = True
        else:
            in_position = False
            buy_price = 0.00
            order_id = 0
            ordered_qty = 0
            signal_type = ''

        if not(in_position):
            connection = db_util.connect_database()
            if connection.is_connected():
                query = """SELECT SYMBOL_NAME, current_price, ema_7, ema_25, ema_99, CASE WHEN `SIGNAL_7_25` = 'BUY' or `SIGNAL_7_99` = 'BUY' or `SIGNAL_7_200` = 'BUY' THEN 'BUY' WHEN `SIGNAL_7_25` = 'SELL' or `SIGNAL_7_99` = 'SELL' or `SIGNAL_7_200` = 'SELL' THEN 'SELL' ELSE 'None' END as `SIGNAL` FROM `ant_cryptotradingbot`.`crypto_symbols_ema_data` WHERE `SIGNAL_7_25` in ('BUY', 'SELL') or `SIGNAL_7_99`  in ('BUY', 'SELL') or `SIGNAL_7_200`  in ('BUY', 'SELL');"""
                symbols_list = db_util.queryExecution(connection, query, 'select')
                signal_name = 'EMA'
                if len(symbols_list) == 0:
                    query = """SELECT csd.`symbol_name`, `current_askPrice`, `upper_BBand_price`, `middle_BBand_price`, `lower_BBand_price`, `MACD_dif`, `MACD_dem`, `MACD_macd`, `last_RSI`, `stoch`, `2hrs_ST`, csd.`last_update_DateTime`, csmsd.sum_dem_macd_prv, csmsd.sum_dem_macd_current FROM `ant_cryptotradingbot`.`crypto_symbols_data` as csd 
                                    INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_macd_st_data` as csmsd on csd.symbol_name = csmsd.symbol_name 
                                    WHERE (csd.upper_BBand_price > csd.current_askPrice 
                                    and (csd.middle_BBand_price < csd.current_askPrice or ((csd.middle_BBand_price + csd.lower_BBand_price)/2) < csd.current_askPrice)) and 
                                    csmsd.sum_dem_macd_current >= 0 and csmsd.sum_dem_macd_prv < csmsd.sum_dem_macd_current and csd.MACD_dem < 0 and 
                                    csd.MACD_macd > 0 and csd.last_RSI > 50 and csd.last_RSI < 65 and csd.`stoch` = 1
                                    and csd.`2hrs_ST` = True and csd.is_Active = True;"""
                    symbols_list = db_util.queryExecution(connection, query, 'select')
                    signal_name = 'MACD - BUY'

                if len(symbols_list) > 0:
                    # symbols_count = len(symbols_list)
                    # selected_symbol = symbols_list[randint(0, symbols_count-1)]
                    for selected_symbol in symbols_list:
                        symbol = selected_symbol[0]
                        symbol_info = exchange.fetch_ticker(symbol)['info']
                        cur_ask_price = round(float(symbol_info['askPrice']), 8)
                        order_trigger = False
                        if signal_name == 'EMA':
                            ema_7 = selected_symbol[2]
                            ema_25 = selected_symbol[3]
                            ema_99 = selected_symbol[4]
                            order_type = selected_symbol[5]
                            query_macd = """SELECT csd.`symbol_name`, `current_askPrice`, `upper_BBand_price`, `middle_BBand_price`, `lower_BBand_price`, `MACD_dif`, `MACD_dem`, `MACD_macd`, `last_RSI`, `stoch`, `2hrs_ST`, csd.`last_update_DateTime`, csmsd.sum_dem_macd_prv, csmsd.sum_dem_macd_current FROM `ant_cryptotradingbot`.`crypto_symbols_data` as csd 
                                            INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_macd_st_data` as csmsd on csd.symbol_name = csmsd.symbol_name 
                                            WHERE csd.`symbol_name` ='{}'""".format(symbol)
                            macd_list = db_util.queryExecution(connection, query_macd, 'select')
                            MACD_dif = macd_list[0][5]
                            MACD_macd = macd_list[0][7]
                            if selected_symbol[5] == 'BUY' and MACD_dif > 0 and MACD_macd < 0:
                                order_type = 'SELL'
                            elif selected_symbol[5] == 'SELL' and MACD_dif < 0:
                                order_type = 'BUY'

                            signal_type = signal_name + ' - ' + order_type
                            print("Order Type :: {} - Symbol :: {} - Current Price :: {} - EMA7 :: {} - EMA25 :: {} - EMA99 :: {}".format(order_type, symbol, cur_ask_price, ema_7, ema_25, ema_99))
                            if (ema_7 < cur_ask_price and order_type == 'BUY') or (ema_7 > cur_ask_price and order_type == 'SELL'):
                                order_trigger = True
                        elif signal_name == 'MACD - BUY':
                            signal_type = signal_name
                            order_type = 'BUY'
                            order_trigger = True
                            MACD_dif = selected_symbol[5]
                            MACD_dem = selected_symbol[6]
                            MACD_macd = selected_symbol[7]
                            print("Order Type :: {} - Symbol :: {} - Current Price :: {} - MACD_dif :: {} - MACD_dem :: {} - MACD_macd :: {}"
                                  .format(order_type, symbol, cur_ask_price, MACD_dif, MACD_dem, MACD_macd))

                        if order_trigger:
                            info = None
                            try:
                                info = client.futures_symbol_ticker(symbol=symbol)
                                print(info)
                            except Exception as ex:
                                error_log = str(ex).replace('\'', '\'\'') + " - trade_logic :: line ::" \
                                            + str(sys.exc_info()[2].tb_lineno)
                                print(symbol + ' - ' + error_log)
                            if info is not None:
                                symbol_df = get_data_frame(symbol)
                                closes = symbol_df['close'].tolist()
                                icloses = [float(c) for c in closes]
                                np_closes = np.array(icloses)
                                rsi = talib.RSI(np_closes, RSI_PERIOD)
                                last_rsi = round(float(rsi[-1]), 2)
                                if ((last_rsi <= 70 and order_type == 'BUY') or (last_rsi >= 20 and order_type == 'SELL')) and not(in_position): # and is_entry_point
                                    in_position, buy_price, ordered_qty, order_id, signal_type = buy_or_sell(symbol, order_type, signal_type, in_position, nthread)
                                    if in_position:
                                        connection.close()
                                        break
                        print('Time sleep for : {} seconds.....'.format(str(10)))
                        time.sleep(10)
                    connection.close()
                else:
                    connection.close()
                    return

        if in_position:
            target_percent = 0.5
            repurchase_percent = -5
            if order_type == 'SELL':
                target_percent = -1 * target_percent
                repurchase_percent = -1 * repurchase_percent

            highest_price = buy_price
            is_half_target = False
            is_min_target = False
            is_full_target = False
            old_target_percent = 0
            is_exit_call = False
            exit_method = ''
            f_current_price = 0.00
            current_percent = 0
            target_price = 0
            repurchase_price = 0
            last_rsi = 0
            rev_target = 0
            prev_order_price = 0
            while True:
                dt_today = datetime.today()  # Local time
                dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
                current_date = str(datetime.strftime(dt_India, "%d%m%Y"))
                if start_date != current_date:
                    break
                connection = db_util.connect_database()
                if connection.is_connected():
                    close_ordertype = 'SELL'
                    if order_type == 'SELL':
                        close_ordertype = 'BUY'
                    query = """SELECT SYMBOL_NAME, current_price, ema_7, CASE WHEN `SIGNAL_7_25` = 'BUY' or `SIGNAL_7_99` = 'BUY' or `SIGNAL_7_200` = 'BUY' THEN 'BUY' WHEN `SIGNAL_7_25` = 'SELL' or `SIGNAL_7_99` = 'SELL' or `SIGNAL_7_200` = 'SELL' THEN 'SELL' ELSE 'None' END as `SIGNAL` FROM `ant_cryptotradingbot`.`crypto_symbols_ema_data` WHERE (`SIGNAL_7_25` = '{}' or `SIGNAL_7_99` = '{}' or `SIGNAL_7_200` = '{}') and symbol_name='{}';"""\
                        .format(close_ordertype, close_ordertype, close_ordertype, symbol)
                    symbols_list = db_util.queryExecution(connection, query, 'select')
                    if symbols_list is None or symbols_list == []:
                        symbol_df = get_data_frame(symbol)
                        closes = symbol_df['close'].tolist()
                        icloses = [float(c) for c in closes]
                        np_closes = np.array(icloses)
                        rsi = talib.RSI(np_closes, RSI_PERIOD)
                        last_rsi = round(float(rsi[-1]), 2)

                        # current_price = client.get_symbol_ticker(symbol=symbol)
                        # f_current_price = round(float(current_price['price']), 8)
                        symbol_info = exchange.fetch_ticker(symbol)['info']
                        # cur_ask_price = round(float(symbol_info['askPrice']), 8)
                        f_current_price = round(float(symbol_info['bidPrice']), 8)
                        current_percent = round(float((f_current_price - buy_price) / (buy_price / 100)), 2)
                        target_price = round(float(buy_price + (buy_price * target_percent / 100)), 8)
                        repurchase_price = round(float(buy_price + (buy_price * repurchase_percent / 100)), 8)
                        # if len(lst_support) > 0 and stoploss_percent < 0:
                        #     for support in lst_support:
                        #         if not (is_resistance_reach):
                        #             stoploss_percent = round(float((support - buy_price) / (buy_price / 100)), 2)
                        #             if -2 <= stoploss_percent < -1:
                        #                 stop_loss = support
                        #                 break
                        #
                        # if len(lst_resistance) > 0:
                        #     if not(is_resistance_reach) and target_price < lst_resistance[0]:
                        #         target_price = lst_resistance[0]
                        #     for resist in lst_resistance:
                        #         if resist > f_current_price >= target_price and stop_loss != target_price:
                        #             stop_loss = target_price
                        #             target_price = resist
                        #             is_resistance_reach = True
                        #             break

                    #     if buy_price < f_current_price and f_current_price > highest_price and order_type == 'SELL':
                    #         highest_price = f_current_price
                    #     elif buy_price > f_current_price and f_current_price < highest_price and order_type == 'BUY':
                    #         highest_price = f_current_price
                    #
                    #     if f_current_price < buy_price < highest_price and is_half_target is False and order_type == 'SELL':
                    #         target_price = highest_price
                    #     elif f_current_price > buy_price > highest_price and is_half_target is False and order_type == 'BUY':
                    #         target_price = highest_price
                    #
                    #     repurchase_percent = round(float((repurchase_price - buy_price) / (buy_price / 100)), 2)
                    #     target_percent = round(float((target_price - buy_price) / (buy_price / 100)), 2)
                    #
                    #     rev_target = target_percent / 2
                    #     min_target = rev_target / 2
                    #
                    #     if order_type == 'BUY' and (rev_target < 0.5 or min_target < 0.5):
                    #         rev_target = 0.50
                    #         min_target = 0.50
                    #     elif order_type == 'SELL' and (rev_target > -0.5 or min_target > -0.5):
                    #         rev_target = -0.50
                    #         min_target = -0.50
                    #
                    #     if (current_percent >= min_target and target_percent >= 1.5 and order_type == 'BUY') or \
                    #             (current_percent <= min_target and target_percent <= -1.5 and order_type == 'SELL'):
                    #         is_min_target = True
                    #
                    #     if (current_percent >= rev_target and target_percent >= 1.5 and order_type == 'BUY') or \
                    #             (current_percent <= rev_target and target_percent <= -1.5 and order_type == 'SELL'):
                    #         is_half_target = True
                    #
                    #     if (target_percent <= current_percent <= 20 and order_type == 'BUY') or \
                    #             (target_percent <= current_percent <= -20 and order_type == 'SELL'):
                    #         is_full_target = True
                    #         old_target_percent = target_percent
                    #         target_percent = target_percent * 2
                    #         target_price = round(float(buy_price + (buy_price * target_percent / 100)), 5)
                    #
                    #     if is_min_target and ((current_percent < min_target and order_type == 'BUY') or \
                    #                           (current_percent > min_target and order_type == 'SELL')):
                    #         is_exit_call = True
                    #         exit_method = "Min. target achieved and going down"
                    #
                    #     if is_half_target and ((current_percent < rev_target and order_type == 'BUY') or \
                    #                           (current_percent > rev_target and order_type == 'SELL')):
                    #         is_exit_call = True
                    #         exit_method = "Half target achieved and going down"
                    #
                    #     if is_full_target and ((current_percent < old_target_percent and order_type == 'BUY') or \
                    #                           (current_percent > old_target_percent and order_type == 'SELL')):
                    #         is_exit_call = True
                    #         exit_method = "Target achieved and going down"
                    # else:
                    #     is_exit_call = True
                    #     exit_method = "Target achieved and going down"

                    # update_query = """DELETE FROM `ant_cryptotradingbot`.`current_buy_order_report_future` WHERE `symbol_name`='{}' and `signal_type`='{}' and `order_quantity`=0 and `username`='{}';"""\
                    #     .format(symbol, signal_type, username)
                    # query_result = db_util.queryExecution(connection, update_query, 'update')

                    # is_exit = False
                    # sell_reason = ''
                    # if (f_current_price >= target_price and order_type == 'BUY') or (f_current_price <= target_price and order_type == 'SELL'):
                    #     is_exit = True
                    #     sell_reason = 'Target Achieved'
                    #     print('{} - Target achieved == price : {} ({} %) - Target : {} ({} %) ...'\
                    #           .format(symbol, f_current_price, current_percent, target_price, target_percent))
                    # elif (last_rsi >= RSI_OVERBOUGHT_SELL and current_percent > rev_target and order_type == 'BUY') or \
                    #         (last_rsi <= RSI_OVERBOUGHT_SELL and current_percent < rev_target and order_type == 'SELL'):
                    #     is_exit = True
                    #     sell_reason = 'RSI - Overbought'
                    #     print('{} - RSI Overbought reached == price : {} ({} %) - RSI : {} ...'\
                    #           .format(symbol, f_current_price, current_percent, last_rsi))
                    # elif is_exit_call:
                    #     is_exit = True
                    #     sell_reason = 'Other - ' + exit_method
                    #     print('{} - Exit call == price : {} ({} %) - {} ...'\
                    #           .format(symbol, f_current_price, current_percent, exit_method))
                    # elif f_current_price <= stop_loss:  # or last_rsi <= RSI_OVERSOLD
                    #     is_exit = True
                    #     sell_reason = 'Stop loss hit'
                    #     print('{} - Stoploss hitting == price : {} ({} %) - Stoploss : {} ({} %) ...'\
                    #           .format(symbol, f_current_price, current_percent, stop_loss, stoploss_percent))

                    if prev_order_price != buy_price:
                        buy_or_sell(symbol, close_ordertype, signal_type, in_position, nthread, ordered_qty, order_id=0, open_price=buy_price, ordered_price=target_price)
                        break

                    if trade_type == 'live':
                        '''Live Trade'''
                        currnt_busd_bal = float(getBalance('USDT'))
                    else:
                        '''Mock Trade'''
                        with open(busd_bal_txt, 'r') as busd:
                            currnt_busd_bal = float(busd.readline())
                            busd.close()
                    ## Re-purchase
                    # if ((f_current_price <= repurchase_price and order_type == 'BUY') or (f_current_price >= repurchase_price and order_type == 'SELL')) and currnt_busd_bal >= 50:
                    #     in_position, buy_price, ordered_qty, order_id, signal_type = buy_or_sell(symbol, order_type, signal_type, in_position,
                    #                                                       nthread, sell_reason='repurchase', order_id=order_id)
                    #     select_query = """SELECT `order_seq_id`,`symbol_name`,`signal_type`,`order_quantity`,`buy_price`,`order_date` FROM `ant_cryptotradingbot`.`current_buy_order_report_future` WHERE `username`='{}' and `symbol_name` = '{}';""" \
                    #         .format(username, symbol)
                    #     if order_type == 'SELL':
                    #         select_query = """SELECT `order_seq_id`,`symbol_name`,`signal_type`,`order_quantity`,`sell_price`,`order_date` FROM `ant_cryptotradingbot`.`current_buy_order_report_future` WHERE `username`='{}' and `symbol_name` = '{}';""" \
                    #             .format(username, symbol)
                    #
                    #     select_query_result = db_util.queryExecution(connection, select_query, 'select')
                    #     ordered_qty = float(select_query_result[0][3])
                    #     buy_price = float(select_query_result[0][4])

                    dt_today = datetime.today()  # Local time
                    dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
                    trade_date = str(dt_India.strftime('%Y-%m-%d %H:%M:%S'))
                    print('{} :::: {} :: {} - {} ==::== {} - Time sleep for : 1 minute..... - qty : {} :: avg price : {} -- current price : {} ({} %) - Target : {} ({} %) - Re-purchase : {} ({} %) - RSI : {} - DB Update : {}'\
                          .format(order_type, trade_date, username, nthread, symbol, ordered_qty, buy_price, f_current_price, current_percent,
                                  target_price, target_percent, repurchase_price, repurchase_percent, last_rsi, str(query_result)))
                    connection.close()
                    time.sleep(60)
                gc.collect()
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - trade_logic :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print(symbol + ' - ' + error_log)
    finally:
        gc.collect()


def buy_or_sell(symbol, buy_sell, signal_type, in_position_entry, order_seq, qty=0, sell_reason='', order_id=0, open_price=0, ordered_price=0):
    exchange = exchange_init()
    symbol_info = exchange.fetch_ticker(symbol)['info']
    cur_price = round(float(symbol_info['askPrice']), 8)
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
        time.sleep(5)
        if trade_type == 'live':
            '''Live Trade'''
            currnt_busd_bal = float(getBalance('USDT'))
        else:
            '''Mock Trade'''
            with open(busd_bal_txt, 'r') as busd:
                currnt_busd_bal = float(busd.readline())
                busd.close()

        if currnt_busd_bal > BUY_AMT and (not(in_position_entry) or sell_reason == 'repurchase'):
            # buy_amount = BUY_AMT
            # if os.path.exists(current_dir+'supertrend_current_buy_log.txt'):
            #     buy_amount = currnt_busd_bal
            # else:
            #     buy_amount = currnt_busd_bal / 2

            symbol_info = exchange.fetch_ticker(symbol)['info']
            cur_price = round(float(symbol_info['bidPrice']), 8)
            qty = int(round(float(BUY_AMT), 4) / cur_price)
            while (float(qty)*cur_price) > BUY_AMT:
                qty -= 1
                symbol_info = exchange.fetch_ticker(symbol)['info']
                cur_price = round(float(symbol_info['bidPrice']), 8)
            symbol_info = exchange.fetch_ticker(symbol)['info']
            cur_bid_price = round(float(symbol_info['bidPrice']), 8)
            connection = db_util.connect_database()
            if connection.is_connected():
                select_query = """SELECT `order_seq_id`,`symbol_name`,`signal_type`,`order_quantity`,`buy_price`,`order_date` FROM `ant_cryptotradingbot`.`current_buy_order_report_future` WHERE `username`='{}' and `symbol_name` = '{}';""" \
                    .format(username, symbol)
                if buy_sell == 'BUY' and sell_reason != 'repurchase':
                    select_query = """SELECT `order_seq_id`,`symbol_name`,`signal_type`,`order_quantity`,`sell_price`,`order_date` FROM `ant_cryptotradingbot`.`current_buy_order_report_future` WHERE `username`='{}' and `symbol_name` = '{}';""" \
                        .format(username, symbol)
                select_query_result = db_util.queryExecution(connection, select_query, 'select')
                if len(select_query_result) > 0 and sell_reason != 'repurchase':
                    return False, 0, 0, 0, signal_type
                elif len(select_query_result) == 0 or sell_reason == 'repurchase':
                    qty = qty * 20
                    if sell_reason == 'repurchase':
                        print('{} - {} - {} - {}'.format(type(select_query_result[0][3]), type(select_query_result[0][4]), type(qty), type(cur_bid_price)))
                        total_amount = (float(select_query_result[0][3]) * float(select_query_result[0][4]))\
                                    + (float(qty) * float(cur_bid_price))
                        cum_qty = float(select_query_result[0][3]) + float(qty)
                        cur_price = float(total_amount) / cum_qty
                        query_1 = """UPDATE `ant_cryptotradingbot`.`current_buy_order_report_future` SET `order_quantity`={},`buy_price`={} ,`order_date`='{}' 
                        WHERE `symbol_name`='{}' and `signal_type`='{}' and `username`='{}';""" \
                            .format(cum_qty, cur_price, trade_date, symbol, signal_type, username)
                        if buy_sell == 'SELL':
                            query_1 = """UPDATE `ant_cryptotradingbot`.`current_buy_order_report_future` SET `order_quantity`={},`sell_price`={} ,`order_date`='{}' 
                            WHERE `symbol_name`='{}' and `signal_type`='{}' and `username`='{}';""" \
                                .format(cum_qty, cur_price, trade_date, symbol, signal_type, username)
                    else:
                        query_1 = """INSERT INTO `ant_cryptotradingbot`.`current_buy_order_report_future` (`order_seq_id`,`symbol_name`,`signal_type`,
                        `order_quantity`,`buy_price`,`current_price`,`profit_percent`,`target_price`,`username`,`order_date`) 
                        VALUES({},'{}','{}',{},{},null,null,null,'{}','{}');""" \
                            .format(order_seq, symbol, signal_type, qty, cur_bid_price, username, trade_date)
                        if buy_sell == 'SELL':
                            query_1 = """INSERT INTO `ant_cryptotradingbot`.`current_buy_order_report_future` (`order_seq_id`,`symbol_name`,`signal_type`,
                            `order_quantity`,`sell_price`,`current_price`,`profit_percent`,`target_price`,`username`,`order_date`) 
                            VALUES({},'{}','{}',{},{},null,null,null,'{}','{}');""" \
                                .format(order_seq, symbol, signal_type, qty, cur_bid_price, username, trade_date)

                    query_result = db_util.queryExecution(connection, query_1, 'insert')

                if trade_type == 'live':
                    '''Live Trade'''
                    if order_id == 0:
                        print("Quantity:{},Symbol:{},price:{}".format(qty,symbol,cur_bid_price))
                        buy_order = client.futures_create_order(symbol=symbol, side=buy_sell, type='MARKET',
                                                                quantity=qty)
                        orderId = buy_order['orderId']
                        orderStatus = buy_order['status']
                    else:
                        orderId = order_id
                        orderStatus = 'NEW'
                    query_1 = """UPDATE `ant_cryptotradingbot`.`current_buy_order_report_future` SET `buy_orderID`={} 
                    WHERE `symbol_name`='{}' and `username`='{}';""" \
                        .format(orderId, symbol, username)
                    if buy_sell == 'SELL':
                        query_1 = """UPDATE `ant_cryptotradingbot`.`current_buy_order_report_future` SET `sell_orderID`={} 
                        WHERE `symbol_name`='{}' and `username`='{}';""" \
                            .format(orderId, symbol, username)

                    query_result = db_util.queryExecution(connection, query_1, 'update')
                    while orderStatus != 'FILLED' and orderStatus != 'CANCELED':
                        print("{} - {} ==::== {} is waiting for buy === qty: {} ;; price: {}"
                              .format(username, order_seq, symbol, qty, cur_bid_price))
                        time.sleep(60)
                        symbol_info = exchange.fetch_ticker(symbol)['info']
                        cur_price = round(float(symbol_info['bidPrice']), 8)
                        current_percent = round(float((cur_price - cur_bid_price) / (cur_bid_price / 100)), 2)
                        buy_order = client.futures_get_order(symbol=symbol, orderId=orderId)
                        orderStatus = buy_order['status']
                        dt_today = datetime.today()  # Local time
                        dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
                        current_date = str(datetime.strftime(dt_India, "%d%m%Y"))
                        if (current_percent > 2 and orderStatus == 'NEW' and sell_reason != 'repurchase') or (start_date != current_date):
                            cancel_order = client.futures_cancel_order(symbol=symbol, orderId=orderId)
                            query_1 = """DELETE FROM `ant_cryptotradingbot`.`current_buy_order_report_future` 
                            WHERE `symbol_name`='{}' and `signal_type`='{}' and `username`='{}' and `order_quantity`='{}';"""\
                                .format(symbol, signal_type, username, qty)
                            query_result = db_util.queryExecution(connection, query_1, 'update')
                            print("{} - {} ==::== {} is cancelled buy === qty: {} ;; price: {} - cancel :: {}"
                                  .format(username, order_seq, symbol, qty, cur_bid_price, cancel_order))
                            orderStatus = 'CANCELED'

                    buy_order = client.futures_get_order(symbol=symbol, orderId=orderId)
                    buy_status = buy_order['status']
                    if buy_status == 'FILLED':
                        buy_order['commisionPrice'] = 0.0000
                        if 'fills' in buy_order:
                            for buy_order_fills in buy_order['fills']:
                                buy_order['commisionPrice'] += round(float(buy_order_fills['commission']), 8)
                        ordered_qty = int(float(buy_order['executedQty']))
                        is_ordered = True
                else:
                    '''Mock Trade'''
                    symbol_info = exchange.fetch_ticker(symbol)['info']
                    # cur_price = round(float(symbol_info['askPrice']), 8)
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
                    if sell_reason == 'repurchase':
                        qty = select_query_result[0][3]
                        cur_bid_price = select_query_result[0][4]
                        old_trade_date = select_query_result[0][5]
                        query_1 = """UPDATE `ant_cryptotradingbot`.`current_buy_order_report_future` SET `order_quantity`={},`buy_price`={} ,`order_date`='{}' 
                        WHERE `order_seq_id`={} and `symbol_name`='{}' and `signal_type`='{}' and `username`='{}';""" \
                            .format(qty, cur_bid_price, old_trade_date, order_seq, symbol, signal_type,
                                    username)
                        if buy_sell == 'SELL':
                            query_1 = """UPDATE `ant_cryptotradingbot`.`current_buy_order_report_future` SET `order_quantity`={},`sell_price`={} ,`order_date`='{}' 
                            WHERE `order_seq_id`={} and `symbol_name`='{}' and `signal_type`='{}' and `username`='{}';""" \
                                .format(qty, cur_bid_price, old_trade_date, order_seq, symbol, signal_type,
                                        username)
                    else:
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
                #bnb_price = client.get_symbol_ticker(symbol='BNBUSDT')
                #buy_order['commisionPrice'] = float(buy_amount) * 0.6 / 100

                connection = db_util.connect_database()
                if connection.is_connected():
                    if sell_reason == 'repurchase':
                        select_query = """SELECT `order_seq_id`,`symbol_name`,`signal_type`,`order_quantity`,`buy_price`,`order_date` FROM `ant_cryptotradingbot`.`current_buy_order_report_future` WHERE `username`='{}' and `symbol_name` = '{}';""" \
                            .format(username, symbol)
                        if buy_sell == 'SELL':
                            select_query = """SELECT `order_seq_id`,`symbol_name`,`signal_type`,`order_quantity`,`sell_price`,`order_date` FROM `ant_cryptotradingbot`.`current_buy_order_report_future` WHERE `username`='{}' and `symbol_name` = '{}';""" \
                                .format(username, symbol)

                        select_query_result = db_util.queryExecution(connection, select_query, 'select')
                        buy_amount = ordered_qty * cur_price
                        buy_order['commisionPrice'] = float(buy_amount) * 0.6 / 100
                        ordered_qty = float(select_query_result[0][3])
                        cur_price = float(select_query_result[0][4])
                        cum_buy_amount = buy_order['avgPrice'] * qty
                        query = """UPDATE `ant_cryptotradingbot`.`order_report_future` SET `order_quantity`={},`buy_price`={},`buy_amount`={},
                        `order_date`='{}',`commission_price`=`commission_price`+{} 
                        WHERE `username`='{}' and `symbol_name`='{}' and `signal_type`='{}' and `sell_amount` is null;"""\
                                    .format(ordered_qty, cur_price,
                                            cum_buy_amount, trade_date, buy_order['commisionPrice'], username, symbol, signal_type)
                        if buy_sell == 'SELL':
                            query = """UPDATE `ant_cryptotradingbot`.`order_report_future` SET `order_quantity`={},`sell_price`={},`sell_amount`={},
                            `order_date`='{}',`commission_price`=`commission_price`+{} 
                            WHERE `username`='{}' and `symbol_name`='{}' and `signal_type`='{}' and `sell_amount` is null;""" \
                                .format(ordered_qty, cur_price,
                                        cum_buy_amount, trade_date, buy_order['commisionPrice'], username, symbol,
                                        signal_type)
                    else:
                        select_query = """SELECT count(`username`) from `ant_cryptotradingbot`.`order_report_future` WHERE `username`='{}';"""\
                            .format(username)
                        select_query_result = db_util.queryExecution(connection, select_query, 'select')
                        orderSeqId = int(select_query_result[0][0])+1
                        buy_amount = round(float(ordered_qty) * float(cur_price), 4)
                        query = """INSERT INTO `ant_cryptotradingbot`.`order_report_future` (`order_seq_id`,`symbol_name`,`signal_type`,`order_quantity`,`buy_price`,
                        `buy_amount`,`sell_price`,`sell_amount`,`profit_amount`,`profit_percent`,`username`,`order_date`,`update_date`,`commission_price`) 
                        VALUES ({},'{}','{}',{},{},{},null,null,null,null,'{}','{}',null, {});"""\
                                    .format(orderSeqId, symbol, signal_type, ordered_qty, cur_price,
                                            buy_amount, username, trade_date, buy_order['commisionPrice'])
                        if buy_sell == 'SELL':
                            query = """INSERT INTO `ant_cryptotradingbot`.`order_report_future` (`order_seq_id`,`symbol_name`,`signal_type`,`order_quantity`,`buy_price`,
                            `buy_amount`,`sell_price`,`sell_amount`,`profit_amount`,`profit_percent`,`username`,`order_date`,`update_date`,`commission_price`) 
                            VALUES ({},'{}','{}',{},null,null,{},{},null,null,'{}','{}',null, {});""" \
                                .format(orderSeqId, symbol, signal_type, ordered_qty, cur_price,
                                        buy_amount, username, trade_date, buy_order['commisionPrice'])

                    query_result = db_util.queryExecution(connection, query, 'insert')
                    if query_result:
                        w_ins_query = """UPDATE `ant_cryptotradingbot`.`ant_user_wallet` set `binance_exchange_usdt` = `binance_exchange_usdt` - {} WHERE `username` = '{}';""" \
                            .format(buy_amount, username)
                        wallet_query_result = db_util.queryExecution(connection, w_ins_query, 'update')
                        query_1 = """UPDATE `ant_cryptotradingbot`.`current_buy_order_report_future` SET `buy_orderID`={} 
                        WHERE `symbol_name`='{}' and `signal_type`='{}' and `username`='{}';""" \
                            .format(0, symbol, signal_type, username)
                        if buy_sell == 'SELL':
                            query_1 = """UPDATE `ant_cryptotradingbot`.`current_buy_order_report_future` SET `sell_orderID`={} 
                            WHERE `symbol_name`='{}' and `signal_type`='{}' and `username`='{}';""" \
                                .format(0, symbol, signal_type, username)
                        query_result = db_util.queryExecution(connection, query_1, 'update')
                    print(str(buy_order)+' - DB Insert : '+str(query_result))
                    connection.close()
                log = '{} - {} ==::== {} :: {} :: {} :: qty {}'.format(username, order_seq, 'Buy Order', symbol, str(cur_price), str(qty))
                print(log)
                print('Ordered Quantity is : ' + str(ordered_qty))
                in_position_entry = True
            else:
                print('{} - {} ==::== Buy ordered not done... for symbol : {}'.format(username, order_seq, symbol))
                in_position_entry = False
        elif in_position_entry:
            orderId = 0
            orderStatus = 'NEW'
            if trade_type == 'live':
                '''Live Trade'''
                symbol_info = exchange.fetch_ticker(symbol)['info']
                price_prec = 8
                high_price = float(exchange.fetch_ticker(symbol)['high'])
                low_price = float(exchange.fetch_ticker(symbol)['low'])
                price_prec_hg = len(str(high_price-int(high_price))[2:])
                price_prec_lw = len(str(low_price-int(low_price))[2:])
                if price_prec_hg >= price_prec_lw:
                    price_prec = price_prec_hg
                else:
                    price_prec = price_prec_lw

                if price_prec > 5:
                    price_prec = 5
                cur_ask_price = round(float(symbol_info['askPrice']), 8)
                if qty > 0:
                    if order_id == 0:
                        if cur_ask_price < ordered_price and buy_sell == 'BUY':
                            ordered_price = round(float(cur_ask_price + (cur_ask_price * 0.25 / 100)), price_prec)
                        elif cur_ask_price > ordered_price and buy_sell == 'SELL':
                            ordered_price = round(float(cur_ask_price - (cur_ask_price * 0.25 / 100)), price_prec)
                        sell_order = client.futures_create_order(symbol=symbol, side=buy_sell, type='TAKE_PROFIT_MARKET'
                                                                 , quantity=qty, stopprice=round(ordered_price,price_prec), closePosition='true')
                        orderId = sell_order['orderId']
                        orderStatus = sell_order['status']

                    connection = db_util.connect_database()
                    if connection.is_connected():
                        query_1 = """UPDATE `ant_cryptotradingbot`.`current_buy_order_report_future` SET `sell_orderID`={}, `close_orderDate`='{}' 
                        WHERE `symbol_name`='{}' and `signal_type`='{}' and `username`='{}';""" \
                            .format(orderId, trade_date, symbol, signal_type, username)
                        if buy_sell == 'BUY':
                            query_1 = """UPDATE `ant_cryptotradingbot`.`current_buy_order_report_future` SET `buy_orderID`={}, `close_orderDate`='{}' 
                            WHERE `symbol_name`='{}' and `signal_type`='{}' and `username`='{}';""" \
                                .format(orderId, trade_date, symbol, signal_type, username)
                        query_result = db_util.queryExecution(connection, query_1, 'update')
                        query = """UPDATE `ant_cryptotradingbot`.`order_report_future` SET `sell_price`={}, `sell_amount`={}  
                        WHERE `symbol_name`='{}' and `signal_type`='{}' and `order_quantity`={} and `update_date` is null and `username`='{}';""" \
                            .format(cur_ask_price, (cur_ask_price * qty), symbol, signal_type, round(float(qty), 2), username)
                        if buy_sell == 'BUY':
                            query = """UPDATE `ant_cryptotradingbot`.`order_report_future` SET `buy_price`={}, `buy_amount`={}  
                            WHERE `symbol_name`='{}' and `signal_type`='{}' and `order_quantity`={} and `update_date` is null and `username`='{}';""" \
                                .format(cur_ask_price, (cur_ask_price * qty), symbol, signal_type, round(float(qty), 2), username)
                        query_result = db_util.queryExecution(connection, query, 'update')
                        # stopOrderId = 0
                        # stopOrderStatus = ''
                        while orderStatus != 'FILLED':  # and stopOrderStatus != 'FILLED'
                            symbol_info = exchange.fetch_ticker(symbol)['info']
                            cur_price = round(float(symbol_info['askPrice']), 8)
                            current_percent = round(float((cur_price - open_price) / (open_price / 100)), 2)
                            print("{} - {} ==::== {} is waiting for {} === qty: {} ;; price: {} ;; current percent : {}"
                                  .format(username, order_seq, symbol, buy_sell, qty, ordered_price, current_percent))
                            time.sleep(15)
                            sell_order = client.futures_get_order(symbol=symbol, orderId=orderId, side=buy_sell)
                            orderStatus = sell_order['status']
                            dt_today = datetime.today()  # Local time
                            dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
                            current_date = str(datetime.strftime(dt_India, "%d%m%Y"))
                        #     if (((current_percent < -0.5 and buy_sell == 'BUY') or (current_percent > 0.5 and buy_sell == 'SELL')) and orderStatus == 'NEW'):
                        #         client.futures_cancel_order(symbol=symbol, side=buy_sell, orderId=orderId)
                        #         if stopOrderId > 0:
                        #             client.futures_cancel_order(symbol=symbol, side=buy_sell, orderId=stopOrderId)
                        #         stop_price = open_price
                        #         open_price = ordered_price
                        #         if cur_price < ordered_price and buy_sell == 'BUY':
                        #             ordered_price = round(float(cur_ask_price + (cur_ask_price * 2 / 100)), 8)
                        #         elif cur_price > ordered_price and buy_sell == 'SELL':
                        #             ordered_price = round(float(cur_ask_price - (cur_ask_price * 2 / 100)), 8)
                        #         sell_order = client.futures_create_order(symbol=symbol, side=buy_sell,
                        #                                                  type='TAKE_PROFIT_MARKET'
                        #                                                  , quantity=qty, stopprice=round(ordered_price,price_prec),
                        #                                                  closePosition='true')
                        #         orderId = sell_order['orderId']
                        #         orderStatus = sell_order['status']
                        #         stop_order = client.futures_create_order(symbol=symbol, side=buy_sell,
                        #                                                  type='STOP_MARKET'
                        #                                                  , quantity=qty, stopprice=round(stop_price,price_prec),
                        #                                                  closePosition='true')
                        #         stopOrderId = stop_order['orderId']
                        #         stopOrderStatus = stop_order['status']
                        #
                        # stop_order = client.futures_get_order(symbol=symbol, orderId=stopOrderId, side=buy_sell)
                        # if stop_order['status'] == 'FILLED':
                        #     orderId = stopOrderId
                        sell_order = client.futures_get_order(symbol=symbol, orderId=orderId, side=buy_sell)
                        if sell_order['status'] == 'FILLED':
                            query_1 = """UPDATE `ant_cryptotradingbot`.`current_buy_order_report_future` SET `sell_orderID`={}, `sell_price`={}
                            WHERE `symbol_name`='{}' and `signal_type`='{}' and `username`='{}';""" \
                                .format(orderId, ordered_price, symbol, signal_type, username)
                            if buy_sell == 'BUY':
                                query_1 = """UPDATE `ant_cryptotradingbot`.`current_buy_order_report_future` SET `buy_orderID`={}, `buy_price`={}
                                WHERE `symbol_name`='{}' and `signal_type`='{}' and `username`='{}';""" \
                                    .format(orderId, ordered_price, symbol, signal_type, username)

                            query_result = db_util.queryExecution(connection, query_1, 'update')
                            cur_price = round((float(sell_order['avgPrice'])), 8)
                            ordered_qty = int(float(sell_order['executedQty']))
                            # currnt_busd_bal = round(float(getBalance('BUSD')), 2)
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
                cur_price = round(float(symbol_info['askPrice']), 8)
                ordered_qty = qty
                sell_order = {'commisionPrice': 0.0000, 'cummulativeQuoteQty': float(ordered_qty * cur_price)}
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
                    sell_amount = round(float(ordered_qty) * float(cur_price), 4)
                    sell_order['commisionPrice'] = sell_amount * 0.6 / 100
                    if buy_sell == 'BUY':
                        select_query = """SELECT `sell_amount` from `ant_cryptotradingbot`.`order_report_future` 
                        WHERE `symbol_name`='{}' and `signal_type`='{}' and `order_quantity`={} and `update_date` is null and `username`='{}';""" \
                            .format(symbol, signal_type, round(float(ordered_qty), 2), username)
                        select_query_result = db_util.queryExecution(connection, select_query, 'select')
                        buy_amount = round(float(ordered_qty) * float(cur_price), 4)
                        sell_amount = float(select_query_result[0][0])
                        sell_order['commisionPrice'] = buy_amount * 0.6 / 100

                    profit_loss = round((sell_amount - buy_amount), 2)
                    percentage = round((profit_loss * 100) / buy_amount, 2)

                    query = """UPDATE `ant_cryptotradingbot`.`order_report_future` SET `sell_price`={},`sell_amount`={},`profit_amount`={},`profit_percent`={},`update_date`='{}', `sell_reason`='{}', `commission_price`=`commission_price`+{} 
                    WHERE `symbol_name`='{}' and `signal_type`='{}' and `order_quantity`={} and `update_date` is null and `username`='{}';"""\
                        .format(cur_price, sell_amount, profit_loss, percentage, trade_date, sell_reason, sell_order['commisionPrice'], symbol, signal_type, round(float(ordered_qty), 2), username)
                    if buy_sell == 'BUY':
                        query = """UPDATE `ant_cryptotradingbot`.`order_report_future` SET `buy_price`={},`buy_amount`={},`profit_amount`={},`profit_percent`={},`update_date`='{}', `sell_reason`='{}', `commission_price`=`commission_price`+{} 
                        WHERE `symbol_name`='{}' and `signal_type`='{}' and `order_quantity`={} and `update_date` is null and `username`='{}';""" \
                            .format(cur_price, buy_amount, profit_loss, percentage, trade_date, sell_reason,
                                    sell_order['commisionPrice'], symbol, signal_type, round(float(ordered_qty), 2),
                                    username)
                    query_1 = """DELETE FROM `ant_cryptotradingbot`.`current_buy_order_report_future` 
                    WHERE `symbol_name`='{}' and `signal_type`='{}' and `order_quantity`={} and `username`='{}';"""\
                        .format(symbol, signal_type, round(float(ordered_qty), 2), username)
                    query_result = db_util.queryExecution(connection, query, 'update')
                    if query_result:
                        query_result = db_util.queryExecution(connection, query_1, 'update')
                        w_ins_query = """UPDATE `ant_cryptotradingbot`.`ant_user_wallet` set `binance_exchange_usdt` = `binance_exchange_usdt`+{} WHERE `username` = '{}';""" \
                            .format(sell_amount, username)
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
                log = '{} - {} ==::== {} :: {} :: {} :: qty {}'.format(username, order_seq, 'Sell Order', symbol, str(cur_price), str(qty))
                print(log)
                in_position_entry = False
            else:
                print('{} - {} ==::== Close ordered not done... for symbol : {}'.format(username, order_seq, symbol))
                in_position_entry = True
        else:
            print(symbol + ' - ' + 'nothing to do... in buy / sell block...')
        gc.collect()
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - Buy_Sell :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print('Error: - Buy_Sell block error - {} ; qty - {} ; price - {}'.format(error_log, str(qty), cur_price))
    finally:
        gc.collect()
        return in_position_entry, cur_price, ordered_qty, 0, signal_type


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
                    w_ins_query = """UPDATE `ant_cryptotradingbot`.`ant_user_wallet` set `initial_investment_future`={}, `binance_exchange_usdt`= {} WHERE `username`='{}';""" \
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
                    dpr_start_amount = round(float(dpr_bal_query_result[0][1]), 2)
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
                dpr_start_amount = round(float(dpr_query_result[0][0]), 2)
                dpr_end_amount = dpr_start_amount + profit_amount
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

                select_query = """SELECT `symbol_name`,`signal_type`,`order_quantity`,`buy_price`,`sell_price`, `buy_orderID`, `sell_orderID` FROM `ant_cryptotradingbot`.`current_buy_order_report_future` WHERE `username`='{}' and `order_seq_id`={};"""\
                    .format(username, nthread)
                select_query_result = db_util.queryExecution(connection, select_query, 'select')
                pw_select_query = """SELECT `energy_power` FROM `ant_cryptotradingbot`.`ant_user_data` WHERE `username`='{}';"""\
                    .format(username)
                pw_query_result = db_util.queryExecution(connection, pw_select_query, 'select')
                if (int(curr_busd_bal) >= BUY_AMT or len(select_query_result) > 0) and int(pw_query_result[0][0]) >= 30:
                    trade_logic(select_query_result, nthread)
                    print('Time sleep for : 1 second.....')
                    time.sleep(1)
                elif int(pw_query_result[0][0]) < 30:
                    print('{} - {} ==::== Current Energy balance balance is < 30 (Energy Power {})'.format(username, nthread, str(pw_query_result[0][0])))
                else:
                    print('{} - {} ==::== Current USDT balance is < {} (USDT {})'.format(username, nthread, str(BUY_AMT), curr_busd_bal))
                connection.close()
            print('{} - {} ==::== Time sleep for : 1 minutes.....'.format(username, nthread))
            gc.collect()
            time.sleep(59)
        except Exception as ex:
            error_log = str(ex).replace('\'', '\'\'') + " - trade_logic :: line ::" \
                        + str(sys.exc_info()[2].tb_lineno)
            print('Error: - Start trade block error - {}'.format(error_log))
            continue


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

        print(username, ' ==::== ', str(busd_bal))
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
            select_orderseq_query = """select order_seq_id from `ant_cryptotradingbot`.`current_buy_order_report_future` WHERE `username`='{}' order by order_seq_id asc;""" \
                .format(username)
            select_orderseq_query_result = db_util.queryExecution(connection, select_orderseq_query, 'select')
            ord_seq = 0
            for rq in select_orderseq_query_result:
                update_query = """update `ant_cryptotradingbot`.`current_buy_order_report_future` set order_seq_id={} where `username`='{}' and order_seq_id={};""" \
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
            connection.close()
            print(username, ' ==::== ', nthread_count)
            for r in range(0, nthread_count):
                x = threading.Thread(target=start_trade, args=(r,))
                x.start()
                print('Time sleep for : 1 minutes......')
                time.sleep(60)
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - main :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print('Error: - Main error - {}'.format(error_log))
        print('Time sleep for : 1 min......')
        time.sleep(60)
