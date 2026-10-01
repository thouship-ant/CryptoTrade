import sys, os
import time
from datetime import datetime
from pytz import timezone
import ccxt
import schedule
import pandas as pd
import pywhatkit as pw
import config
import warnings
warnings.filterwarnings('ignore')
from logger import logger


def exchange_init():
    bin_exchange = ccxt.binance({
        'apiKey': config.BINANCE_API_KEY,
        'secret': config.BINANCE_API_SECRET
    })
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
        logger.writeLogs(':: Error: - Main error - ' + error_log, 'error', log_filename)
        return [], []


def tr(df):
    df['previous_close'] = df['close'].shift(1)
    df['high-low'] = abs(df['high'] - df['low'])
    df['high-pc'] = abs(df['high'] - df['previous_close'])
    df['low-pc'] = abs(df['low'] - df['previous_close'])
    tr = df[['high-low', 'high-pc', 'low-pc']].max(axis=1)
    return tr


def atr(df, period):
    df['tr'] = tr(df)
    # logger.writeLogs('calculating average true range', 'info', log_filename)
    atr = df['tr'].rolling(period).mean()
    return atr


def supertrend(df, period=7, multiplier=3):
    # logger.writeLogs('calculating supertrend', 'info', log_filename)
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


def check_buy_sell_signal(exchange, symbol, buy_sell_signal, qty, cur_price):
    global in_position
    start_time = str(datetime.strftime(datetime.now(), "%d%m%Y_%H%M%S"))
    curr_hrs = int(datetime.strftime(datetime.now(), "%H"))
    curr_min = int(datetime.strftime(datetime.now(), "%M"))
    dt_today = datetime.today()  # Local time
    dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
    trade_date = str(dt_India.strftime('%m/%d/%Y %H:%M'))
    whats_msg = ''
    '''Live Trade'''
    # usdt_balance = float([d['free'] for d in exchange.fetch_balance()['info']['balances'] if d['asset'] == 'USDT'][0])
    '''Mock Trade'''
    with open(usdt_bal_txt, 'r') as usdt:
        usdt_balance = float(usdt.readline())
        usdt.close()
    if buy_sell_signal == 'buy':
        '''Live Trade'''
        # order_buy = exchange.create_market_buy_order(symbol, qty)
        # order_buy_info = order_buy['info']
        # logger.writeLogs(str(order_buy), 'info', log_filename)
        # cur_price = order_buy['price']
        '''Mock Trade'''
        df_read = pd.read_csv(trade_report_csv)
        order_buy_info = {}
        order_buy_info['orderId'] = str(len(df_read)+1)
        order_buy_info['cummulativeQuoteQty'] = float(qty * cur_price)
        usdt_balance = usdt_balance - order_buy_info['cummulativeQuoteQty']
        with open(usdt_bal_txt, 'w') as usdt:
            usdt.write(str(usdt_balance))
            usdt.close()

        with open(current_dir+'supertrend_current_buy_log.txt', 'w') as f:
            buy_log = '{}|{}|{}|{}'.format(order_buy_info['orderId'], symbol, str(qty), str(cur_price))
            f.write(buy_log)
            f.close()
        with open(trade_report_csv, 'a') as csv:
            trade_report = '\n{},{},SuperTrend,{},{},{},{}'\
                .format(order_buy_info['orderId'], trade_date, symbol, str(qty), str(cur_price),
                        str(order_buy_info['cummulativeQuoteQty']))
            csv.write(trade_report)
            csv.close()
        in_position = True
        logger.writeLogs('{} is bought successfully at {} == qty : {} === amount : {}'
                         .format(symbol, str(cur_price), str(qty), str(order_buy_info['cummulativeQuoteQty'])),
                         'info', log_filename)
        whats_msg = 'Bought {} at {} == qty : {} === amount : {}'.format(symbol, str(cur_price), str(qty),
                                                                         str(order_buy_info['cummulativeQuoteQty']))
        # try:
        #     pw.sendwhatmsg('+919600249294', whats_msg, curr_hrs, (curr_min + 2), 20, True, 5)
        #     time.sleep(145)
        # except:
        #     pass
    else:
        '''Live Trade'''
        # order_sell = exchange.create_market_sell_order(symbol, qty)
        # order_sell_info = order_sell['info']
        # logger.writeLogs(str(order_sell), 'info', log_filename)
        # cur_price = order_sell['price']
        '''Mock Trade'''
        order_sell_info = {}
        order_sell_info['cummulativeQuoteQty'] = float(qty * cur_price)
        usdt_balance = usdt_balance + order_sell_info['cummulativeQuoteQty']
        with open(usdt_bal_txt, 'w') as usdt:
            usdt.write(str(usdt_balance))
            usdt.close()

        if os.path.exists(current_dir+'supertrend_current_buy_log.txt'):
            os.remove(current_dir+'supertrend_current_buy_log.txt')

        flk_report = trade_report_csv_path + '/supertrend_current_buy.txt'
        if os.path.exists(flk_report):
            os.remove(flk_report)

        with open(trade_report_csv, 'a') as csv:
            trade_report = ',{},{},{}'.format(str(cur_price), str(order_sell_info['cummulativeQuoteQty']), trade_date)
            csv.write(trade_report)
            csv.close()
        in_position = False
        logger.writeLogs('{} is sold successfully at {} == qty : {} === amount : {}'
                         .format(symbol, str(cur_price), str(qty), str(order_sell_info['cummulativeQuoteQty'])),
                         'info', log_filename)
        whats_msg = 'Sold {} at {} == qty : {} === amount : {}'.format(symbol, str(cur_price), str(qty),
                                                                       str(order_sell_info['cummulativeQuoteQty']))
        # try:
        #     pw.sendwhatmsg('+919600249294', whats_msg, curr_hrs, (curr_min + 2), 20, True, 5)
        #     time.sleep(145)
        # except:
        #     pass
    if whats_msg != '':
        with open(current_dir+'supertrend_buy_sell_log.txt', 'a') as f:
            log = str(start_time) + ':: ' + whats_msg + '\n'
            f.write(log)
            f.close()


def main(exchange, symbol):
    global qty, time_interval, in_position
    buy_price = 0
    in_position = False
    if os.path.exists(current_dir+'supertrend_current_buy_log.txt'):
        with open(current_dir+'supertrend_current_buy_log.txt', 'r') as f:
            buy_log = str(f.readline())
            print(buy_log)
            str_split = buy_log.split('|')
            symbol = str_split[1]
            qty = int(float(str_split[2]))
            buy_price = float(str_split[3])
            in_position = True
    is_uptrend_lst, close_price_lst = check_supertrend(exchange, symbol, '2h', 60)
    last_row_index = len(is_uptrend_lst.index) - 1
    previous_row_index = last_row_index - 1
    # cur_price = close_price_lst[last_row_index]
    symbol_info = exchange.fetch_ticker(symbol)['info']
    cur_price = float(symbol_info['askPrice'])
    logger.writeLogs('{} - current price is {} ==== In position : {} ==== Is Uptrend : {}'
                     .format(symbol, str(cur_price), str(in_position), str(is_uptrend_lst[last_row_index])), 'info', log_filename)
    '''Live Trade USDT'''
    # usdt_balance = float([d['free'] for d in exchange.fetch_balance()['info']['balances'] if d['asset'] == 'USDT'][0])
    '''Mock Trade USDT'''
    with open(usdt_bal_txt, 'r') as usdt:
        usdt_balance = float(usdt.readline())
        usdt.close()
    if usdt_balance >= 100 or in_position:
        logger.writeLogs('Current USDT balance is {}'.format(str(usdt_balance)), 'info', log_filename)
        if os.path.exists(current_dir+'current_buy_log.txt'):
            buy_amount = usdt_balance
        else:
            buy_amount = usdt_balance / 2

        if (not is_uptrend_lst[previous_row_index] and is_uptrend_lst[last_row_index]) or in_position:
            if not in_position:
                logger.writeLogs('changed to uptrend -- Buy signal', 'info', log_filename)
                qty = int((buy_amount - 0.25) / cur_price)
                check_buy_sell_signal(exchange, symbol, 'buy', qty, cur_price)

            if in_position:
                if buy_price == 0:
                    buy_price = cur_price
                target_percent = 1.5
                while True:
                    is_uptrend_lst, close_price_lst = check_supertrend(exchange, symbol, '2h', 60)
                    last_row_index = len(is_uptrend_lst.index) - 1
                    previous_row_index = last_row_index - 1
                    # cur_price = close_price_lst[last_row_index]
                    symbol_info = exchange.fetch_ticker(symbol)['info']
                    cur_price = float(symbol_info['bidPrice'])
                    current_percent = round(float((cur_price - buy_price) / (buy_price / 100)), 2)
                    target_price = round(float(buy_price + (buy_price * target_percent / 100)), 5)
                    if os.path.exists(current_dir+'supertrend_current_buy_log.txt'):
                        with open(current_dir+'supertrend_current_buy_log.txt', 'r') as f:
                            supertrend_buy_log = str(f.readline())
                            flk_report = trade_report_csv_path + '/supertrend_current_buy.txt'
                            with open(flk_report, 'w') as flk:
                                supertrend_buy_log += '|{}|{}|{}'.format(cur_price, current_percent, target_price)
                                flk.write(supertrend_buy_log)

                    if cur_price >= target_price:
                        logger.writeLogs('Target achieved -- Sell signal', 'info', log_filename)
                        check_buy_sell_signal(exchange, symbol, 'sell', qty, cur_price)
                        break
                    if is_uptrend_lst[previous_row_index] and not is_uptrend_lst[last_row_index]:
                        logger.writeLogs('changed to downtrend -- Sell signal', 'info', log_filename)
                        check_buy_sell_signal(exchange, symbol, 'sell', qty, cur_price)
                        break

                    logger.writeLogs(
                        '{} - Time sleep for : 15 minute..... - qty : {} == price : {} ({} %) - Target : {}'
                        .format(symbol, qty, cur_price, current_percent, target_price),
                        'info', log_filename)
                    time.sleep(58)
    else:
        if usdt_balance < 100:
            logger.writeLogs('Current USDT balanace is less than 100.....', 'info', log_filename)


if __name__ == "__main__":
    start_time = str(datetime.strftime(datetime.now(), "%d%m%Y_%H%M%S"))
    log_filename = "SuperTrend_BOT_{}.log".format(start_time)
    # print(check_supertrend('ALPACAUSDT', '1h', 31))
    exchange = exchange_init()
    symbols = ['ACA', 'AGLD', 'BETA', 'FTM', 'API3', 'CELO', 'CHZ', 'DAR', 'DREP', 'GALA', 'INJ', 'LOKA', 'MANA',
               'MBOX', 'PEOPLE', 'POND', 'SLP', 'STMX', 'STORJ', 'TLM', 'TVK', 'UTK', 'VOXEL', 'CFX']
    current_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../')
    print('current_dir: ', current_dir)
    trade_report_csv_path = current_dir+'../candlestick-screener-master/report'
    if not os.path.exists(trade_report_csv_path):
        os.makedirs(trade_report_csv_path)
    trade_report_csv = trade_report_csv_path + '/supertrend_trade_report.csv'
    '''Mock Trade USDT'''
    usdt_bal_txt = trade_report_csv_path + '/usdt_bal.txt'

    if not os.path.exists(trade_report_csv):
        with open(trade_report_csv, 'w') as csv:
            trade_report_head = 'Order ID,Order Date,Signal Type,Symbol Name,Ordered Qty.,Buy Price,Buy Amount,Sell Price,Sell Amount,Update Date'
            csv.write(trade_report_head)
            csv.close()

    while True:
        try:
            for symbol in symbols:
                symbol += 'USDT'
                main(exchange, symbol)
            time.sleep(290)
        except Exception as ex:
            error_log = str(ex).replace('\'', '\'\'') + " - __main__ :: line ::" \
                        + str(sys.exc_info()[2].tb_lineno)
            logger.writeLogs('Error: - Main error - {}'.format(error_log), 'error', log_filename)
            logger.writeLogs('Time sleep for : 1 min......', 'error', log_filename)
            time.sleep(60)
            continue
