from utils import config
from telethon import TelegramClient, events
from datetime import datetime
from pytz import timezone
import time, sys, os
import pyscreenshot
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from src.utils import db_util
from src.data import DB_Signal_Query as dbsq
import warnings
warnings.filterwarnings('ignore')


# Reading Configs
# Setting configuration values
api_id = config.api_id
api_hash = str(config.api_hash)

phone = config.phone
username = config.username

# Create the client and connect
client = TelegramClient(username, api_id, api_hash)


def insert_signal(symbol_name, signal_side, entry_price, tg1, tg2, tg3, tg4, stop_price=0):
    try:
        dt_today = datetime.today()  # Local time
        dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
        trade_date = str(dt_India.strftime('%Y-%m-%d'))
        entry_date = str(dt_India.strftime('%Y-%m-%d %H:%M:%S'))
        price_prec = dbsq.symbol_precision(None, symbol_name=symbol_name)
        entry_price = round(float(entry_price), price_prec)
        exit_price = round(float(tg4), price_prec)
        tg1 = round(float(tg1), price_prec)
        tg2 = round(float(tg2), price_prec)
        tg3 = round(float(tg3), price_prec)
        if stop_price == 0:
            stop_price = round(float(entry_price - ((entry_price * 2) / 100)), price_prec)
            if signal_side == 'SHORT':
                stop_price = round(float(entry_price + ((entry_price * 2) / 100)), price_prec)
        else:
            stop_price = round(float(stop_price), price_prec)
        connection = db_util.connect_database()
        if connection.is_connected():
            check_query = """SELECT `trade_id` FROM `ant_cryptotradingbot`.`db_telegram_trade_signals` 
            where `symbol_name`='{}' and `trade_closed` = False and `is_tradeable` = True;"""\
                .format(symbol_name)
            check_query_done = db_util.queryExecution(connection, check_query, 'select')
            if len(check_query_done) == 0:
                insert_query = """INSERT `ant_cryptotradingbot`.`db_telegram_trade_signals` (`trade_date`, `symbol_name`, `signal_side`, 
                `entry_price`, `exit_price`, `stop_price`, `entry_date`, `target_price_1`, `target_price_2`, `target_price_3`, `target_price_4`)  
                VALUES ('{}','{}','{}',{},{},{},'{}',{},{},{},{});""" \
                    .format(trade_date, symbol_name, signal_side, entry_price, exit_price, stop_price, entry_date, tg1, tg2, tg3, exit_price)
                is_updated = db_util.queryExecution(connection, insert_query, 'insert')
                print(insert_query)
                if is_updated == True:
                    print('=== Entry === Symbol ::: {} , Signal ::: Telegram - {} , Entry Price ::: {} , Exit Price ::: {} , Stop Price ::: {} , Is_Inserted ::: {} ===='
                                     .format(symbol_name, signal_side, entry_price, exit_price, stop_price, is_updated))
                else:
                    print('!!!=== Unable to insert === Query ::: {} ===='
                                     .format(insert_query))
            else:
                print('=== Already Symbol exist === Symbol ::: {} , Signal ::: Telegram - {} , Entry Price ::: {} , Exit Price ::: {} ===='
                                 .format(symbol_name, signal_side, entry_price, exit_price))
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - insert_signal :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print('Error: - Insert signal error - {}'.format(error_log))


def update_signal(symbol_name, signal_side, exit_price):
    try:
        dt_today = datetime.today()  # Local time
        dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
        exit_date = str(dt_India.strftime('%Y-%m-%d %H:%M:%S'))
        price_prec = dbsq.symbol_precision(None, symbol_name=symbol_name)
        if exit_price > 0:
            exit_price = round(float(exit_price), price_prec)
        connection = db_util.connect_database()
        if connection.is_connected():
            check_query = """SELECT `trade_id`, `entry_price`, `exit_price` FROM `ant_cryptotradingbot`.`db_telegram_trade_signals` 
            where `symbol_name`='{}' and `trade_closed` = False and `is_tradeable` = True;"""\
                .format(symbol_name, signal_side)
            check_query_done = db_util.queryExecution(connection, check_query, 'select')
            if len(check_query_done) == 1:
                entry_price = round(float(check_query_done[0][1]), price_prec)
                if exit_price == 0:
                    exit_price = round(float(check_query_done[0][2]), price_prec)
                isStopLoss = False
                if (entry_price > exit_price and signal_side == 'LONG') or (entry_price < exit_price and signal_side == 'SHORT'):
                    isStopLoss = True
                    
                insert_query = """UPDATE `ant_cryptotradingbot`.`db_telegram_trade_signals` SET  `trade_closed` = True, `exit_date`='{}', `is_stoploss_hit`={}
                WHERE `symbol_name`='{}' and `trade_closed` = False and `is_tradeable` = True;""" \
                    .format(exit_date, isStopLoss, symbol_name)
                is_updated = db_util.queryExecution(connection, insert_query, 'update')
                print('=== Exit === Symbol ::: {} , Signal ::: Telegram - {} , Entry Price ::: {} , Exit Price ::: {} , Is_Inserted ::: {} ===='
                                 .format(symbol_name, signal_side, entry_price, exit_price, is_updated))
            else:
                print('=== No Symbol exist for close === Symbol ::: {} , Signal ::: Telegram - {} , Exit Price ::: {} ===='
                                 .format(symbol_name, signal_side, exit_price))
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - insert_signal :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print('Error: - Insert signal error - {}'.format(error_log))


def gold_vip_data(event):
    if '/usdt' in event.raw_text.lower() and ('idea' in event.raw_text.lower() or 'direction' in event.raw_text.lower()) and ('max leverage' in event.raw_text.lower() or 'freesignal' in event.raw_text.lower()) and 'entry' in event.raw_text.lower() and ('target 1' in event.raw_text.lower() or 'target profit 1' in event.raw_text.lower()):
        print('GOLD_VIP: ', event.raw_text)
        symbol_name = ''
        signal_side = ''
        entry_price = 0.00
        tg1 = 0.00
        tg2 = 0.00
        tg3 = 0.00
        tg4 = 0.00
        stop_price = 0.00
        raw_content = event.raw_text
        while '  ' in raw_content:
            raw_content = raw_content.replace('  ', ' ')
        contents = raw_content.split('\n')
        for line in contents:
            if '/usdt' in line.lower():
                read = line.split(' ')
                if 'coin name' in line.lower():
                    symbol_name = read[2].replace('#', '').replace('/', '').upper()
                else:
                    symbol_name = read[1].replace('#', '').replace('/', '').upper()
            elif 'idea' in line.lower():
                read = line.split(' ')
                if read[1].lower() == 'bullish':
                    signal_side = 'LONG'
                elif read[1].lower() == 'bearish':
                    signal_side = 'SHORT'
            elif 'direction' in line.lower():
                read = line.split(' ')
                signal_side = read[1].upper()
            elif 'entry:' in line.lower():
                read = line.split(' ')
                for word in read:
                    if '-' in word.lower() and entry_price == 0:
                        readword = word.split('-')
                        entry_price = float(readword[0].replace('$', '').strip())
            elif 'entry' in line.lower():
                read = line.split(' ')
                for word in read:
                    if '.' in word.lower() and entry_price == 0:
                        entry_price = float(word.replace('$', '').strip())
            elif 'target 1' in line.lower() or 'target profit 1' in line.lower():
                read = line.split(' ')
                tg1 = float(read[3].replace('$', '').strip())
            elif 'target 2' in line.lower() or 'target profit 2' in line.lower():
                read = line.split(' ')
                tg2 = float(read[3].replace('$', '').strip())
            elif 'target 3' in line.lower() or 'target profit 3' in line.lower():
                read = line.split(' ')
                tg3 = float(read[3].replace('$', '').strip())
            elif 'target 4' in line.lower() or 'target profit 4' in line.lower():
                read = line.split(' ')
                tg4 = float(read[3].replace('$', '').strip())
            elif 'stop' in line.lower() and 'loss' in line.lower():
                read = line.split(' ')
                if 'stop | loss' in line.lower():
                    stop_price = float(read[5].replace('$', '').strip())
                elif 'stop loss' in line.lower():
                    stop_price = float(read[3].replace('$', '').strip())
                elif 'stoploss' in line.lower():
                    stop_price = float(read[1].replace('$', '').strip())
        print('=== Extracted === Symbol ::: {} , Signal ::: Telegram - {} , Entry Price ::: {} , Target 1 ::: {} , Target 2 ::: {} , Target 3 ::: {} , Target 4 ::: {} , Stop Price ::: {} ===='
                         .format(symbol_name, signal_side, entry_price, tg1, tg2, tg3, tg4, stop_price))
        insert_signal(symbol_name, signal_side, entry_price, tg1, tg2, tg3, tg4, stop_price=stop_price)
    elif '/usdt' in event.raw_text.lower() and 'achieved' in event.raw_text.lower() and 'total profit' in event.raw_text.lower():
        symbol_name = ''
        signal_side = ''
        exit_price = 0.00
        exit_percent = 0
        while '  ' in event.raw_text:
            event.raw_text = event.raw_text.replace('  ', ' ')
        contents = event.raw_text.split('\n')
        for line in contents:
            if '/usdt' in line.lower():
                print(line)
                read = line.split(' ')
                for word in read:
                    if '/usdt' in word.lower():
                        print(word)
                        symbol_name = word.replace('#', '').replace('/', '').upper()
            elif 'total profit' in line.lower():
                read = line.split(' ')
                exit_percent = str(read[4])
        print('=== Extracted === Symbol ::: {} , Signal ::: Telegram, Exit Percent ::: {} ===='
                         .format(symbol_name, exit_percent))
        update_signal(symbol_name, signal_side, exit_price)


def marco_vip_data(event):
    if 'new signal' in event.raw_text.lower():
        print('Marco_Polo_VIP_CLUB: ', event.raw_text)
        symbol_name = ''
        signal_side = ''
        entry_price = 0.00
        tg1 = 0.00
        tg2 = 0.00
        tg3 = 0.00
        tg4 = 0.00
        while '  ' in event.raw_text:
            event.raw_text = event.raw_text.replace('  ', ' ')
        contents = event.raw_text.split('\n')
        for line in contents:
            if '/usdt' in line.lower():
                read = line.split(' ')
                symbol_name = read[0].replace('#', '').replace('/', '').upper()
                signal_side = read[1].replace('(', '').replace(',', '').upper()
            elif 'entry' in line.lower():
                read = line.split(' ')
                entry_price = float(read[2])
            elif 'tp1' in line.lower():
                read = line.split(' ')
                tg1 = float(read[1])
            elif 'tp2' in line.lower():
                read = line.split(' ')
                tg2 = float(read[1])
            elif 'tp3' in line.lower():
                read = line.split(' ')
                tg3 = float(read[1])
            elif 'tp4' in line.lower():
                read = line.split(' ')
                tg4 = float(read[1])
        print('=== Extracted === Symbol ::: {} , Signal ::: Telegram - {} , Entry Price ::: {} , Target 1 ::: {} , Target 2 ::: {} , Target 3 ::: {} , Target 4 ::: {} ===='
                         .format(symbol_name, signal_side, entry_price, tg1, tg2, tg3, tg4))
        insert_signal(symbol_name, signal_side, entry_price, tg1, tg2, tg3, tg4)
    elif '/usdt' in event.raw_text.lower() and 'price - ' in event.raw_text.lower() and 'profit - ' in event.raw_text.lower():
        symbol_name = ''
        signal_side = ''
        exit_price = 0.00
        exit_percent = 0
        while '  ' in event.raw_text:
            event.raw_text = event.raw_text.replace('  ', ' ')
        contents = event.raw_text.split('\n')
        for line in contents:
            if '/usdt' in line.lower():
                read = line.split(' ')
                symbol_name = read[0].replace('#', '').replace('/', '').upper()
                signal_side = read[1].replace('(', '').replace(',', '').upper()
            elif 'price -' in line.lower():
                read = line.split(' ')
                exit_price = float(read[3])
            elif 'profit -' in line.lower():
                read = line.split(' ')
                exit_percent = str(read[3])
        print('=== Extracted === Symbol ::: {} , Signal ::: Telegram - {} , Exit Price ::: {} , Exit Percent ::: {} ===='
                         .format(symbol_name, signal_side, exit_price, exit_percent))
        update_signal(symbol_name, signal_side, exit_price)


# def take_pic():
    # try:
        # img = pyscreenshot.grab()
        # current_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../')
        # img_folder = current_dir + 'scr_images/'
        # if not os.path.exists(img_folder):
            # os.makedirs(img_folder)
        # dt_today = datetime.today()  # Local time
        # dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
        # imagename = str(datetime.strftime(dt_India, "%d%m%Y%H%M%S"))
        # name = img_folder + imagename + ".png"
        # img.save(name)
        # return name
    # except Exception as ex:
        # error_log = str(ex).replace('\'', '\'\'') + " - insert_signal :: line ::" \
                    # + str(sys.exc_info()[2].tb_lineno)
        # print('Error: - Taken scr error - {}'.format(error_log))
        # return ''
        
      
# -1001446149432 - marco_vip
@client.on(events.NewMessage(chats=-1001446149432))
async def my_event_handler(event):
    marco_vip_data(event)


# -1001446149432 - GOLD_VIP
@client.on(events.NewMessage(chats=-1001427013917))
async def my_event_handler(event):
    gold_vip_data(event)


#-766017680 - ANT CryptoBot
@client.on(events.NewMessage(chats=-766017680))
async def my_event_handler(event):
    print('ANT CryptoBot: ', event.raw_text)
    if event.raw_text.lower().startswith('goldvip') or event.raw_text.lower() == 'gold vip':
        gold_vip_data(event)
    elif event.raw_text.lower().startswith('marcovip') or event.raw_text.lower() == 'marcovip':
        marco_vip_data(event)


while True:
    try:
        client.start()
        client.run_until_disconnected()
    except:
        continue