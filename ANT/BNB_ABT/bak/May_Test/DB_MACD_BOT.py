import pandas as pd
import numpy as np
import talib
from binance.client import Client
import config
import db_util
from random import randint
from datetime import datetime
from logger import logger
import time, sys, os
from pytz import timezone


def getBalance(symbol):
    info = client.get_account()
    bal = info['balances']
    is_locked = False
    symbol_bal = 0.00
    for b in bal:
        if b['asset'] == symbol and float(b['free']) > 0 and float(b['locked']) == 0:
            symbol_bal = float(b['free'])
            break
        elif b['asset'] == symbol and float(b['locked']) > 0:
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


def trade_logic():
    symbol = ''
    in_position = False
    buy_price = 0.00
    ordered_qty = 0
    try:
        if os.path.exists(current_dir+'current_buy_log.txt'):
            with open(current_dir+'current_buy_log.txt', 'r') as f:
                buy_log = str(f.readline())
                print(buy_log)
                str_split = buy_log.split('|')
                symbol = str_split[1]
                ordered_qty = int(float(str_split[2]))
                buy_price = float(str_split[3])
                in_position = True

        if not(in_position):
            cur = db_util.connect_database()
            if cur:
                logger.writeLogs('Connection opened... - ', 'info', log_filename)
                query = "SELECT csd.[symbol_name], [current_askPrice], [upper_BBand_price], [middle_BBand_price], [lower_BBand_price], [MACD_dif], [MACD_dem], [MACD_macd], [last_RSI], [2hrs_ST], csd.[last_update_DateTime] FROM [dbo].[crypto_symbols_data] as csd " \
                        "INNER JOIN [dbo].[crypto_symbols_macd_st_data] as csmsd on csd.symbol_name = csmsd.symbol_name " \
                        "WHERE (csd.upper_BBand_price > csd.current_askPrice " \
                        "and (csd.middle_BBand_price < csd.current_askPrice or ((csd.middle_BBand_price + csd.lower_BBand_price)/2) < csd.current_askPrice)) " \
                        "and csmsd.sum_dem_macd_current >= 0 and csmsd.sum_dem_macd_prv < csmsd.sum_dem_macd_current and csd.MACD_dif >= 0 and csd.MACD_dem <= 0 and csd.last_RSI < 60 and csd.last_RSI > 45 and csd.[2hrs_ST] = 'True' and csd.is_Active = 'True'"
                symbols_list = db_util.queryExecution(cur, query, 'select')
                if len(symbols_list) > 0:
                    symbols_count = len(symbols_list)
                    selected_symbol = symbols_list[randint(0, symbols_count-1)]
                    symbol = selected_symbol[0]
                    last_rsi = selected_symbol[8]
                    in_position, buy_price, ordered_qty = buy_or_sell(symbol, 1.0, last_rsi, in_position)
                else:
                    return

        if in_position:
            target_percent = 2
            rev_buy_price = buy_price
            if in_position:
                while True:
                    cur = db_util.connect_database()
                    if cur:
                        query = "SELECT csd.[symbol_name], [current_askPrice], [upper_BBand_price], [middle_BBand_price], [lower_BBand_price], [MACD_dif], [MACD_dem], [MACD_macd], csmsd.[sum_dem_macd_prv], csmsd.[sum_dem_macd_current], [last_RSI], [2hrs_ST], csd.[last_update_DateTime] FROM [dbo].[crypto_symbols_data] as csd " \
                                "INNER JOIN [dbo].[crypto_symbols_macd_st_data] as csmsd on csd.symbol_name = csmsd.symbol_name " \
                                "WHERE csd.[symbol_name]='{}'".format(symbol)
                        symbols_list = db_util.queryExecution(cur, query, 'select')
                        if len(symbols_list) > 0:
                            selected_symbol = symbols_list[0]
                            Two_hrs_ST = selected_symbol[11]
                            symbol_df = get_data_frame(symbol)

                            closes = symbol_df['close'].tolist()
                            icloses = [float(c) for c in closes]
                            np_closes = np.array(icloses)
                            rsi = talib.RSI(np_closes, RSI_PERIOD)
                            last_rsi = rsi[-1]

                            current_price = client.get_symbol_ticker(symbol=symbol)
                            f_current_price = round(float(current_price['price']), 8)
                            current_percent = round(float((f_current_price - buy_price) / (buy_price / 100)), 2)
                            target_price = round(float(buy_price + (buy_price * target_percent / 100)), 5)
                            stop_loss = round(float(rev_buy_price - (rev_buy_price * 2 / 100)), 5)

                            if os.path.exists(current_dir+'current_buy_log.txt'):
                                with open(current_dir+'current_buy_log.txt', 'r') as f:
                                    macd_buy_log = str(f.readline())
                                    flk_report = trade_report_csv_path+'/macd_current_buy.txt'
                                    with open(flk_report, 'w') as flk:
                                        macd_buy_log += '|{}|{}|{}'.format(f_current_price, current_percent, target_price)
                                        flk.write(macd_buy_log)

                            if f_current_price >= target_price or last_rsi >= RSI_OVERBOUGHT:
                                buy_or_sell(symbol, -1.0, last_rsi, in_position, ordered_qty)
                                break
                            elif not(Two_hrs_ST):
                                buy_or_sell(symbol, -1.0, last_rsi, in_position, ordered_qty)
                                break
                            elif f_current_price <= stop_loss or last_rsi <= RSI_OVERSOLD:
                                buy_or_sell(symbol, -1.0, last_rsi, in_position, ordered_qty)
                                break

                            logger.writeLogs('{} - Time sleep for : 1 minute..... - qty : {} == price : {} ({} %) - Target : {} - RSI : {}'
                                  .format(symbol, ordered_qty, f_current_price, current_percent, target_price, last_rsi), 'info', log_filename)
                            time.sleep(60)
            # print(symbol, ' - Time sleep for : 15 mins.....')
            # time.sleep(899)
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - trade_logic :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        logger.writeLogs(symbol + ' - ' + error_log, 'error', log_filename)
        # exclude_symbols.append(symbol)


def buy_or_sell(symbol, buy_sell, last_rsi, in_position_entry, qty=0):
    start_time = str(datetime.strftime(datetime.now(), "%d%m%Y_%H%M%S"))
    current_price = client.get_symbol_ticker(symbol=symbol)
    cur_price = round(float(current_price['price']), 8)
    ordered_qty = 0
    try:
        log = ''
        dt_today = datetime.today()  # Local time
        dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
        trade_date = str(dt_India.strftime('%m/%d/%Y %H:%M'))
        '''Live Trade'''
        # currnt_usdt_bal = getBalance('USDT')
        '''Mock Trade'''
        with open(usdt_bal_txt, 'r') as usdt:
            currnt_usdt_bal = float(usdt.readline())
            usdt.close()

        if buy_sell == 1.0: # and (last_rsi >= RSI_OVERSOLD and last_rsi <= RSI_OVERBOUGHT) # signal to buy (either compare with current price to but/sell or use limit order with value
            if not(in_position_entry):
                if os.path.exists(current_dir+'supertrend_current_buy_log.txt'):
                    buy_amount = currnt_usdt_bal
                else:
                    buy_amount = currnt_usdt_bal / 2

                qty = int(round((float(buy_amount) - 0.2), 4) / round(float(current_price['price']), 8))
                '''Live Trade'''
                # buy_order = client.order_market_buy(symbol=symbol, quantity=qty)
                # cur_price = round((float(buy_order['cummulativeQuoteQty']) / float(buy_order['executedQty'])), 8)
                # ordered_qty = int(float(buy_order['executedQty']))
                '''Mock Trade'''
                df_read = pd.read_csv(trade_report_csv)
                cur_price = round(float(current_price['price']), 8)
                ordered_qty = qty
                buy_order = {}
                buy_order['orderId'] = str(len(df_read)+1)
                buy_order['cummulativeQuoteQty'] = float(ordered_qty * cur_price)
                currnt_usdt_bal = currnt_usdt_bal - buy_order['cummulativeQuoteQty']
                with open(usdt_bal_txt, 'w') as usdt:
                    usdt.write(str(currnt_usdt_bal))
                    usdt.close()

                with open(current_dir+'current_buy_log.txt', 'w') as f:
                    buy_log = '{}|{}|{}|{}'.format(buy_order['orderId'], symbol, ordered_qty, cur_price)
                    f.write(buy_log)
                    f.close()
                with open(trade_report_csv, 'a') as csv:
                    trade_report = '\n{},{},MACD,{},{},{},{}' \
                        .format(buy_order['orderId'], trade_date, symbol, str(ordered_qty), str(cur_price),
                                str(buy_order['cummulativeQuoteQty']))
                    csv.write(trade_report)
                    csv.close()
                logger.writeLogs(str(buy_order), 'info', log_filename)
                log = '{} :: {} :: {} :: qty {}'.format('Buy Order', symbol, str(cur_price), str(qty))
                logger.writeLogs(log, 'info', log_filename)
                # ordered_qty = float(getBalance(symbol.replace('USDT', ''))) - prev_qty
                logger.writeLogs('Ordered Quantity is : ' + str(ordered_qty), 'info', log_filename)
                in_position_entry = True
        elif buy_sell == -1.0:  # and (last_rsi <= RSI_OVERSOLD or last_rsi >= RSI_OVERBOUGHT) # signal to sell (either compare with current price to but/sell or use limit order with value
            if in_position_entry:
                # qty = getBalance(symbol.replace('USDT', ''))
                '''Live Trade'''
                # sell_order = client.order_market_sell(symbol=symbol, quantity=qty)
                # cur_price = round((float(sell_order['cummulativeQuoteQty']) / float(sell_order['executedQty'])), 8)
                # ordered_qty = int(float(sell_order['executedQty']))
                '''Mock Trade'''
                df_read = pd.read_csv(trade_report_csv)
                cur_price = round(float(current_price['price']), 8)
                ordered_qty = qty
                sell_order = {}
                sell_order['orderId'] = str(len(df_read))
                sell_order['cummulativeQuoteQty'] = float(ordered_qty * cur_price)
                currnt_usdt_bal = currnt_usdt_bal + sell_order['cummulativeQuoteQty']
                with open(usdt_bal_txt, 'w') as usdt:
                    usdt.write(str(currnt_usdt_bal))
                    usdt.close()

                if os.path.exists(current_dir+'current_buy_log.txt'):
                    os.remove(current_dir+'current_buy_log.txt')

                flk_report = trade_report_csv_path + '/macd_current_buy.txt'
                if os.path.exists(flk_report):
                    os.remove(flk_report)

                with open(trade_report_csv, 'a') as csv:
                    trade_report = ',{},{},{}'.format(str(cur_price), str(sell_order['cummulativeQuoteQty']), trade_date)
                    csv.write(trade_report)
                    csv.close()
                logger.writeLogs(str(sell_order), 'info', log_filename)
                log = '{} :: {} :: {} :: qty {}'.format('Sell Order', symbol, str(cur_price), str(qty))
                logger.writeLogs(log, 'info', log_filename)
                in_position_entry = False
        else:
            logger.writeLogs(symbol + ' - ' + 'nothing to do...' + ' last RSI: ' + str(last_rsi), 'info', log_filename)

        if log != '':
            with open(current_dir+'buy_sell_log.txt', 'a') as f:
                log = str(start_time) + ':: ' + log + '\n'
                f.write(log)
                f.close()
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - Buy_Sell :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        logger.writeLogs('Error: - Buy_Sell block error - {}'.format(error_log), 'error', log_filename)
    return in_position_entry, cur_price, ordered_qty



def start_trade():
    try:
        while True:
            '''Live Trade'''
            # curr_usdt_bal = getBalance('USDT')
            '''Mock Trade'''
            with open(usdt_bal_txt, 'r') as usdt:
                curr_usdt_bal = float(usdt.readline())
                usdt.close()

            if int(curr_usdt_bal) >= 100 or os.path.exists(current_dir+'current_buy_log.txt'):
                # buy_BNB()
                trade_logic()
            else:
                logger.writeLogs('Current USDT balance is < 100 (USDT {})'.format(curr_usdt_bal), 'info', log_filename)
            #print('======================')
            logger.writeLogs('Time sleep for : 15 minutes.....', 'info', log_filename)
            time.sleep(896)
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - trade_logic :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        logger.writeLogs('Error: - Start trade block error - {}'.format(error_log), 'error', log_filename)


def buy_BNB():
    try:
        bnb_symbol = 'BNBUSDT'
        bnb_qty = getBalance('BNB')
        bnb_price = client.get_symbol_ticker(symbol=bnb_symbol)
        bnb_qty_price = round(float(bnb_qty * round(float(bnb_price['price']), 1)), 2)
        if bnb_qty_price <= 3.00:
            '''Live Trade'''
            # curr_usdt_bal = getBalance('USDT')
            '''Mock Trade'''
            with open(usdt_bal_txt, 'r') as usdt:
                curr_usdt_bal = float(usdt.readline())
                usdt.close()

            curr_hrs = int(datetime.strftime(datetime.now(), "%H"))
            curr_min = int(datetime.strftime(datetime.now(), "%M"))
            dt_today = datetime.today()  # Local time
            dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
            trade_date = str(dt_India.strftime('%m/%d/%Y %H:%M'))
            if int(curr_usdt_bal) >= 10.5:
                qty = round(float(10.5 / round(float(bnb_price['price']), 1)), 3)
                '''Live Trade'''
                # buy_order = client.order_market_buy(symbol=bnb_symbol, quantity=qty)
                '''Mock Trade'''
                df_read = pd.read_csv(bnb_csv)
                cur_price = round(float(bnb_price['price']), 1)
                buy_order = {}
                buy_order['orderId'] = str(len(df_read)+1)
                buy_order['executedQty'] = qty
                buy_order['cummulativeQuoteQty'] = float(buy_order['executedQty'] * cur_price)
                buy_order['status'] = 'FILLED'
                curr_usdt_bal = curr_usdt_bal - buy_order['cummulativeQuoteQty']
                with open(usdt_bal_txt, 'w') as usdt:
                    usdt.write(str(curr_usdt_bal))
                    usdt.close()

                if buy_order['status'] == 'FILLED':
                    cur_price = round((float(buy_order['cummulativeQuoteQty']) / float(buy_order['executedQty'])), 1)
                    buy_quantity = round(float(buy_order['executedQty']), 3)
                    with open(bnb_csv, 'a') as csv:
                        bnb_report = '\n{},{},Transaction Charge,{},{},{},{}' \
                            .format(buy_order['orderId'], trade_date, bnb_symbol, str(qty), str(cur_price),
                                    str(buy_order['cummulativeQuoteQty']))
                        csv.write(bnb_report)
                        csv.close()
                    logger.writeLogs('Bought BNB for {}'.format(buy_order['cummulativeQuoteQty']), 'info', log_filename)
                else:
                    els_msg = 'Unable to buy BNB for commission purpose. Current BNB worth below {} USDT. Please check and buy it manually.....'.format(bnb_qty_price)
                    logger.writeLogs(els_msg, 'info', log_filename)
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - trade_logic :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        logger.writeLogs('BNBUSDT - ' + error_log, 'error', log_filename)


if __name__ == "__main__":
    while True:
        start_time = str(datetime.strftime(datetime.now(), "%d%m%Y_%H%M%S"))
        log_filename = "DB_MACD_BOT_{}.log".format(start_time)
        current_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../')
        print('current_dir: ', current_dir)
        trade_report_csv_path = current_dir + '../candlestick-screener-master/report'
        '''Mock Trade'''
        usdt_bal_txt = trade_report_csv_path + '/usdt_bal.txt'

        try:
            if not os.path.exists(trade_report_csv_path):
                os.makedirs(trade_report_csv_path)
            trade_report_csv = trade_report_csv_path + '/macd_trade_report.csv'
            if not os.path.exists(trade_report_csv):
                with open(trade_report_csv, 'w') as csv:
                    trade_report_head = 'Order ID,Order Date,Signal Type,Symbol Name,Ordered Qty.,Buy Price,Buy Amount,Sell Price,Sell Amount,Update Date'
                    csv.write(trade_report_head)
                    csv.close()
            bnb_csv = trade_report_csv_path + '/bnb_report.csv'
            if not os.path.exists(bnb_csv):
                with open(bnb_csv, 'w') as bnb_csv:
                    trade_report_head = 'Order ID,Order Date,Signal Type,Symbol Name,Ordered Qty.,Buy Price,Buy Amount'
                    bnb_csv.write(trade_report_head)
                    bnb_csv.close()

            api_key = config.BINANCE_API_KEY
            api_secret = config.BINANCE_API_SECRET
            client = Client(api_key, api_secret)
            logger.writeLogs('Connection opened... - ', 'info', log_filename)
            # pprint.pprint(client.get_account())
            '''Live Trade'''
            # usdt_bal = getBalance('USDT')
            '''Mock Trade'''
            with open(usdt_bal_txt, 'r') as usdt:
                usdt_bal = float(usdt.readline())
                usdt.close()

            logger.writeLogs(str(usdt_bal), 'info', log_filename)
            s_interval = '15m'  # valid intervals - 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
            RSI_PERIOD = 6
            RSI_OVERBOUGHT = 70
            RSI_OVERSOLD = 30
            start_trade()
        except Exception as ex:
            error_log = str(ex).replace('\'', '\'\'') + " - main :: line ::" \
                        + str(sys.exc_info()[2].tb_lineno)
            logger.writeLogs('Error: - Main error - {}'.format(error_log), 'error', log_filename)
            logger.writeLogs('Time sleep for : 1 min......', 'error', log_filename)
            time.sleep(60)
            continue
