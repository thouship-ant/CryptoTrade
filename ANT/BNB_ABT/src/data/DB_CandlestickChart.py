import os, sys, time, gc
import pandas as pd
import ccxt
import talib
from datetime import datetime, timedelta
from pytz import timezone
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from src.utils import db_util
from src.utils import chart_data as cd
from src.utils import supRes_level as srl
#from utils.logger import logger
import warnings
warnings.filterwarnings('ignore')


def download_data(symbol, limit=480):
    try:
        pd.set_option('display.max_rows', None)
        pd.options.mode.chained_assignment = None  # default='warn'
        exchange = ccxt.binance()
        bars = exchange.fetch_ohlcv(symbol.replace('1000', ''), timeframe='15m', limit=limit)
        df = pd.DataFrame(bars, columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df['Date'] = pd.to_datetime(df['Date'], unit='ms')
        # df['Adj Close'] = df['Close']
        last_date = str(df['Date'][df.index[-1]].strftime('%Y-%m-%d'))
        dt_yesterday = datetime.today() - timedelta(days=1)
        dt_India_yesterday = dt_yesterday.astimezone(timezone('Asia/Kolkata'))
        trade_date_yesterday = str(dt_India_yesterday.strftime('%Y-%m-%d'))
        dt_today = datetime.today()
        dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
        trade_date = str(dt_India.strftime('%Y-%m-%d'))
        time.sleep(4)
        if last_date == trade_date_yesterday or last_date == trade_date:
            return df
        else:
            return []
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - download_data :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print('Error: - Download data block error - {} - for {}'.format(error_log, symbol.replace('1000', '')))
        return []
    finally:
        gc.collect()


def pattern_signal_data():
    try:
        connection = db_util.connect_database()
        if connection.is_connected():
            """Pattern signal"""
            update_query = """TRUNCATE TABLE `ant_cryptotradingbot`.`live_patterns_signal`;"""
            update_result = db_util.queryExecution(connection, update_query, 'update')
            query = 'SELECT `PatternName`,`KeyWord` from `ant_cryptotradingbot`.`CS_Patterns` where is_active = true order by `s_no` asc'
            pattern_list = db_util.queryExecution(connection, query, 'select')
            if len(pattern_list) > 0:
                for pattern in pattern_list:
                    pattern_function = getattr(talib, pattern[1])
                    query = 'SELECT symbol_name from `ant_cryptotradingbot`.`crypto_symbols_data` where is_active = true order by `symbol_id` asc'
                    get_symbol_list = db_util.queryExecution(connection, query, 'select')
                    if len(get_symbol_list) > 0:
                        for symbol_name in get_symbol_list:
                            symbol = symbol_name[0]
                            try:
                                query_data = "SELECT DateTime as 'Date',Open,High,Low,Close from `ant_cryptotradingbot`.`{}`" \
                                    .format(symbol)
                                df = pd.read_sql(query_data, connection)
                                round = 0
                                while len(df.index) == 0 and round < 5:
                                    df = pd.read_sql(query_data, connection)
                                    time.sleep(1)
                                    round += 1
                                results = pattern_function(df['Open'], df['High'], df['Low'], df['Close'])
                                last = results.tail(1).values[0]

                                if last > 0:
                                    pattern_signal = 'bullish'
                                elif last < 0:
                                    pattern_signal = 'bearish'
                                else:
                                    pattern_signal = ''

                                if pattern_signal != '':
                                    update_query = """INSERT INTO `ant_cryptotradingbot`.`live_patterns_signal` (`symbol_name`,`PatternName`,`SignalType`) 
                                    VALUES ('{}','{}','{}');""" \
                                        .format(symbol, pattern[0], pattern_signal)
                                    update_result = db_util.queryExecution(connection, update_query, 'update')
                            except Exception as e:
                                error_log = str(e).replace('\'', '\'\'') + " - main :: line ::" \
                                            + str(sys.exc_info()[2].tb_lineno)
                                print('failed on symbol: {} - error ::: {}'.format(symbol, error_log))
                                del_qry = "UPDATE `ant_cryptotradingbot`.`crypto_symbols_data` SET `is_Active` = False WHERE `symbol_name`='{}';" \
                                    .format(symbol)
                                db_util.queryExecution(connection, del_qry, 'insert')
                            finally:
                                del df
                                del results
                                gc.collect()
        connection.close()
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - pattern_signal :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print('Error: - Pattern signal block error - {}'.format(error_log))


def start_cs_tool():
    cur_symbol = ''
    try:
        while True:
            dt_today = datetime.today()  # Local time
            dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
            current_date = str(datetime.strftime(dt_India, "%d%m%Y"))
            if start_date != current_date:
                sys.exit()
            connection = db_util.connect_database()
            if connection.is_connected():
                query = 'SELECT symbol_name from `ant_cryptotradingbot`.`crypto_symbols_data` where is_active = true order by `symbol_id` asc limit {} offset {}'\
                    .format(limit, offset)
                get_symbol_list = db_util.queryExecution(connection, query, 'select')
                if len(get_symbol_list) > 0:
                    symbols_count = 0
                    insert_count = 0
                    for symbol_name in get_symbol_list:
                        cur_symbol = symbol_name[0]
                        is_create_table_query = False
                        chart_data = []
                        volume_data = []
                        sr_data = ''
                        table_check_query = "SELECT table_name from information_schema.tables where table_schema = 'ant_cryptotradingbot' and table_name = '{}';"\
                            .format(symbol_name[0])
                        is_table_check_query = db_util.queryExecution(connection, table_check_query, 'select')
                        if len(is_table_check_query) == 0:
                            create_table_query = "CREATE TABLE `ant_cryptotradingbot`.`{}` (`s_no` INT AUTO_INCREMENT NOT NULL,`DateTime` DATETIME NOT NULL,`Open` DECIMAL(12,8) NOT NULL,`High` DECIMAL(12,8) NOT NULL,`Low` DECIMAL(12,8) NOT NULL,`Close` DECIMAL(12,8) NOT NULL,`Volume` BIGINT NOT NULL,PRIMARY KEY (`s_no`));" \
                                .format(symbol_name[0])
                            is_create_table_query = db_util.queryExecution(connection, create_table_query, 'insert')
                        elif len(is_table_check_query) == 1:
                            create_table_query = "TRUNCATE TABLE `ant_cryptotradingbot`.`{}`;" \
                                .format(symbol_name[0])
                            is_create_table_query = db_util.queryExecution(connection, create_table_query, 'insert')
                        if len(is_table_check_query) == 1 or is_create_table_query:
                            pd_data = download_data(symbol_name[0])
                            lst_trade_date = []
                            print('Symbol ::: {} - data_length ::: {}'.format(symbol_name[0], len(pd_data.values)))
                            if len(pd_data.values) > 0:
                                for i,data in pd_data.iterrows():
                                    dt_date = datetime(int(data['Date'].strftime('%Y')),int(data['Date'].strftime('%m')),
                                                       int(data['Date'].strftime('%d')),int(data['Date'].strftime('%H')),
                                                       int(data['Date'].strftime('%M')),int(data['Date'].strftime('%S'))) \
                                              + timedelta(minutes=330)
                                    trade_date = str(dt_date.strftime('%Y-%m-%d %H:%M:%S'))
                                    insert_query = "INSERT INTO `ant_cryptotradingbot`.`{}` (`DateTime`,`Open`,`High`,`Low`,`Close`,`Volume`) VALUES ('{}',{},{},{},{},{});"\
                                        .format(symbol_name[0], trade_date, data['Open'], data['High'], data['Low'],
                                                data['Close'], data['Volume'])
                                    is_insert_query = db_util.queryExecution(connection, insert_query, 'insert')
                                    if is_insert_query:
                                        insert_count += 1
                                #    str_data = "x: '{}',y: [{}, {}, {}, {}]"\
                                #        .format(trade_date, data['Open'], data['High'], data['Low'], data['Close'])
                                #    str_data = "{" + str_data + "}"
                                #    vol_data = "x: '{}',y: {}" \
                                #        .format(trade_date, data['Volume'])
                                #    vol_data = "{" + vol_data + "}"
                                #    chart_data.append(str_data)
                                #    volume_data.append(vol_data)
                                    lst_trade_date.append(trade_date)
                                del_qry = "DELETE FROM `ant_cryptotradingbot`.`symbol_support_resistance` WHERE `symbol_name`='{}';" \
                                    .format(symbol_name[0])
                                is_del_qry = db_util.queryExecution(connection, del_qry, 'insert')
                                ss, rr = srl.main(symbol_name[0])
                                ss = ss[-2:]
                                rr = rr[-2:]
                                for support in ss:
                                    trade_date = lst_trade_date[support[0]+384]
                                    insert_qry = "INSERT INTO `ant_cryptotradingbot`.`symbol_support_resistance` (`symbol_name`,`Date`,`Type`,`Value`) VALUES ('{}','{}','{}',{});"\
                                        .format(symbol_name[0], trade_date, "Support", support[1])
                                    is_insert_query = db_util.queryExecution(connection, insert_qry, 'insert')
                                    #sr_data += ", {name: 'Support',type: 'line',data: [{x: '" + trade_date + "',y: " + \
                                    #           str(support[1]) + "}, {x: '" + lst_trade_date[-1] + "',y: " + str(support[1]) + "}]}"
                                for res in rr:
                                    trade_date = lst_trade_date[res[0]+384]
                                    insert_qry = "INSERT INTO `ant_cryptotradingbot`.`symbol_support_resistance` (`symbol_name`,`Date`,`Type`,`Value`) VALUES ('{}','{}','{}',{});"\
                                        .format(symbol_name[0], trade_date, "Resistance", res[1])
                                    is_insert_query = db_util.queryExecution(connection, insert_qry, 'insert')
                                    #sr_data += ", {name: 'Resistance',type: 'line',data: [{x: '" + trade_date + "',y: " + \
                                    #           str(res[1]) + "}, {x: '" + lst_trade_date[-1] + "',y: " + str(res[1]) + "}]}"
                                #str_chart_data = str(chart_data[384:480]).replace('"{', "{").replace('}"', "}")
                                #str_volume_data = str(volume_data[384:480]).replace('"{', "{").replace('}"', "}")\
                                #    .replace('[', "").replace(']', "")
                                #cd.create_chart(symbol=symbol_name[0], chartData=str_chart_data, volData=str_volume_data, srData=sr_data)
                                symbols_count += 1
                                time.sleep(1)
                            del pd_data
                            gc.collect()
                    print('====Total Symbols are {} ({} entries) ===='.format(symbols_count, insert_count))

                    if int(limit) == 100:
                        while not os.path.exists(cs_batch_check):
                            print(
                                'Time sleep for : 30 seconds...... "cs_batch_check" -- limit : {}'.format(limit)
                                )
                            time.sleep(30)
                        pattern_signal_data()
                        if os.path.exists(cs_batch_check):
                            os.remove(cs_batch_check)
                        print('Time sleep for : 30 seconds......')
                        time.sleep(30)
                    else:
                        with open(cs_batch_check, 'w') as bat:
                            bat.write("waiting...")
                            bat.close()
                    while os.path.exists(cs_batch_check):
                        print('Time sleep for : 30 seconds...... "cs_batch_check" -- offset : {}'.format(offset)
                                         )
                        time.sleep(30)

                    print('Time sleep for : 2 minutes......')
                    time.sleep(120)
                else:
                    print('Time sleep for : 1 min......')
                    time.sleep(60)
            connection.close()
            gc.collect()
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - start_ta_tool :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print('Symbol {} :: Error: - Start CS tool block error - {}'.format(cur_symbol, error_log))
        connection = db_util.connect_database()
        if connection.is_connected():
            del_qry = "UPDATE `ant_cryptotradingbot`.`crypto_symbols_data` SET `is_Active` = False WHERE `symbol_name`='{}';" \
                .format(cur_symbol)
            is_del_qry = db_util.queryExecution(connection, del_qry, 'insert')
        connection.close()
    finally:
        gc.collect()


if __name__ == '__main__':
    while True:
        dt_today = datetime.today()  # Local time
        dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
        start_date = str(datetime.strftime(dt_India, "%d%m%Y"))
        log_filename = "DB_CS_Data_{}.log".format(start_date)
        try:
            print('CS tool started... - ')
            current_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../')
            batch_folder = current_dir + 'batches/data/'
            cs_batch_check = batch_folder + '/cs_batch_check.log'
            limit = sys.argv[1]
            offset = sys.argv[2]
            start_cs_tool()
        except Exception as ex:
            error_log = str(ex).replace('\'', '\'\'') + " - main :: line ::" \
                        + str(sys.exc_info()[2].tb_lineno)
            print('Error: - Main error - {}'.format(error_log))
            print('Time sleep for : 1 min......')
            time.sleep(60)
            continue
