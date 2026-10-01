import pandas as pd
import numpy as np
import talib
from binance.client import Client
import ccxt
from utils import config, db_util
from random import randint
from datetime import datetime
#from utils.logger import logger
import time, sys, os
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
        elif b['asset'] == symbol and float(b['locked']) > 0 and symbol != 'USDT':
            symbol_bal = float(b['locked'])
            is_locked = True
            break
        elif b['asset'] == symbol and symbol == 'USDT':
            symbol_bal = float(b['free'])
            is_locked = False
            break
    return symbol_bal


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
        # pprint.pprint(bars)

        for line in bars:
            del line[5:]

        df = pd.DataFrame(bars, columns=['date', 'open', 'high', 'low', 'close'])
        return df
    except:
        pass


def trade_logic(select_query_result):
    symbol = ''
    try:
        exchange = exchange_init()
        if len(select_query_result) > 0:
            symbol = select_query_result[0][0]
            signal_type = select_query_result[0][1]
            ordered_qty = float(select_query_result[0][2])
            buy_price = float(select_query_result[0][3])
            in_position = True
        else:
            in_position = False
            buy_price = 0.00
            ordered_qty = 0
            signal_type = ''

        if not(in_position):
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
                            if res_count < len(rr_trim):
                                is_entry_point = False
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
                            in_position, buy_price, ordered_qty = buy_or_sell(symbol, 1.0, signal_type, in_position)
                            break
                else:
                    return

        if in_position:
            target_percent = 2
            stoploss_percent = -1 * target_percent
            is_half_target = False
            is_resistance_reach = False
            # is_half_sl = False
            while True:
                symbol_info = exchange.fetch_ticker(symbol)['info']
                cur_bid_price = round(float(symbol_info['bidPrice']), 8)
                ss, rr = srl.main(symbol)
                ss_trim = ss[-2:]
                rr_trim = rr[-2:]
                lst_support = []
                lst_resistance = []
                for sup in ss_trim:
                    if sup[1] < cur_bid_price:
                        lst_support.append(sup[1])
                    if sup[1] > cur_bid_price:
                        lst_resistance.append(sup[1])
                lst_support.sort(reverse=True)
                for res in rr_trim:
                    if res[1] > cur_bid_price:
                        lst_resistance.append(res[1])
                lst_resistance.sort()
                connection = db_util.connect_database()
                if connection.is_connected():
                    query = """SELECT csd.`symbol_name`, `current_askPrice`, `upper_BBand_price`, `middle_BBand_price`, `lower_BBand_price`, `MACD_dif`, `MACD_dem`, `MACD_macd`, csmsd.`sum_dem_macd_prv`, csmsd.`sum_dem_macd_current`, `last_RSI`, `2hrs_ST`, csd.`last_update_DateTime` FROM `ant_cryptotradingbot`.`crypto_symbols_data` as csd 
                    INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_macd_st_data` as csmsd on csd.symbol_name = csmsd.symbol_name 
                    INNER JOIN `ant_cryptotradingbot`.`live_patterns_signal` as lps on csd.symbol_name = lps.symbol_name  
                    WHERE ((csd.MACD_dem < 0 and csd.MACD_dif < 0 and csd.MACD_macd < 0) or (lps.`PatternName` in ('Hanging Man','Shooting Star','Evening Star','Evening Doji Star','Three Black Crows','Dark Cloud Cover','Engulfing Pattern') and lps.SignalType = 'bearish') or csd.last_RSI > {} or (csd.`15mins_ST` = False and csd.`2hrs_ST` = False)) and csd.`symbol_name`='{}'"""\
                        .format(RSI_OVERBOUGHT_SELL, symbol)
                    if signal_type == 'SuperTrend':
                        query = """SELECT csd.`symbol_name`, `current_askPrice`, `upper_BBand_price`, `middle_BBand_price`, `lower_BBand_price`, `MACD_dif`, `MACD_dem`, `MACD_macd`, csmsd.`sum_dem_macd_prv`, csmsd.`sum_dem_macd_current`, `last_RSI`, `2hrs_ST`, csd.`last_update_DateTime` FROM `ant_cryptotradingbot`.`crypto_symbols_data` as csd 
                        INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_macd_st_data` as csmsd on csd.symbol_name = csmsd.symbol_name 
                        INNER JOIN `ant_cryptotradingbot`.`live_patterns_signal` as lps on csd.symbol_name = lps.symbol_name  
                        WHERE ((csd.MACD_dem < 0 and csd.MACD_dif < 0 and csd.MACD_macd < 0) or (lps.`PatternName` in ('Hanging Man','Shooting Star','Evening Star','Evening Doji Star','Three Black Crows','Dark Cloud Cover','Engulfing Pattern') and lps.SignalType = 'bearish') or csd.last_RSI > {} or (csd.`15mins_ST` = False and csd.`2hrs_ST` = False)) and csd.`symbol_name`='{}'"""\
                            .format(RSI_OVERBOUGHT_SELL, symbol)
                    if signal_type.startswith("Pattern"):
                        query = """SELECT csd.`symbol_name`, `current_askPrice`, `upper_BBand_price`, `middle_BBand_price`, `lower_BBand_price`, `MACD_dif`, `MACD_dem`, `MACD_macd`, csmsd.`sum_dem_macd_prv`, csmsd.`sum_dem_macd_current`, `last_RSI`, `2hrs_ST`, csd.`last_update_DateTime`, lps.`PatternName` FROM `ant_cryptotradingbot`.`crypto_symbols_data` as csd 
                        INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_macd_st_data` as csmsd on csd.symbol_name = csmsd.symbol_name
                        INNER JOIN `ant_cryptotradingbot`.`live_patterns_signal` as lps on csd.symbol_name = lps.symbol_name  
                        WHERE ((lps.`PatternName` in ('Hanging Man','Shooting Star','Evening Star','Evening Doji Star','Three Black Crows','Dark Cloud Cover','Engulfing Pattern') and lps.SignalType = 'bearish') and csd.last_RSI > {} and (csd.`15mins_ST` = False or csd.`2hrs_ST` = False)) and csd.`symbol_name`='{}';""" \
                            .format(RSI_OVERBOUGHT_SELL, symbol)
                    symbols_list = db_util.queryExecution(connection, query, 'select')
                    is_exit_call = False
                    exit_method = ''
                    if len(symbols_list) > 0:
                        is_exit_call = True
                        if not signal_type.startswith("Pattern"):
                            exit_method = signal_type
                        else:
                            exit_method = str(symbols_list[0][13])

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
                    stop_loss = round(float(buy_price + (buy_price * stoploss_percent / 100)), 5)
                    if len(lst_support) > 0 and stoploss_percent < 0:
                        for support in lst_support:
                            if not (is_resistance_reach):
                                stoploss_percent = round(float((support - buy_price) / (buy_price / 100)), 2)
                                if -2 <= stoploss_percent < -1:
                                    stop_loss = support
                                    break

                    if len(lst_resistance) > 0:
                        if not(is_resistance_reach) and target_price < lst_resistance[0]:
                            target_price = lst_resistance[0]
                        for resist in lst_resistance:
                            if resist > f_current_price >= target_price and stop_loss != target_price:
                                stop_loss = target_price
                                target_price = resist
                                is_resistance_reach = True
                                break

                    stoploss_percent = round(float((stop_loss - buy_price) / (buy_price / 100)), 2)
                    target_percent = round(float((target_price - buy_price) / (buy_price / 100)), 2)

                    rev_target = target_percent / 2
                    if current_percent >= rev_target and target_percent > 2:
                        is_half_target = True

                    # if current_percent >= target_percent:
                    #     stoploss_percent = stoploss_percent - target_percent
                    #     target_percent = target_percent * 2
                    #
                    if is_half_target and current_percent < (rev_target/2):
                        is_exit_call = True
                        exit_method = "Half target achieved and going down"

                    query_result = False
                    connection = db_util.connect_database()
                    if connection.is_connected():
                        update_query = """UPDATE `ant_cryptotradingbot`.`current_buy_order_report` SET `current_price`={},`profit_percent`={},`target_price`={},`target_percent`={},`stoploss_price`={},`stoploss_percent`={} 
                        WHERE `symbol_name`='{}' and `signal_type`='{}' and `order_quantity`={} and `username`='{}';"""\
                            .format(f_current_price, current_percent, target_price, target_percent, stop_loss,
                                    stoploss_percent, symbol, signal_type, round(float(ordered_qty), 2), username)
                        query_result = db_util.queryExecution(connection, update_query, 'update')

                    is_exit = False
                    sell_reason = ''
                    if f_current_price >= target_price:
                        is_exit = True
                        sell_reason = 'Target Achieved'
                        print('{} - Target achieved == price : {} ({} %) - Target : {} ({} %) ...'
                                         .format(symbol, f_current_price, current_percent, target_price, target_percent)
                                         )
                    elif last_rsi >= RSI_OVERBOUGHT_SELL:
                        is_exit = True
                        sell_reason = 'RSI - Overbought'
                        print('{} - RSI Overbought reached == price : {} ({} %) - RSI : {} ...'
                                         .format(symbol, f_current_price, current_percent, last_rsi)
                                         )
                    elif is_exit_call:
                        is_exit = True
                        sell_reason = 'Other - ' + exit_method
                        print('{} - Exit call == price : {} ({} %) - {} ...'
                                         .format(symbol, f_current_price, current_percent, exit_method)
                                         )
                    elif f_current_price <= stop_loss:  # or last_rsi <= RSI_OVERSOLD
                        is_exit = True
                        sell_reason = 'Stop loss hit'
                        print('{} - Stoploss hitting == price : {} ({} %) - Stoploss : {} ({} %) ...'
                                         .format(symbol, f_current_price, current_percent, stop_loss, stoploss_percent)
                                         )

                    if is_exit:
                        buy_or_sell(symbol, -1.0, signal_type, in_position, ordered_qty, sell_reason)
                        break

                    print('{} - Time sleep for : 1 minute..... - qty : {} == price : {} ({} %) - Target : {} ({} %) - Stoploss : {} ({} %) - RSI : {} - DB Update : {}'
                                     .format(symbol, ordered_qty, f_current_price, current_percent, target_price, target_percent, stop_loss, stoploss_percent, last_rsi, str(query_result))
                                     )
                    time.sleep(60)
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - trade_logic :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print(symbol + ' - ' + error_log)


def buy_or_sell(symbol, buy_sell, signal_type, in_position_entry, qty=0, sell_reason=''):
    exchange = exchange_init()
    symbol_info = exchange.fetch_ticker(symbol)['info']
    cur_price = round(float(symbol_info['askPrice']), 8)
    ordered_qty = 0
    try:
        log = ''
        dt_today = datetime.today()  # Local time
        dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
        trade_date = str(dt_India.strftime('%Y-%m-%d %H:%M:%S'))
        if trade_type == 'live':
            '''Live Trade'''
            currnt_usdt_bal = getBalance('USDT')
        else:
            '''Mock Trade'''
            with open(usdt_bal_txt, 'r') as usdt:
                currnt_usdt_bal = float(usdt.readline())
                usdt.close()

        if buy_sell == 1.0: # and (last_rsi >= RSI_OVERSOLD and last_rsi <= RSI_OVERBOUGHT) # signal to buy (either compare with current price to but/sell or use limit order with value
            if not(in_position_entry):
                buy_amount = currnt_usdt_bal
                # if os.path.exists(current_dir+'supertrend_current_buy_log.txt'):
                #     buy_amount = currnt_usdt_bal
                # else:
                #     buy_amount = currnt_usdt_bal / 2

                qty = int(round((float(buy_amount) - 0.2), 4) / cur_price)
                while (qty*cur_price) > buy_amount:
                    qty -= 1
                    symbol_info = exchange.fetch_ticker(symbol)['info']
                    cur_price = round(float(symbol_info['askPrice']), 8)
                if trade_type == 'live':
                    '''Live Trade'''
                    buy_order = client.order_market_buy(symbol=symbol, quantity=qty)
                    buy_order['commisionPrice'] = 0.0000
                    for buy_order_fills in buy_order['fills']:
                        buy_order['commisionPrice'] += round(float(buy_order_fills['commission']), 8)
                    cur_price = round((float(buy_order['cummulativeQuoteQty']) / float(buy_order['executedQty'])), 8)
                    ordered_qty = int(float(buy_order['executedQty']))
                    currnt_usdt_bal = round(float(getBalance('USDT')), 2)
                else:
                    '''Mock Trade'''
                    symbol_info = exchange.fetch_ticker(symbol)['info']
                    cur_price = round(float(symbol_info['askPrice']), 8)
                    ordered_qty = qty
                    buy_order = {}
                    buy_order['cummulativeQuoteQty'] = float(ordered_qty * cur_price)
                    buy_order['commisionPrice'] = 0.0000
                    currnt_usdt_bal = round(float(currnt_usdt_bal - buy_order['cummulativeQuoteQty']), 2)
                    with open(usdt_bal_txt, 'w') as usdt:
                        usdt.write(str(currnt_usdt_bal))
                        usdt.close()
                        
                bnb_price = client.get_symbol_ticker(symbol='BNBUSDT')
                buy_order['commisionPrice'] = buy_order['commisionPrice'] * float(bnb_price['price'])

                connection = db_util.connect_database()
                if connection.is_connected():
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
                    query_1 = """INSERT INTO `ant_cryptotradingbot`.`current_buy_order_report` (`order_seq_id`,`symbol_name`,`signal_type`,
                    `order_quantity`,`buy_price`,`current_price`,`profit_percent`,`target_price`,`username`,`order_date`) 
                    VALUES({},'{}','{}',{},{},null,null,null,'{}','{}');"""\
                        .format(orderSeqId, symbol, signal_type, ordered_qty, cur_price, username, trade_date)
                    query_result = db_util.queryExecution(connection, query, 'insert')
                    if query_result:
                        query_result = db_util.queryExecution(connection, query_1, 'insert')
                        w_ins_query = """UPDATE `ant_cryptotradingbot`.`ant_user_wallet` set `binance_exchange_usdt` = {} WHERE `username` = '{}';""" \
                            .format(currnt_usdt_bal, username)
                        wallet_query_result = db_util.queryExecution(connection, w_ins_query, 'update')
                    print(str(buy_order)+' - DB Insert : '+str(query_result))
                log = '{} :: {} :: {} :: qty {}'.format('Buy Order', symbol, str(cur_price), str(qty))
                print(log)
                print('Ordered Quantity is : ' + str(ordered_qty))
                in_position_entry = True
        elif buy_sell == -1.0:  # and (last_rsi <= RSI_OVERSOLD or last_rsi >= RSI_OVERBOUGHT) # signal to sell (either compare with current price to but/sell or use limit order with value
            if in_position_entry:
                if trade_type == 'live':
                    '''Live Trade'''
                    sell_order = client.order_market_sell(symbol=symbol, quantity=qty)
                    sell_order['commisionPrice'] = 0.0000
                    for sell_order_fills in sell_order['fills']:
                        sell_order['commisionPrice'] += round(float(sell_order_fills['commission']), 8)
                    cur_price = round((float(sell_order['cummulativeQuoteQty']) / float(sell_order['executedQty'])), 8)
                    ordered_qty = int(float(sell_order['executedQty']))
                    currnt_usdt_bal = round(float(getBalance('USDT')), 2)
                else:
                    '''Mock Trade'''
                    # df_read = pd.read_csv(trade_report_csv)
                    symbol_info = exchange.fetch_ticker(symbol)['info']
                    cur_price = round(float(symbol_info['askPrice']), 8)
                    ordered_qty = qty
                    sell_order = {'commisionPrice': 0.0000, 'cummulativeQuoteQty': float(ordered_qty * cur_price)}
                    # sell_order['orderSeqId'] = str(len(df_read))
                    currnt_usdt_bal = round(float(currnt_usdt_bal + sell_order['cummulativeQuoteQty']), 2)
                    with open(usdt_bal_txt, 'w') as usdt:
                        usdt.write(str(currnt_usdt_bal))
                        usdt.close()

                bnb_price = client.get_symbol_ticker(symbol='BNBUSDT')
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
                        w_ins_query = """UPDATE `ant_cryptotradingbot`.`ant_user_wallet` set `binance_exchange_usdt` = {} WHERE `username` = '{}';""" \
                            .format(currnt_usdt_bal, username)
                        wallet_query_result = db_util.queryExecution(connection, w_ins_query, 'update')
                    print(str(sell_order)+' - DB Update : '+str(query_result))
                log = '{} :: {} :: {} :: qty {}'.format('Sell Order', symbol, str(cur_price), str(qty))
                print(log)
                in_position_entry = False
        else:
            print(symbol + ' - ' + 'nothing to do... in buy / sell block...')
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - Buy_Sell :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print('Error: - Buy_Sell block error - {} ; qty - {} ; price - {}'.format(error_log, str(qty), cur_price))
    return in_position_entry, cur_price, ordered_qty



def start_trade():
    try:
        while True:
            if trade_type == 'live':
                '''Live Trade'''
                curr_usdt_bal = getBalance('USDT')
            else:
                '''Mock Trade'''
                with open(usdt_bal_txt, 'r') as usdt:
                    curr_usdt_bal = float(usdt.readline())
                    usdt.close()

            connection = db_util.connect_database()
            if connection.is_connected():
                dt_today = datetime.today()  # Local time
                dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
                current_date = str(datetime.strftime(dt_India, "%d%m%Y"))
                if start_date != current_date:
                    update_query = """UPDATE `ant_cryptotradingbot`.`ant_user_data` SET `is_tool_running`=False  
                            WHERE `is_tool_running` = True and `username` = '{}'"""\
                        .format(username)
                    db_update = db_util.queryExecution(connection, update_query, 'update')
                    print('Trading closed for end of date ::: {} -- DBUpdate ::: {}'.format(start_date, db_update))
                    sys.exit()
                select_query = """SELECT `symbol_name`,`signal_type`,`order_quantity`,`buy_price` FROM `ant_cryptotradingbot`.`current_buy_order_report` WHERE `username`='{}';"""\
                    .format(username)
                select_query_result = db_util.queryExecution(connection, select_query, 'select')
                if int(curr_usdt_bal) >= 100 or len(select_query_result) > 0:
                    if buy_BNB():
                        wallet_query = """SELECT count(*) FROM `ant_cryptotradingbot`.`ant_user_wallet` where `username` = '{}'"""\
                            .format(username)
                        wallet_query_result = db_util.queryExecution(connection, wallet_query, 'select')
                        if wallet_query_result[0][0] == 0:
                            curr_usdt_bal = round(float(curr_usdt_bal), 2)
                            new_usdt_bal = round(float(getBalance('USDT')), 2)
                            w_ins_query = """INSERT `ant_cryptotradingbot`.`ant_user_wallet` (`username`, `initial_investment`, `binance_exchange_usdt`) VALUES ('{}', {}, {});"""\
                                .format(username, curr_usdt_bal, new_usdt_bal)
                            wallet_query_result = db_util.queryExecution(connection, w_ins_query, 'insert')
                            print('New Wallet DBInsert :: {}'.format(wallet_query_result))
                        trade_logic(select_query_result)
                        print('Time sleep for : 1 second.....')
                        time.sleep(1)
                else:
                    print('Current USDT balance is < 100 (USDT {})'.format(curr_usdt_bal))
            print('Time sleep for : 5 minutes.....')
            time.sleep(299)
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - trade_logic :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print('Error: - Start trade block error - {}'.format(error_log))


def buy_BNB():
    try:
        bnb_symbol = 'BNBUSDT'
        bnb_qty = getBalance('BNB')
        bnb_price = client.get_symbol_ticker(symbol=bnb_symbol)
        bnb_qty_price = round(float(bnb_qty * round(float(bnb_price['price']), 1)), 2)
        if bnb_qty_price <= 1.00:
            if trade_type == 'live':
                '''Live Trade'''
                curr_usdt_bal = getBalance('USDT')
            else:
                '''Mock Trade'''
                return True

            # curr_hrs = int(datetime.strftime(datetime.now(), "%H"))
            # curr_min = int(datetime.strftime(datetime.now(), "%M"))
            dt_today = datetime.today()  # Local time
            dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
            trade_date = str(dt_India.strftime('%Y-%m-%d %H:%M:%S'))
            if int(curr_usdt_bal) >= 10.5:
                qty = round(float(10.5 / round(float(bnb_price['price']), 1)), 3)
                buy_order = client.order_market_buy(symbol=bnb_symbol, quantity=qty)

                if buy_order['status'] == 'FILLED':
                    cur_price = round((float(buy_order['cummulativeQuoteQty']) / float(buy_order['executedQty'])), 1)
                    buy_quantity = round(float(buy_order['executedQty']), 3)
                    buy_amount = round(float(buy_order['cummulativeQuoteQty']), 4)
                    query_result = False
                    connection = db_util.connect_database()
                    if connection.is_connected():
                        query = """INSERT INTO `ant_cryptotradingbot`.`bnb_report` (`symbol_name`,`order_quantity`,`buy_price`,`buy_amount`,`username`,`order_date`) 
                        VALUES ('{}',{},{},{},'{}','{}');"""\
                            .format(bnb_symbol, buy_quantity, cur_price, buy_amount, username, trade_date)
                        query_result = db_util.queryExecution(connection, query, 'insert')
                        currnt_usdt_bal = round(float(getBalance('USDT')), 2)
                        w_ins_query = """UPDATE `ant_cryptotradingbot`.`ant_user_wallet` set `binance_exchange_usdt` = {} WHERE `username` = '{}';""" \
                            .format(currnt_usdt_bal, username)
                        wallet_query_result = db_util.queryExecution(connection, w_ins_query, 'update')
                    print('Bought BNB for {} -- DB Update : {}'.format(buy_order['cummulativeQuoteQty'], str(query_result)))
                    return query_result
                else:
                    els_msg = 'Unable to buy BNB for commission purpose. Current BNB worth below {} USDT. Please check and buy it manually.....'.format(bnb_qty_price)
                    print(els_msg)
                    return False
        else:
            return True
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - trade_logic :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print('BNBUSDT - ' + error_log)
        return False


if __name__ == "__main__":
    dt_today = datetime.today()  # Local time
    dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
    start_date = str(datetime.strftime(dt_India, "%d%m%Y"))
    log_filename = "DB_Trading_BOT_{}_{}.log".format(start_date, str(sys.argv[1]))
    while True:
        current_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../')
        print('current_dir: ', current_dir)
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
                usdt_bal = getBalance('USDT')
            else:
                '''Mock Trade'''
            # trade_report_csv_path = current_dir + '../candlestick-screener-master/report'
                usdt_bal_txt = current_dir + '/usdt_bal.txt'
                with open(usdt_bal_txt, 'r') as usdt:
                    usdt_bal = float(usdt.readline())
                    usdt.close()

            print(str(usdt_bal))
            s_interval = '15m'  # valid intervals - 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
            RSI_PERIOD = 6
            RSI_OVERBOUGHT = 70
            RSI_OVERBOUGHT_SELL = 75
            RSI_OVERSOLD = 30
            start_trade()
        except Exception as ex:
            error_log = str(ex).replace('\'', '\'\'') + " - main :: line ::" \
                        + str(sys.exc_info()[2].tb_lineno)
            print('Error: - Main error - {}'.format(error_log))
            print('Time sleep for : 1 min......')
            time.sleep(60)
            continue
