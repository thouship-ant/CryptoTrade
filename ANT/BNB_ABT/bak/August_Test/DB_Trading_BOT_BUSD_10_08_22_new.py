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
import time, sys, os, gc
from pytz import timezone
from utils import supRes_level as srl


def exchange_init():
    bin_exchange = ccxt.binance()
    return bin_exchange


def getBalance(symbol):
    info = client.get_account()
    bal = info['balances']
    is_locked = False
    symbol_bal = 0.00
    for b in bal:
        if b['asset'] == symbol and float(b['free']) > 0 and float(b['locked']) == 0:
            symbol_bal = float(b['free'])
            break
        elif b['asset'] == symbol and float(b['locked']) > 0 and symbol != 'BUSD':
            symbol_bal = float(b['locked'])
            is_locked = True
            break
        elif b['asset'] == symbol and symbol == 'BUSD':
            symbol_bal = float(b['free'])
            is_locked = False
            break
    return symbol_bal


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
    try:
        exchange = exchange_init()
        if len(select_query_result) > 0:
            symbol = select_query_result[0][0]
            signal_type = select_query_result[0][1]
            ordered_qty = float(select_query_result[0][2])
            buy_price = float(select_query_result[0][3])
            buy_orderID = float(select_query_result[0][4])
            sell_orderID = float(select_query_result[0][5])
            in_position = True
        else:
            in_position = False
            buy_price = 0.00
            buy_orderID = 0
            sell_orderID = 0
            ordered_qty = 0
            signal_type = ''

        if sell_orderID > 0:
            in_position = True
        elif buy_orderID > 0:
            in_position, buy_price, ordered_qty = buy_or_sell(symbol, 1.0, signal_type, in_position, nthread, order_id=buy_orderID)
        elif not(in_position):
            connection = db_util.connect_database()
            if connection.is_connected():
                query = """SELECT csd.`symbol_name`, `current_askPrice`, `upper_BBand_price`, `middle_BBand_price`, `lower_BBand_price`, `MACD_dif`, `MACD_dem`, `MACD_macd`, `last_RSI`, `2hrs_ST`, csd.`last_update_DateTime`, csmsd.sum_dem_macd_prv, csmsd.sum_dem_macd_current FROM `ant_cryptotradingbot`.`crypto_symbols_data` as csd 
                INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_macd_st_data` as csmsd on csd.symbol_name = csmsd.symbol_name 
                INNER JOIN `ant_cryptotradingbot`.`live_patterns_signal` as lps on csd.symbol_name = lps.symbol_name 
                WHERE (csd.upper_BBand_price > csd.current_askPrice 
                and (csd.middle_BBand_price < csd.current_askPrice or ((csd.middle_BBand_price + csd.lower_BBand_price)/2) < csd.current_askPrice)) 
                and csmsd.sum_dem_macd_current >= 0 and csmsd.sum_dem_macd_prv < csmsd.sum_dem_macd_current and csd.MACD_dem <= 0 and csd.MACD_macd > 0 and csd.last_RSI < 55 
                and lps.`PatternName` in ('Inverted Hammer','Hammer','Piercing Pattern','Morning Star','Morning Doji Star','Three Advancing White Soldiers','Engulfing Pattern') 
                and lps.SignalType = 'bullish' and csd.`2hrs_ST` = True and csd.is_Active = True;"""
                symbols_list = db_util.queryExecution(connection, query, 'select')
                signal_type = 'MACD'
                if len(symbols_list) == 0:
                    query = query.replace("and csmsd.sum_dem_macd_prv < csmsd.sum_dem_macd_current and csd.MACD_dem <= 0",
                                          "and csmsd.`2hrs_ST_prv` = False and csmsd.`2hrs_ST_current` = True and csmsd.sum_dem_macd_prv < csmsd.sum_dem_macd_current")
                    symbols_list = db_util.queryExecution(connection, query, 'select')
                    signal_type = 'SuperTrend'
                if len(symbols_list) == 0:
                    query = """SELECT csd.`symbol_name`, `current_askPrice`, `upper_BBand_price`, `middle_BBand_price`, `lower_BBand_price`, `MACD_dif`, `MACD_dem`, `MACD_macd`, `last_RSI`, `2hrs_ST`, csd.`last_update_DateTime`, lps.`PatternName` FROM `ant_cryptotradingbot`.`crypto_symbols_data` as csd 
                    INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_macd_st_data` as csmsd on csd.symbol_name = csmsd.symbol_name 
                    INNER JOIN `ant_cryptotradingbot`.`live_patterns_signal` as lps on csd.symbol_name = lps.symbol_name 
                    WHERE csd.MACD_macd > 0 and csd.last_RSI < 60 and csd.`2hrs_ST` = True and csd.is_Active = True
                    and csmsd.sum_dem_macd_current >= 0 and csmsd.sum_dem_macd_prv < csmsd.sum_dem_macd_current 
                    and lps.`PatternName` in ('Inverted Hammer','Hammer','Piercing Pattern','Morning Star','Morning Doji Star','Three Advancing White Soldiers','Engulfing Pattern') and lps.SignalType = 'bullish';"""
                    symbols_list = db_util.queryExecution(connection, query, 'select')
                    signal_type = 'Pattern'

                if len(symbols_list) > 0:
                    # symbols_count = len(symbols_list)
                    # selected_symbol = symbols_list[randint(0, symbols_count-1)]
                    for selected_symbol in symbols_list:
                        symbol = selected_symbol[0]
                        if signal_type == "Pattern":
                            signal_type += '-' + selected_symbol[11]

                        is_entry_point = False
                        ss, rr = srl.main(symbol)
                        symbol_info = exchange.fetch_ticker(symbol)['info']
                        cur_ask_price = round(float(symbol_info['askPrice']), 8)
                        ss_trim = ss[-2:]
                        rr_trim = rr[-2:]
                        sup_count = 0
                        lst_support = []
                        lst_resistance = []
                        for sup in ss_trim:
                            if sup[1] < cur_ask_price:
                                lst_support.append(sup[1])
                                is_entry_point = True
                                sup_count += 1
                        res_count = 0
                        if is_entry_point and sup_count == len(ss_trim):
                            for res in rr_trim:
                                if res[1] > cur_ask_price:
                                    lst_resistance.append(res[1])
                                    is_entry_point = True
                                    res_count += 1
                            # if res_count < len(rr_trim):
                            #     is_entry_point = False
                        else:
                            is_entry_point = False

                        if signal_type.startswith('Pattern'):
                            if len(lst_support) > 0 and len(lst_resistance) > 0 and is_entry_point:
                                lst_support.sort(reverse=True)
                                lst_resistance.sort()
                                dif_sup_price = float(lst_resistance[0] - lst_support[0])
                                avg_sup_price = float(lst_support[0] + (dif_sup_price/3))
                                print("Support: {}, Resistance: {} , dif_sup: {}, avg_sup: {}"
                                      .format(lst_support[0], lst_resistance[0], dif_sup_price, avg_sup_price))
                                if avg_sup_price < cur_ask_price:
                                    is_entry_point = False
                            else:
                                is_entry_point = False

                        symbol_df = get_data_frame(symbol)
                        closes = symbol_df['close'].tolist()
                        icloses = [float(c) for c in closes]
                        np_closes = np.array(icloses)
                        rsi = talib.RSI(np_closes, RSI_PERIOD)
                        last_rsi = round(float(rsi[-1]), 2)
                        if last_rsi <= 60 and is_entry_point and not(in_position):
                            in_position, buy_price, ordered_qty = buy_or_sell(symbol, 1.0, signal_type, in_position, nthread)
                            break
                else:
                    return

        if in_position:
            target_percent = 2
            repurchase_percent = -20
            is_half_target = False
            is_resistance_reach = False
            is_full_target = False
            old_target_percent = 0
            is_exit_call = False
            exit_method = ''
            while True:
                dt_today = datetime.today()  # Local time
                dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
                current_date = str(datetime.strftime(dt_India, "%d%m%Y"))
                if start_date != current_date:
                    break
                # symbol_info = exchange.fetch_ticker(symbol)['info']
                # cur_bid_price = round(float(symbol_info['bidPrice']), 8)
                # ss, rr = srl.main(symbol)
                # ss_trim = ss[-2:]
                # rr_trim = rr[-2:]
                # lst_support = []
                # lst_resistance = []
                # for sup in ss_trim:
                #     if sup[1] < cur_bid_price:
                #         lst_support.append(sup[1])
                #     if sup[1] > cur_bid_price:
                #         lst_resistance.append(sup[1])
                # lst_support.sort(reverse=True)
                # for res in rr_trim:
                #     if res[1] > cur_bid_price:
                #         lst_resistance.append(res[1])
                # lst_resistance.sort()
                connection = db_util.connect_database()
                if connection.is_connected():
                    # query = """SELECT csd.`symbol_name`, `current_askPrice`, `upper_BBand_price`, `middle_BBand_price`, `lower_BBand_price`, `MACD_dif`, `MACD_dem`, `MACD_macd`, csmsd.`sum_dem_macd_prv`, csmsd.`sum_dem_macd_current`, `last_RSI`, `2hrs_ST`, csd.`last_update_DateTime` FROM `ant_cryptotradingbot`.`crypto_symbols_data` as csd
                    # INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_macd_st_data` as csmsd on csd.symbol_name = csmsd.symbol_name
                    # INNER JOIN `ant_cryptotradingbot`.`live_patterns_signal` as lps on csd.symbol_name = lps.symbol_name
                    # WHERE ((csd.MACD_dem < 0 and csd.MACD_dif < 0 and csd.MACD_macd < 0) or (lps.`PatternName` in ('Hanging Man','Shooting Star','Evening Star','Evening Doji Star','Three Black Crows','Dark Cloud Cover','Engulfing Pattern') and lps.SignalType = 'bearish') or csd.last_RSI > {} or (csd.`15mins_ST` = False and csd.`2hrs_ST` = False)) and csd.`symbol_name`='{}'"""\
                    #     .format(RSI_OVERBOUGHT_SELL, symbol)
                    # if signal_type == 'SuperTrend':
                    #     query = """SELECT csd.`symbol_name`, `current_askPrice`, `upper_BBand_price`, `middle_BBand_price`, `lower_BBand_price`, `MACD_dif`, `MACD_dem`, `MACD_macd`, csmsd.`sum_dem_macd_prv`, csmsd.`sum_dem_macd_current`, `last_RSI`, `2hrs_ST`, csd.`last_update_DateTime` FROM `ant_cryptotradingbot`.`crypto_symbols_data` as csd
                    #     INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_macd_st_data` as csmsd on csd.symbol_name = csmsd.symbol_name
                    #     INNER JOIN `ant_cryptotradingbot`.`live_patterns_signal` as lps on csd.symbol_name = lps.symbol_name
                    #     WHERE ((csd.MACD_dem < 0 and csd.MACD_dif < 0 and csd.MACD_macd < 0) or (lps.`PatternName` in ('Hanging Man','Shooting Star','Evening Star','Evening Doji Star','Three Black Crows','Dark Cloud Cover','Engulfing Pattern') and lps.SignalType = 'bearish') or csd.last_RSI > {} or (csd.`15mins_ST` = False and csd.`2hrs_ST` = False)) and csd.`symbol_name`='{}'"""\
                    #         .format(RSI_OVERBOUGHT_SELL, symbol)
                    # if signal_type.startswith("Pattern"):
                    #     query = """SELECT csd.`symbol_name`, `current_askPrice`, `upper_BBand_price`, `middle_BBand_price`, `lower_BBand_price`, `MACD_dif`, `MACD_dem`, `MACD_macd`, csmsd.`sum_dem_macd_prv`, csmsd.`sum_dem_macd_current`, `last_RSI`, `2hrs_ST`, csd.`last_update_DateTime`, lps.`PatternName` FROM `ant_cryptotradingbot`.`crypto_symbols_data` as csd
                    #     INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_macd_st_data` as csmsd on csd.symbol_name = csmsd.symbol_name
                    #     INNER JOIN `ant_cryptotradingbot`.`live_patterns_signal` as lps on csd.symbol_name = lps.symbol_name
                    #     WHERE ((lps.`PatternName` in ('Hanging Man','Shooting Star','Evening Star','Evening Doji Star','Three Black Crows','Dark Cloud Cover','Engulfing Pattern') and lps.SignalType = 'bearish') and csd.last_RSI > {} and (csd.`15mins_ST` = False or csd.`2hrs_ST` = False)) and csd.`symbol_name`='{}';""" \
                    #         .format(RSI_OVERBOUGHT_SELL, symbol)
                    # symbols_list = db_util.queryExecution(connection, query, 'select')
                    # is_exit_call = False
                    # exit_method = ''
                    # if len(symbols_list) > 0:
                    #     is_exit_call = True
                    #     if not signal_type.startswith("Pattern"):
                    #         exit_method = signal_type
                    #     else:
                    #         exit_method = str(symbols_list[0][13])

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
                    target_price = round(float(buy_price + (buy_price * target_percent / 100)), 5)
                    repurchase_price = round(float(buy_price + (buy_price * repurchase_percent / 100)), 5)
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

                    repurchase_percent = round(float((repurchase_price - buy_price) / (buy_price / 100)), 2)
                    target_percent = round(float((target_price - buy_price) / (buy_price / 100)), 2)

                    rev_target = target_percent / 2
                    if current_percent >= rev_target and target_percent >= 1.5:
                        is_half_target = True

                    if target_percent <= current_percent <= 20:
                        is_full_target = True
                        old_target_percent = target_percent
                        target_percent = target_percent * 2
                        target_price = round(float(buy_price + (buy_price * target_percent / 100)), 5)

                    if is_half_target and current_percent < rev_target:
                        is_exit_call = True
                        exit_method = "Half target achieved and going down"

                    if is_full_target and current_percent < old_target_percent:
                        is_exit_call = True
                        exit_method = "Target achieved and going down"

                    query_result = False
                    connection = db_util.connect_database()
                    if connection.is_connected():
                        update_query = """UPDATE `ant_cryptotradingbot`.`current_buy_order_report` SET `current_price`={},`profit_percent`={},`target_price`={},`target_percent`={},`stoploss_price`={},`stoploss_percent`={} 
                        WHERE `symbol_name`='{}' and `signal_type`='{}' and `order_quantity`={} and `username`='{}';"""\
                            .format(f_current_price, current_percent, target_price, target_percent, repurchase_price,
                                    repurchase_percent, symbol, signal_type, round(float(ordered_qty), 2), username)
                        query_result = db_util.queryExecution(connection, update_query, 'update')

                    is_exit = False
                    sell_reason = ''
                    if f_current_price >= target_price:
                        is_exit = True
                        sell_reason = 'Target Achieved'
                        print('{} - Target achieved == price : {} ({} %) - Target : {} ({} %) ...'\
                              .format(symbol, f_current_price, current_percent, target_price, target_percent))
                    elif last_rsi >= RSI_OVERBOUGHT_SELL and current_percent > rev_target:
                        is_exit = True
                        sell_reason = 'RSI - Overbought'
                        print('{} - RSI Overbought reached == price : {} ({} %) - RSI : {} ...'\
                              .format(symbol, f_current_price, current_percent, last_rsi))
                    elif is_exit_call:
                        is_exit = True
                        sell_reason = 'Other - ' + exit_method
                        print('{} - Exit call == price : {} ({} %) - {} ...'\
                              .format(symbol, f_current_price, current_percent, exit_method))
                    # elif f_current_price <= stop_loss:  # or last_rsi <= RSI_OVERSOLD
                    #     is_exit = True
                    #     sell_reason = 'Stop loss hit'
                    #     print('{} - Stoploss hitting == price : {} ({} %) - Stoploss : {} ({} %) ...'\
                    #           .format(symbol, f_current_price, current_percent, stop_loss, stoploss_percent))

                    if is_exit or sell_orderID > 0:
                        buy_or_sell(symbol, -1.0, signal_type, in_position, nthread, ordered_qty, sell_reason, order_id=sell_orderID)
                        break

                    ## Re-purchase
                    if f_current_price <= repurchase_price:
                        in_position, buy_price, ordered_qty = buy_or_sell(symbol, 1.0, signal_type, in_position,
                                                                          nthread, sell_reason='repurchase')
                        connection = db_util.connect_database()
                        if connection.is_connected():
                            select_query = """SELECT `order_seq_id`,`symbol_name`,`signal_type`,`order_quantity`,`buy_price`,`order_date` FROM `ant_cryptotradingbot`.`current_buy_order_report` WHERE `username`='{}' and `symbol_name` = '{}';""" \
                                .format(username, symbol)
                            select_query_result = db_util.queryExecution(connection, select_query, 'select')
                            ordered_qty = float(select_query_result[0][3])
                            buy_price = float(select_query_result[0][4])

                    dt_today = datetime.today()  # Local time
                    dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
                    trade_date = str(dt_India.strftime('%Y-%m-%d %H:%M:%S'))
                    print('{} :: {} - {} ==::== {} - Time sleep for : 1 minute..... - qty : {} :: avg buy price : {} -- current price : {} ({} %) - Target : {} ({} %) - Re-purchase : {} ({} %) - RSI : {} - DB Update : {}'\
                          .format(trade_date, username, nthread, symbol, ordered_qty, buy_price, f_current_price, current_percent,
                                  target_price, target_percent, repurchase_price, repurchase_percent, last_rsi, str(query_result)))
                    time.sleep(60)
                gc.collect()
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - trade_logic :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print(symbol + ' - ' + error_log)
    finally:
        gc.collect()


def buy_or_sell(symbol, buy_sell, signal_type, in_position_entry, order_seq, qty=0, sell_reason='', order_id=0):
    exchange = exchange_init()
    symbol_info = exchange.fetch_ticker(symbol.replace('USDT','BUSD'))['info']
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
        time.sleep(randint(15, 50))
        if trade_type == 'live':
            '''Live Trade'''
            currnt_busd_bal = float(getBalance('BUSD'))
        else:
            '''Mock Trade'''
            with open(busd_bal_txt, 'r') as busd:
                currnt_busd_bal = float(busd.readline())
                busd.close()

        if buy_sell == 1.0 and currnt_busd_bal > BUY_AMT: # and (last_rsi >= RSI_OVERSOLD and last_rsi <= RSI_OVERBOUGHT) # signal to buy (either compare with current price to but/sell or use limit order with value
            if not(in_position_entry) or sell_reason == 'repurchase':
                # buy_amount = BUY_AMT
                # if os.path.exists(current_dir+'supertrend_current_buy_log.txt'):
                #     buy_amount = currnt_busd_bal
                # else:
                #     buy_amount = currnt_busd_bal / 2

                symbol_info = exchange.fetch_ticker(symbol.replace('USDT', 'BUSD'))['info']
                cur_price = round(float(symbol_info['bidPrice']), 8)
                qty = int(round(float(BUY_AMT), 4) / cur_price)
                while (float(qty)*cur_price) > BUY_AMT:
                    qty -= 1
                    symbol_info = exchange.fetch_ticker(symbol.replace('USDT', 'BUSD'))['info']
                    cur_price = round(float(symbol_info['bidPrice']), 8)
                symbol_info = exchange.fetch_ticker(symbol.replace('USDT', 'BUSD'))['info']
                cur_bid_price = round(float(symbol_info['bidPrice']), 8)
                connection = db_util.connect_database()
                if connection.is_connected():
                    select_query = """SELECT `order_seq_id`,`symbol_name`,`signal_type`,`order_quantity`,`buy_price`,`order_date` FROM `ant_cryptotradingbot`.`current_buy_order_report` WHERE `username`='{}' and `symbol_name` = '{}';""" \
                        .format(username, symbol)
                    select_query_result = db_util.queryExecution(connection, select_query, 'select')
                    if len(select_query_result) == 0 or sell_reason == 'repurchase':
                        if sell_reason == 'repurchase':
                            print('{} - {} - {} - {}'.format(type(select_query_result[0][3]), type(select_query_result[0][4]), type(qty), type(cur_bid_price)))
                            total_amount = (float(select_query_result[0][3]) * float(select_query_result[0][4]))\
                                        + (float(qty) * float(cur_bid_price))
                            cum_qty = float(select_query_result[0][3]) + float(qty)
                            cur_price = float(total_amount) / cum_qty
                            query_1 = """UPDATE `ant_cryptotradingbot`.`current_buy_order_report` SET `order_quantity`={},`buy_price`={} ,`order_date`='{}' 
                            WHERE `symbol_name`='{}' and `signal_type`='{}' and `username`='{}';""" \
                                .format(cum_qty, cur_price, trade_date, symbol, signal_type, username)
                        else:
                            query_1 = """INSERT INTO `ant_cryptotradingbot`.`current_buy_order_report` (`order_seq_id`,`symbol_name`,`signal_type`,
                            `order_quantity`,`buy_price`,`current_price`,`profit_percent`,`target_price`,`username`,`order_date`) 
                            VALUES({},'{}','{}',{},{},null,null,null,'{}','{}');""" \
                                .format(order_seq, symbol, signal_type, qty, cur_bid_price, username, trade_date)
                        query_result = db_util.queryExecution(connection, query_1, 'insert')
                        if trade_type == 'live':
                            '''Live Trade'''
                            if order_id == 0:
                                buy_order = client.order_limit_buy(symbol=symbol.replace('USDT', 'BUSD'), quantity=qty,
                                                                   price=cur_bid_price)
                                orderId = buy_order['orderId']
                                orderStatus = buy_order['status']
                            else:
                                orderId = order_id
                                orderStatus = 'NEW'
                            query_1 = """UPDATE `ant_cryptotradingbot`.`current_buy_order_report` SET `buy_orderID`={} 
                            WHERE `symbol_name`='{}' and `signal_type`='{}' and `username`='{}';""" \
                                .format(orderId, symbol, signal_type, username)
                            query_result = db_util.queryExecution(connection, query_1, 'update')
                            while orderStatus == 'NEW':
                                print("{} - {} ==::== {} is waiting for buy === qty: {} ;; price: {}"
                                      .format(username, order_seq, symbol.replace('USDT', 'BUSD'), qty, cur_bid_price))
                                time.sleep(60)
                                symbol_info = exchange.fetch_ticker(symbol.replace('USDT', 'BUSD'))['info']
                                cur_price = round(float(symbol_info['bidPrice']), 8)
                                current_percent = round(float((cur_price - cur_bid_price) / (cur_bid_price / 100)), 2)
                                buy_order = client.get_order(symbol=symbol.replace('USDT', 'BUSD'), orderId=orderId)
                                orderStatus = buy_order['status']
                                dt_today = datetime.today()  # Local time
                                dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
                                current_date = str(datetime.strftime(dt_India, "%d%m%Y"))
                                if (current_percent > 2 and orderStatus == 'NEW' and sell_reason != 'repurchase') or (start_date != current_date):
                                    cancel_order = client.cancel_order(symbol=symbol.replace('USDT', 'BUSD'), orderId=orderId)
                                    query_1 = """UPDATE `ant_cryptotradingbot`.`current_buy_order_report` SET `buy_orderID`={} 
                                    WHERE `symbol_name`='{}' and `signal_type`='{}' and `username`='{}';""" \
                                        .format(0, symbol, signal_type, username)
                                    query_result = db_util.queryExecution(connection, query_1, 'update')
                                    print("{} - {} ==::== {} is cancelled buy === qty: {} ;; price: {} - cancel :: {}"
                                          .format(username, order_seq, symbol.replace('USDT', 'BUSD'), qty, cur_bid_price, cancel_order))
                                    orderStatus = 'CANCELED'

                            buy_order = client.get_order(symbol=symbol.replace('USDT', 'BUSD'), orderId=orderId)
                            buy_status = buy_order['status']
                            if buy_status == 'FILLED':
                                buy_order['commisionPrice'] = 0.0000
                                if 'fills' in buy_order:
                                    for buy_order_fills in buy_order['fills']:
                                        buy_order['commisionPrice'] += round(float(buy_order_fills['commission']), 8)
                                cur_price = round(
                                    (float(buy_order['cummulativeQuoteQty']) / float(buy_order['executedQty'])), 8)
                                ordered_qty = int(float(buy_order['executedQty']))
                                is_ordered = True
                        else:
                            '''Mock Trade'''
                            symbol_info = exchange.fetch_ticker(symbol.replace('USDT', 'BUSD'))['info']
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
                                query_1 = """UPDATE `ant_cryptotradingbot`.`current_buy_order_report` SET `order_quantity`={},`buy_price`={} ,`order_date`='{}' 
                                WHERE `order_seq_id`={} and `symbol_name`='{}' and `signal_type`='{}' and `username`='{}';""" \
                                    .format(qty, cur_bid_price, old_trade_date, order_seq, symbol, signal_type,
                                            username)
                            else:
                                query_1 = """DELETE FROM `ant_cryptotradingbot`.`current_buy_order_report` WHERE `order_seq_id`={} and `symbol_name`='{}' and `signal_type`='{}'
                                                        and `order_quantity`={} and `buy_price`={} and `username`='{}' and `order_date`='{}';""" \
                                .format(order_seq, symbol, signal_type, qty, cur_bid_price, username, trade_date)
                            query_result = db_util.queryExecution(connection, query_1, 'insert')
                    connection.close()

                if is_ordered:
                    bnb_price = client.get_symbol_ticker(symbol='BNBBUSD')
                    buy_order['commisionPrice'] = buy_order['commisionPrice'] * float(bnb_price['price'])

                    connection = db_util.connect_database()
                    if connection.is_connected():
                        if sell_reason == 'repurchase':
                            select_query = """SELECT `order_seq_id`,`symbol_name`,`signal_type`,`order_quantity`,`buy_price`,`order_date` FROM `ant_cryptotradingbot`.`current_buy_order_report` WHERE `username`='{}' and `symbol_name` = '{}';""" \
                                .format(username, symbol)
                            select_query_result = db_util.queryExecution(connection, select_query, 'select')
                            buy_amount = ordered_qty * cur_price
                            ordered_qty = float(select_query_result[0][3])
                            cur_price = float(select_query_result[0][4])
                            cum_buy_amount = ordered_qty * cur_price
                            query = """UPDATE `ant_cryptotradingbot`.`order_report` SET `order_quantity`={},`buy_price`={},`buy_amount`={},
                            `order_date`='{}',`commission_price`=`commission_price`+{} 
                            WHERE `username`='{}' and `symbol_name`='{}' and `signal_type`='{}' and `sell_amount` is null;"""\
                                        .format(ordered_qty, cur_price,
                                                cum_buy_amount, trade_date, buy_order['commisionPrice'], username, symbol, signal_type)
                        else:
                            select_query = """SELECT count(`username`) from `ant_cryptotradingbot`.`order_report` WHERE `username`='{}';"""\
                                .format(username)
                            select_query_result = db_util.queryExecution(connection, select_query, 'select')
                            orderSeqId = int(select_query_result[0][0])+1
                            buy_amount = round(float(ordered_qty) * float(cur_price), 4)
                            query = """INSERT INTO `ant_cryptotradingbot`.`order_report` (`order_seq_id`,`symbol_name`,`signal_type`,`order_quantity`,`buy_price`,
                            `buy_amount`,`sell_price`,`sell_amount`,`profit_amount`,`profit_percent`,`username`,`order_date`,`update_date`,`commission_price`) 
                            VALUES ({},'{}','{}',{},{},{},null,null,null,null,'{}','{}',null, {});"""\
                                        .format(orderSeqId, symbol, signal_type, ordered_qty, cur_price,
                                                buy_amount, username, trade_date, buy_order['commisionPrice'])
                        query_result = db_util.queryExecution(connection, query, 'insert')
                        if query_result:
                            w_ins_query = """UPDATE `ant_cryptotradingbot`.`ant_user_wallet` set `binance_exchange_usdt` = `binance_exchange_usdt` - {} WHERE `username` = '{}';""" \
                                .format(buy_amount, username)
                            wallet_query_result = db_util.queryExecution(connection, w_ins_query, 'update')
                            query_1 = """UPDATE `ant_cryptotradingbot`.`current_buy_order_report` SET `buy_orderID`={} 
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
                    print('{} - {} ==::== Buy ordered not done... for symbol : {}'.format(username, order_seq, symbol.replace('USDT', 'BUSD')))
                    in_position_entry = False
        elif buy_sell == -1.0:  # and (last_rsi <= RSI_OVERSOLD or last_rsi >= RSI_OVERBOUGHT) # signal to sell (either compare with current price to but/sell or use limit order with value
            if in_position_entry:
                if trade_type == 'live':
                    '''Live Trade'''
                    symbol_info = exchange.fetch_ticker(symbol.replace('USDT', 'BUSD'))['info']
                    cur_ask_price = round(float(symbol_info['askPrice']), 8)
                    currnt_currency_bal = int(getBalance(symbol.replace('USDT', '')))
                    if currnt_currency_bal >= qty:
                        if order_id == 0:
                            sell_order = client.order_limit_sell(symbol=symbol.replace('USDT', 'BUSD'), quantity=qty, price=cur_ask_price)
                            orderId = sell_order['orderId']
                            orderStatus = sell_order['status']
                        else:
                            orderId = order_id
                            orderStatus = 'NEW'

                        connection = db_util.connect_database()
                        if connection.is_connected():
                            query_1 = """UPDATE `ant_cryptotradingbot`.`current_buy_order_report` SET `sell_orderID`={}, `sell_orderDate`='{}' 
                            WHERE `symbol_name`='{}' and `signal_type`='{}' and `username`='{}';""" \
                                .format(orderId, trade_date, symbol, signal_type, username)
                            query_result = db_util.queryExecution(connection, query_1, 'update')
                            query = """UPDATE `ant_cryptotradingbot`.`order_report` SET `sell_price`={}  
                            WHERE `symbol_name`='{}' and `signal_type`='{}' and `order_quantity`={} and `update_date` is null and `username`='{}';""" \
                                .format(cur_ask_price, symbol, signal_type, round(float(qty), 2), username)
                            query_result = db_util.queryExecution(connection, query, 'update')
                            connection.close()
                        while orderStatus == 'NEW':
                            print("{} - {} ==::== {} is waiting for sell === qty: {} ;; price: {}"
                                  .format(username, order_seq, symbol.replace('USDT', 'BUSD'), qty, cur_ask_price))
                            time.sleep(60)
                            symbol_info = exchange.fetch_ticker(symbol.replace('USDT', 'BUSD'))['info']
                            cur_price = round(float(symbol_info['askPrice']), 8)
                            current_percent = round(float((cur_price - cur_ask_price) / (cur_ask_price / 100)), 2)
                            sell_order = client.get_order(symbol=symbol.replace('USDT', 'BUSD'), orderId=orderId)
                            orderStatus = sell_order['status']
                            dt_today = datetime.today()  # Local time
                            dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
                            current_date = str(datetime.strftime(dt_India, "%d%m%Y"))
                            if (current_percent < 2 and orderStatus == 'NEW') or (start_date != current_date):
                                cancel_order = client.cancel_order(symbol=symbol.replace('USDT', 'BUSD'), orderId=orderId)
                                query_1 = """UPDATE `ant_cryptotradingbot`.`current_buy_order_report` SET `sell_orderID`={}, `sell_orderDate`=null 
                                WHERE `symbol_name`='{}' and `signal_type`='{}' and `username`='{}';""" \
                                    .format(0, symbol, signal_type, username)
                                query_result = db_util.queryExecution(connection, query_1, 'update')
                                print("{} - {} ==::== {} is cancelled sell === qty: {} ;; price: {} - cancel :: {}"
                                      .format(username, order_seq, symbol.replace('USDT', 'BUSD'), qty, cur_ask_price, cancel_order))
                                orderStatus = 'CANCELED'

                        sell_order = client.get_order(symbol=symbol.replace('USDT', 'BUSD'), orderId=orderId)
                        if sell_order['status'] == 'FILLED':
                            sell_order['commisionPrice'] = 0.0000
                            if 'fills' in sell_order:
                                for sell_order_fills in sell_order['fills']:
                                    sell_order['commisionPrice'] += round(float(sell_order_fills['commission']), 8)
                            cur_price = round((float(sell_order['cummulativeQuoteQty']) / float(sell_order['executedQty'])), 8)
                            ordered_qty = int(float(sell_order['executedQty']))
                            # currnt_busd_bal = round(float(getBalance('BUSD')), 2)
                            is_ordered = True
                        else:
                            print("sell_order: ", sell_order)
                            query = """UPDATE `ant_cryptotradingbot`.`order_report` SET `sell_price`= null  
                            WHERE `symbol_name`='{}' and `signal_type`='{}' and `order_quantity`={} and `update_date` is null and `username`='{}';""" \
                                .format(symbol, signal_type, round(float(qty), 2), username)
                            query_result = db_util.queryExecution(connection, query, 'insert')
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
                        select_query = """SELECT `buy_amount` from `ant_cryptotradingbot`.`order_report` 
                        WHERE `symbol_name`='{}' and `signal_type`='{}' and `order_quantity`={} and `update_date` is null and `username`='{}';"""\
                            .format(symbol, signal_type, round(float(ordered_qty), 2), username)
                        select_query_result = db_util.queryExecution(connection, select_query, 'select')
                        if len(select_query_result) > 0:
                            currnt_busd_bal = round(float(currnt_busd_bal + sell_order['cummulativeQuoteQty']), 2)
                            with open(busd_bal_txt, 'w') as busd:
                                busd.write(str(currnt_busd_bal))
                                busd.close()
                            is_ordered = True
                        connection.close()

                if is_ordered:
                    bnb_price = client.get_symbol_ticker(symbol='BNBBUSD')
                    sell_order['commisionPrice'] = sell_order['commisionPrice'] * float(bnb_price['price'])

                    connection = db_util.connect_database()
                    if connection.is_connected():
                        select_query = """SELECT `buy_amount` from `ant_cryptotradingbot`.`order_report` 
                        WHERE `symbol_name`='{}' and `signal_type`='{}' and `order_quantity`={} and `update_date` is null and `username`='{}';"""\
                            .format(symbol, signal_type, round(float(ordered_qty), 2), username)
                        select_query_result = db_util.queryExecution(connection, select_query, 'select')
                        buy_amount = float(select_query_result[0][0])
                        sell_amount = round(float(ordered_qty) * float(cur_price), 4)
                        profit_loss = round((sell_amount - buy_amount), 2)
                        percentage = round((profit_loss * 100) / buy_amount, 2)

                        query = """UPDATE `ant_cryptotradingbot`.`order_report` SET `sell_price`={},`sell_amount`={},`profit_amount`={},`profit_percent`={},`update_date`='{}', `sell_reason`='{}', `commission_price`=`commission_price`+{} 
                        WHERE `symbol_name`='{}' and `signal_type`='{}' and `order_quantity`={} and `update_date` is null and `username`='{}';"""\
                            .format(cur_price, sell_amount, profit_loss, percentage, trade_date, sell_reason, sell_order['commisionPrice'], symbol, signal_type, round(float(ordered_qty), 2), username)
                        query_1 = """DELETE FROM `ant_cryptotradingbot`.`current_buy_order_report` 
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
                                query_1 = """UPDATE `ant_cryptotradingbot`.`current_buy_order_report` SET `sell_orderID`={}, `sell_orderDate`=null 
                                WHERE `symbol_name`='{}' and `signal_type`='{}' and `username`='{}';""" \
                                    .format(0, symbol, signal_type, username)
                                query_result = db_util.queryExecution(connection, query_1, 'update')

                        print(str(sell_order)+' - DB Update : '+str(query_result))
                        connection.close()
                    log = '{} - {} ==::== {} :: {} :: {} :: qty {}'.format(username, order_seq, 'Sell Order', symbol, str(cur_price), str(qty))
                    print(log)
                    in_position_entry = False
                else:
                    print('{} - {} ==::== Sell ordered not done... for symbol : {}'.format(username, order_seq, symbol.replace('USDT', 'BUSD')))
                    in_position_entry = True
        else:
            print(symbol + ' - ' + 'nothing to do... in buy / sell block...')
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - Buy_Sell :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print('Error: - Buy_Sell block error - {} ; qty - {} ; price - {}'.format(error_log, str(qty), cur_price))
    finally:
        gc.collect()
        return in_position_entry, cur_price, ordered_qty


def start_trade(nthread):
    while True:
        try:
            if trade_type == 'live':
                '''Live Trade'''
                curr_busd_bal = round(float(getBalance('BUSD')), 2)
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
                wallet_query = """SELECT `initial_investment` FROM `ant_cryptotradingbot`.`ant_user_wallet` where `username` = '{}'""" \
                    .format(username)
                wallet_query_result = db_util.queryExecution(connection, wallet_query, 'select')
                if wallet_query_result[0][0] == 0:
                    curr_busd_bal = round(float(curr_busd_bal), 2)
                    w_ins_query = """UPDATE `ant_cryptotradingbot`.`ant_user_wallet` set `initial_investment`={}, `binance_exchange_usdt`= {} WHERE `username`='{}';""" \
                        .format(curr_busd_bal, curr_busd_bal, username)
                    wallet_query_result = db_util.queryExecution(connection, w_ins_query, 'update')
                    print('New Wallet DBUpdated :: {}'.format(wallet_query_result))
                dpr_bal_query = """(select distinct auw.`initial_investment` as invest_amount, (auw.`binance_exchange_usdt`+(select sum(buy_amount) from `ant_cryptotradingbot`.`order_report` where username = '{}' and sell_amount is null)) as final_amount from `ant_cryptotradingbot`.`order_report` as ort inner join `ant_cryptotradingbot`.`ant_user_wallet` as auw on auw.username = ort.username where ort.username = '{}' and ort.sell_amount is null)
                union all
                (select distinct auw.`initial_investment` as invest_amount, auw.`binance_exchange_usdt` as final_amount from `ant_cryptotradingbot`.`order_report` as ort inner join `ant_cryptotradingbot`.`ant_user_wallet` as auw on auw.username = ort.username where ort.username = '{}' and ort.sell_amount is not null
                and (select count(buy_amount) from `ant_cryptotradingbot`.`order_report` where username = '{}' and sell_amount is null) = 0)
                union all
                (select distinct auw.`initial_investment` as invest_amount, auw.`binance_exchange_usdt` as final_amount from `ant_cryptotradingbot`.`ant_user_wallet` as auw left join `ant_cryptotradingbot`.`order_report` as ort on auw.username = ort.username where auw.username = '{}' and ort.username is null)""" \
                    .format(username, username, username, username, username)
                dpr_bal_query_result = db_util.queryExecution(connection, dpr_bal_query, 'select')
                drp_start_date = str(datetime.strftime(dt_India, "%Y-%m-%d"))
                dpr_query = """SELECT `start_amount` FROM `ant_cryptotradingbot`.`daily_profit_report` where `date` = '{}' and `username` = '{}'""" \
                    .format(drp_start_date, username)
                dpr_query_result = db_util.queryExecution(connection, dpr_query, 'select')
                if len(dpr_query_result) == 0:
                    dpr_start_amount = round(float(dpr_bal_query_result[0][1]), 2)
                    dpr_ins_query = """INSERT `ant_cryptotradingbot`.`daily_profit_report` (`date`, `username`, `start_amount`, `end_amount`, `update_date`) VALUES ('{}', '{}', {}, {}, '{}');""" \
                        .format(drp_start_date, username, dpr_start_amount, dpr_start_amount, trade_date)
                    dpr_query_result = db_util.queryExecution(connection, dpr_ins_query, 'insert')
                profit_amount = 0
                commission_amount = 0
                dpr_bal_query = """select sum(orp.profit_amount), sum(orp.commission_price) from 
                                (select cast(update_date as date) as `date`, profit_amount, commission_price from `ant_cryptotradingbot`.`order_report` where `username` = '{}') as orp
                                where orp.`date`='{}' group by orp.`date`""".format(username, drp_start_date)
                dpr_bal_query_result = db_util.queryExecution(connection, dpr_bal_query, 'select')
                if len(dpr_bal_query_result) > 0:
                    profit_amount = round(float(dpr_bal_query_result[0][0]), 2)
                    commission_amount = round(float(dpr_bal_query_result[0][1]), 2)
                print('Profit select of date ::: {} -- profit ::: {}'.format(drp_start_date, profit_amount))
                dpr_query = """SELECT `start_amount` FROM `ant_cryptotradingbot`.`daily_profit_report` where `date` = '{}' and `username` = '{}'""" \
                    .format(drp_trade_date, username)
                dpr_query_result = db_util.queryExecution(connection, dpr_query, 'select')
                dpr_start_amount = round(float(dpr_query_result[0][0]), 2)
                dpr_end_amount = dpr_start_amount + profit_amount
                profit_percent = round(
                    float((dpr_end_amount - commission_amount - dpr_start_amount) / (dpr_start_amount / 100)), 2)
                update_query = """UPDATE `ant_cryptotradingbot`.`daily_profit_report` 
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

                select_query = """SELECT `symbol_name`,`signal_type`,`order_quantity`,`buy_price`, `buy_orderID`, `sell_orderID` FROM `ant_cryptotradingbot`.`current_buy_order_report` WHERE `username`='{}' and `order_seq_id`={};"""\
                    .format(username, nthread)
                select_query_result = db_util.queryExecution(connection, select_query, 'select')
                pw_select_query = """SELECT `energy_power` FROM `ant_cryptotradingbot`.`ant_user_data` WHERE `username`='{}';"""\
                    .format(username)
                pw_query_result = db_util.queryExecution(connection, pw_select_query, 'select')
                if (int(curr_busd_bal) >= 100 or len(select_query_result) > 0) and int(pw_query_result[0][0]) >= 30:
                    trade_logic(select_query_result, nthread)
                    print('Time sleep for : 1 second.....')
                    time.sleep(1)
                elif int(pw_query_result[0][0]) < 30:
                    print('{} - {} ==::== Current Energy balance balance is < 30 (Energy Power {})'.format(username, nthread, str(pw_query_result[0][0])))
                else:
                    print('{} - {} ==::== Current BUSD balance is < 100 (BUSD {})'.format(username, nthread, curr_busd_bal))
                connection.close()
            print('{} - {} ==::== Time sleep for : 5 minutes.....'.format(username, nthread))
            gc.collect()
            time.sleep(299)
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
            busd_bal = getBalance('BUSD')
        else:
            '''Mock Trade'''
            # trade_report_csv_path = current_dir + '../candlestick-screener-master/report'
            busd_bal_txt = current_dir + '/busd_bal.txt'
            with open(busd_bal_txt, 'r') as busd:
                busd_bal = float(busd.readline())
                busd.close()

        print(username, ' ==::== ', str(busd_bal))
        s_interval = '15m'  # valid intervals - 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
        RSI_PERIOD = 6
        RSI_OVERBOUGHT = 70
        RSI_OVERBOUGHT_SELL = 80
        RSI_OVERSOLD = 30
        BUY_AMT = 50
        connection = db_util.connect_database()
        if connection.is_connected():
            current_pos = 0.00
            ba_select_query = """select `single_trade_amount` from `ant_cryptotradingbot`.`ant_user_data` where `username`='{}';""" \
                .format(username)
            ba_select_query_result = db_util.queryExecution(connection, ba_select_query, 'select')
            if ba_select_query_result[0][0] != 50 and ba_select_query_result > 0:
                BUY_AMT = ba_select_query_result[0][0]
            select_query = """select cbor.symbol_name from `ant_cryptotradingbot`.`current_buy_order_report` as cbor 
            left join `ant_cryptotradingbot`.`order_report` as ort on ort.symbol_name = cbor.symbol_name 
            and ort.signal_type = cbor.signal_type and ort.order_quantity = cbor.order_quantity 
            and ort.buy_price = cbor.buy_price and ort.order_date = cbor.order_date and ort.username = cbor.username
            where ort.buy_amount is null and cbor.buy_orderID = 0 and cbor.username = '{}';""" \
                .format(username)
            select_query_result = db_util.queryExecution(connection, select_query, 'select')
            for rq in select_query_result:
                delete_query = """delete from `ant_cryptotradingbot`.`current_buy_order_report` where symbol_name = '{}' and username = '{}';""" \
                    .format(rq[0], username)
                update_query_result = db_util.queryExecution(connection, delete_query, 'update')

            select_query = """select cbor.symbol_name, cbor.signal_type, cbor.order_quantity, cbor.buy_price, cbor.order_date 
            from `ant_cryptotradingbot`.`current_buy_order_report` as cbor 
            inner join `ant_cryptotradingbot`.`order_report` as ort on ort.symbol_name = cbor.symbol_name 
            and ort.signal_type = cbor.signal_type and ort.order_quantity = cbor.order_quantity 
            and ort.buy_price = cbor.buy_price and ort.order_date = cbor.order_date and ort.username = cbor.username
            where ort.sell_amount is null and ort.sell_price is not null and cbor.sell_orderID = 0 and cbor.username = '{}';""" \
                .format(username)
            select_query_result = db_util.queryExecution(connection, select_query, 'select')
            for rq in select_query_result:
                update_query = """update `ant_cryptotradingbot`.`order_report` set sell_price = null 
                where symbol_name = '{}' and signal_type = '{}' and order_quantity = {} 
                and buy_price = {} and order_date = '{}' and `update_date` is null and username = '{}';""" \
                    .format(rq[0], rq[1], rq[2], rq[3], rq[4], username)
                update_query_result = db_util.queryExecution(connection, update_query, 'update')

            select_query = """SELECT sum(`buy_price`*`order_quantity`) FROM `ant_cryptotradingbot`.`current_buy_order_report` WHERE `username`='{}';"""\
                .format(username)
            select_query_result = db_util.queryExecution(connection, select_query, 'select')
            if select_query_result[0][0] is not None:
                current_pos = float(select_query_result[0][0])
            nthread_count = int((int(busd_bal+current_pos) / 2) / BUY_AMT) + 1
            print(username, ' ==::== ', nthread_count)
            select_orderseq_query = """select order_seq_id from `ant_cryptotradingbot`.`current_buy_order_report` WHERE `username`='{}' order by order_seq_id asc;""" \
                .format(username)
            select_orderseq_query_result = db_util.queryExecution(connection, select_orderseq_query, 'select')
            ord_seq = 0
            for rq in select_orderseq_query_result:
                update_query = """update `ant_cryptotradingbot`.`current_buy_order_report` set order_seq_id={} where `username`='{}' and order_seq_id={};""" \
                    .format(ord_seq, username, rq[0])
                update_query_result = db_util.queryExecution(connection, update_query, 'update')
                ord_seq += 1

            if nthread_count < len(select_orderseq_query_result):
                nthread_count = len(select_orderseq_query_result)

            query_1 = """UPDATE `ant_cryptotradingbot`.`ant_user_data` SET `max_trade`={} 
            WHERE `username`='{}';""" \
                .format(nthread_count, username)
            query_result = db_util.queryExecution(connection, query_1, 'update')
            connection.close()


            for r in range(0, nthread_count):
                x = threading.Thread(target=start_trade, args=(r,))
                x.start()
                print('Time sleep for : 1 minute......')
                time.sleep(60)
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - main :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print('Error: - Main error - {}'.format(error_log))
        print('Time sleep for : 1 min......')
        time.sleep(60)
