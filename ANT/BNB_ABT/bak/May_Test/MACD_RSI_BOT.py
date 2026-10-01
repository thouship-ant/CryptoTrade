import pandas as pd
import numpy as np
import talib
import pywhatkit as pw
from talib import MA_Type
from datetime import datetime
from pytz import timezone
import matplotlib.pyplot as plt
from binance.client import Client
import config
import time, sys, os
from logger import logger
import SuperTrend_BOT

global symbol, exclude_symbols, qty, in_position


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


def get_symbol():
    logger.writeLogs('getting symbols...', 'info', log_filename)
    lstselsymbol = []
    lstsymbol = client.get_symbol_ticker()
    if os.path.exists(current_dir+'symbols.txt'):
        os.remove(current_dir+'symbols.txt')
    for ls in lstsymbol:
        # if ls['symbol'].find("USDT") > 1 and ls['symbol'].find("UPUSDT") == -1 \
        #         and ls['symbol'].find("DOWNUSDT") == -1:
        #     with open('symbols.txt', 'a') as f:
        #         info = client.get_symbol_info(ls['symbol'])
        #         f.write(info['symbol']+','+info['baseAsset']+'\n')
        #         f.close()
        if ls['symbol'].find("USDT") > 1 and ls['symbol'].find("UPUSDT") == -1 \
                and ls['symbol'].find("DOWNUSDT") == -1 and float(ls['price']) < 0.9 and float(ls['price']) > 0:
            info = client.get_symbol_info(ls['symbol'])
            if info['quoteAsset'] == "USDT" and info['status'] == 'TRADING' and info['isSpotTradingAllowed']:
                with open(current_dir+'symbols.txt', 'a') as f:
                    f.write(info['symbol']+'\n')
                    f.close()
                lstselsymbol.append(info['symbol'])
    return lstselsymbol


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


def plot_graph(df):
    df = df.astype(float)
    df[['close', 'MACD', 'signal']].plot()
    plt.xlabel('Date', fontsize=18)
    plt.ylabel('Close price', fontsize=18)
    x_axis = df.index

    plt.scatter(df.index, df['Buy'], color='purple', label='Buy', marker='^', alpha=1)
    plt.scatter(df.index, df['Sell'], color='red', label='Sell', marker='v', alpha=1)

    plt.show()


def trade_logic(symbol):
    in_position = False
    buy_price = 0.00
    #prev_qty = float(getBalance(symbol.replace('USDT', '')))
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

        # with open('output.txt', 'w') as f:
        #     f.write(
        #         symbol_df.to_string()
        #     )
        # plot_graph(symbol_df)

        # get the column=Position as a list of items.
        buy_sell_indicate = symbol_df['Position'].tolist()
        # print(buy_sell_indicate[-1])

        # MACD value for last closing
        MACD_DIF = round(float(symbol_df['MACD'][-2]), 8)
        MACD_DEM = round(float(symbol_df['signal'][-2]), 8)
        MACD_MACD = round(float((-1 * MACD_DEM + MACD_DIF)), 8)

        # RSI value for last closing
        closes = symbol_df['close'].tolist()
        icloses = [float(c) for c in closes]
        np_closes = np.array(icloses)
        rsi = talib.RSI(np_closes, RSI_PERIOD)
        last_rsi = rsi[-2]
        logger.writeLogs('{} - DIF: {} , DEM: {}, MACD: {} :: RSI: {}'
                         .format(symbol, str(MACD_DIF), str(MACD_DEM), str(MACD_MACD), str(last_rsi)),
                         'info', log_filename)

        # Bolinger Bands (upper, middle, lower) value for last closing
        np_close = np.array(icloses, dtype=float)
        upper_bands, middle_bands, lower_bands = talib.BBANDS(np_close, matype=MA_Type.T3)
        f_upper_bands = round(float(upper_bands[-2]), 8)
        f_middle_bands = round(float(middle_bands[-2]), 8)
        f_lower_bands = round(float(lower_bands[-2]), 8)
        #print('Upper : {}, Middle : {}, Lower: {}'.format(f_upper_bands,f_middle_bands,f_lower_bands))

        is_entryPoint = False
        current_price = client.get_symbol_ticker(symbol=symbol)
        f_current_price = round(float(current_price['price']), 8)
        if f_current_price < f_upper_bands and \
                (f_current_price > f_middle_bands or ((f_middle_bands + f_lower_bands)/2) < f_current_price):
            is_entryPoint = True
        # else:
        #     print('Current price {} is greater than upper band price {}'.format(current_price['price'], f_upper_bands))
            # exchange = SuperTrend_BOT.exchange_init()
            # is_uptrend_lst, close_price_lst = SuperTrend_BOT.check_supertrend(exchange, symbol, '2h', 720)
            # last_row_index = len(is_uptrend_lst.index) - 1
            # is_entryPoint = is_uptrend_lst[last_row_index]

        if not(in_position) and is_entryPoint and (MACD_MACD + MACD_DEM) >= 0 and MACD_DIF >= 0 and MACD_DEM <= 0\
                and last_rsi < 60 and last_rsi > 45:   # or (in_position and buy_sell_indicate[-1] == -1.0)
            in_position, buy_price, ordered_qty = buy_or_sell(symbol, 1.0, last_rsi, in_position)

        target_percent = 2
        rev_buy_price = buy_price
        if in_position:
            while True:
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
                # exchange = SuperTrend_BOT.exchange_init()
                # is_uptrend_lst, close_price_lst = SuperTrend_BOT.check_supertrend(exchange, symbol, '2h', 720)
                # last_row_index = len(is_uptrend_lst.index) - 1
                # is_exitPoint = not(is_uptrend_lst[last_row_index])
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
                # elif is_exitPoint:
                #     buy_or_sell(symbol, -1.0, last_rsi, in_position, ordered_qty)
                #     break
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
        exclude_symbols.append(symbol)


def buy_or_sell(symbol, buy_sell, last_rsi, in_position_entry, qty=0):
    start_time = str(datetime.strftime(datetime.now(), "%d%m%Y_%H%M%S"))
    current_price = client.get_symbol_ticker(symbol=symbol)
    cur_price = round(float(current_price['price']), 8)
    ordered_qty = 0
    try:
        # print(current_price['price']) # Output is in json format, only price needs to be accessed
        log = ''
        prev_qty = float(getBalance(symbol.replace('USDT', '')))
        curr_hrs = int(datetime.strftime(datetime.now(), "%H"))
        curr_min = int(datetime.strftime(datetime.now(), "%M"))
        dt_today = datetime.today()  # Local time
        dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
        trade_date = str(dt_India.strftime('%m/%d/%Y %H:%M'))
        '''Live Trade'''
        # currnt_usdt_bal = getBalance('USDT')
        '''Mock Trade'''
        with open(usdt_bal_txt, 'r') as usdt:
            currnt_usdt_bal = float(usdt.readline())
            usdt.close()

        if buy_sell == 1.0 and (last_rsi >= RSI_OVERSOLD and last_rsi <= RSI_OVERBOUGHT):  # signal to buy (either compare with current price to but/sell or use limit order with value
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
                # whats_msg = 'Buy Order \n==========\nOrder Id: {} \nSymbol: {} \nQuantity: {} \nPrice: {} \nAmount: {} \nOrder Status: {}'\
                #             .format(buy_order['orderId'], symbol, ordered_qty, cur_price, buy_order['cummulativeQuoteQty'], buy_order['status'])
                # try:
                #     pw.sendwhatmsg('+919600249294', whats_msg, curr_hrs, (curr_min + 2), 10, True, 5)
                #     time.sleep(145)
                # except:
                #     pass
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
                # whats_msg = 'Sell Order \n==========\nOrder Id: {} \nSymbol: {} \nQuantity: {} \nPrice: {} \nAmount: {} \nOrder Status: {}'\
                #             .format(sell_order['orderId'], symbol, ordered_qty, cur_price, sell_order['cummulativeQuoteQty'], sell_order['status'])
                # try:
                #     pw.sendwhatmsg('+919600249294', whats_msg, curr_hrs, (curr_min + 2), 10, True, 5)
                #     time.sleep(145)
                # except:
                #     pass
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
        error_log = str(ex).replace('\'', '\'\'') + " - trade_logic :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        logger.writeLogs('Error: - Buy_Sell block error - {}'.format(error_log), 'error', log_filename)
    return in_position_entry, cur_price, ordered_qty


def start_trade():
    try:
        #symbols = ['PERLUSDT']
        #symbols = ['XLMUSDT', 'TRXUSDT', 'VENUSDT', 'NULSUSDT', 'VETUSDT', 'BTTUSDT', 'HOTUSDT', 'ZILUSDT', 'FETUSDT', 'IOSTUSDT', 'CELRUSDT', 'MITHUSDT', 'TFUELUSDT', 'ONEUSDT', 'GTOUSDT', 'ERDUSDT', 'DOGEUSDT', 'DUSKUSDT', 'ANKRUSDT', 'WINUSDT', 'COSUSDT', 'NPXSUSDT', 'PERLUSDT', 'DENTUSDT', 'MFTUSDT', 'KEYUSDT', 'STORMUSDT', 'DOCKUSDT', 'FUNUSDT', 'CVCUSDT', 'CHZUSDT', 'BEAMUSDT', 'RVNUSDT', 'HCUSDT', 'HBARUSDT', 'NKNUSDT', 'ARPAUSDT', 'IOTXUSDT', 'CTXCUSDT', 'TROYUSDT', 'VITEUSDT', 'TCTUSDT', 'BTSUSDT', 'LTOUSDT', 'STRATUSDT', 'AIONUSDT', 'MBLUSDT', 'COTIUSDT', 'STPTUSDT', 'DATAUSDT', 'GXSUSDT', 'ARDRUSDT', 'LENDUSDT', 'MDTUSDT', 'STMXUSDT', 'BKRWUSDT', 'SCUSDT', 'VTHOUSDT', 'DGBUSDT', 'AUDUSDT', 'BLZUSDT', 'IRISUSDT', 'JSTUSDT', 'RSRUSDT', 'BZRXUSDT', 'FIOUSDT', 'NBSUSDT', 'OXTUSDT', 'SUNUSDT', 'FLMUSDT', 'UTKUSDT', 'AKROUSDT', 'DNTUSDT', 'ROSEUSDT', 'XEMUSDT', 'SKLUSDT', 'REEFUSDT', 'RIFUSDT', 'TRUUSDT', 'CKBUSDT', 'OMUSDT', 'PONDUSDT', 'LINAUSDT', 'RAMPUSDT', 'CFXUSDT', 'EPSUSDT', 'TLMUSDT', 'SLPUSDT', 'SHIBUSDT', 'MDXUSDT', 'XVGUSDT', 'KEEPUSDT', 'PHAUSDT', 'TVKUSDT', 'ALPACAUSDT', 'FORUSDT', 'REQUSDT', 'WAXPUSDT', 'XECUSDT', 'ELFUSDT', 'POLYUSDT', 'IDEXUSDT', 'GALAUSDT', 'SYSUSDT', 'DFUSDT', 'ADXUSDT', 'QIUSDT', 'POWRUSDT', 'JASMYUSDT', 'AMPUSDT']
        #start_time = str(datetime.strftime(datetime.now(), "%d%m%Y_%H%M%S"))
        symbols = get_symbol()  # get dynamic symbols from binance exchange
        logger.writeLogs('Total symbols are ' + str(len(symbols)), 'info', log_filename)
        logger.writeLogs('{} balance is {}'.format('USDT', usdt_bal), 'info', log_filename)
        while True:
            for idx, symbol in enumerate(symbols):
                if not(symbol in exclude_symbols):
                    #print(' ')
                    #print('======  ', idx + 1, '  ======')
                    #print('current symbol is {}'.format(symbol))
                    # curr_usdt_bal = 100.28613319
                    '''Live Trade'''
                    # curr_usdt_bal = getBalance('USDT')
                    '''Mock Trade'''
                    with open(usdt_bal_txt, 'r') as usdt:
                        curr_usdt_bal = float(usdt.readline())
                        usdt.close()

                    if int(curr_usdt_bal) >= 100 or os.path.exists(current_dir+'current_buy_log.txt'):
                        # buy_BNB()
                        trade_logic(symbol)
                    else:
                        logger.writeLogs('Current USDT balance is < 100 (USDT {})'.format(curr_usdt_bal), 'info', log_filename)
                    #print('======================')
                    logger.writeLogs(symbol + ' - Time sleep for : 2 seconds.....', 'info', log_filename)
                    time.sleep(2)
            logger.writeLogs('Time sleep for : 10 mins.....', 'info', log_filename)
            time.sleep(600)
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
                    # whats_msg = 'Buy Order \n==========\nOrder Id: {} \nSymbol: {} \nQuantity: {} \nPrice: {} \nAmount: {} \nOrder Status: {}'\
                    #             .format(buy_order['orderId'], buy_order['symbol'], buy_quantity, cur_price, buy_order['cummulativeQuoteQty'], buy_order['status'])
                    # try:
                    #     pw.sendwhatmsg('+919600249294', whats_msg, curr_hrs, (curr_min + 2), 10, True, 5)
                    #     time.sleep(145)
                    # except:
                    #     pass
                    logger.writeLogs('Bought BNB for {}'.format(buy_order['cummulativeQuoteQty']), 'info', log_filename)
                else:
                    els_msg = 'Unable to buy BNB for commission purpose. Current BNB worth below {} USDT. Please check and buy it manually.....'.format(bnb_qty_price)
                    # try:
                    #     pw.sendwhatmsg('+919600249294', els_msg, curr_hrs, (curr_min + 2), 10, True, 5)
                    #     time.sleep(145)
                    # except:
                    #     pass
                    logger.writeLogs(els_msg, 'info', log_filename)
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - trade_logic :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        logger.writeLogs(symbol + ' - ' + error_log, 'error', log_filename)


if __name__ == '__main__':
    while True:
        start_time = str(datetime.strftime(datetime.now(), "%d%m%Y_%H%M%S"))
        log_filename = "MACD_RSI_BOT_{}.log".format(start_time)
        current_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../')
        print('current_dir: ',current_dir)
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
            # usdt_bal = 100.28613319
            qty = 0
            s_interval = '15m'  # valid intervals - 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
            RSI_PERIOD = 6
            RSI_OVERBOUGHT = 70
            RSI_OVERSOLD = 30
            exclude_symbols = ['SHIBUSDT', 'VENUSDT', 'FETUSDT', 'ERDUSDT', 'NPXSUSDT', 'STORMUSDT', 'HCUSDT', 'STRATUSDT',
                               'LENDUSDT', 'BKRWUSDT', 'BTTUSDT', 'BZRXUSDT', 'NUUSDT', 'KEEPUSDT', 'AUDUSDT']
            start_trade()
        except Exception as ex:
            error_log = str(ex).replace('\'', '\'\'') + " - trade_logic :: line ::" \
                        + str(sys.exc_info()[2].tb_lineno)
            logger.writeLogs('Error: - Main error - {}'.format(error_log), 'error', log_filename)
            logger.writeLogs('Time sleep for : 1 min......', 'error', log_filename)
            time.sleep(60)
            continue
