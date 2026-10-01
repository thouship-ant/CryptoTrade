import threading
import subprocess
from utils import db_util
from utils.logger import logger
import time, sys, os
from datetime import datetime, timedelta
from pytz import timezone


def run_batch(batch_file_name):
    subprocess.call([r'{}'.format(batch_file_name)])


if __name__ == '__main__':
    while True:
        dt_today = datetime.today()  # Local time
        dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
        start_date = str(datetime.strftime(dt_India, "%d%m%Y"))
        log_filename = "Run_Batch_{}.log".format(start_date)
        try:
            dt_yesterday = datetime.today() - timedelta(days=1)
            dt_India_yesterday = dt_yesterday.astimezone(timezone('Asia/Kolkata'))
            yesterday_date = str(dt_India_yesterday.strftime('%Y-%m-%d'))
            current_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../')
            batch_folder = current_dir + 'batches/users/'
            if not os.path.exists(batch_folder):
                os.makedirs(batch_folder)
            connection = db_util.connect_database()
            if connection.is_connected():
                query = """SELECT `username`, `validity`, `is_Active` FROM `ant_cryptotradingbot`.`ant_user_data` 
                WHERE `is_Active` = True and `validity_status`='valid'"""
                users_list = db_util.queryExecution(connection, query, 'select')
                if len(users_list) > 0:
                    for user_list in users_list:
                        query = """SELECT `username`, `role`, `exchange_name`, `api_key`, `api_secret`, `max_invest`, 
                        `validity_status`, `is_tool_running` FROM `ant_cryptotradingbot`.`ant_user_data`  
                        WHERE `api_key` is not null and `validity` > '{}' and `is_tool_running` = False and `is_Active` = True and `username` = '{}'"""\
                            .format(yesterday_date, user_list[0])
                        valid_users_list = db_util.queryExecution(connection, query, 'select')
                        if len(valid_users_list) > 0:
                            batch_file_name = batch_folder + 'Run_DB_Trading_BOT_{}.bat'.format(user_list[0])
                            batch_text = "python.exe ..\src\DB_Trading_BOT_BUSD.py {} {} {}"\
                                .format(user_list[0], valid_users_list[0][3], valid_users_list[0][4])
                            with open(batch_file_name, 'w') as bat:
                                bat.write(batch_text)
                                bat.close()
                            update_query = """UPDATE `ant_cryptotradingbot`.`ant_user_data` SET `is_tool_running`=True  
                                    WHERE `api_key` is not null and `validity` > '{}' and `is_tool_running` = False 
                                    and `is_Active` = True and `username` = '{}'"""\
                                .format(yesterday_date, user_list[0])
                            db_update = db_util.queryExecution(connection, update_query, 'update')
                            logger.writeLogs('{} - tool running status changed ::: True , DB Update ::: {}'
                                             .format(user_list[0], db_update), 'info', log_filename)
                            x = threading.Thread(target=run_batch, args=(batch_file_name,))
                            x.start()
                            time.sleep(5)
                        else:
                            batch_file_name = batch_folder + 'Run_DB_Trading_BOT_{}.bat'.format(user_list[0])
                            if not os.path.exists(batch_file_name):
                                os.makedirs(batch_file_name)
                            update_query = """UPDATE `ant_cryptotradingbot`.`ant_user_data` SET `is_tool_running`=False, `validity_status`='Expired'  
                                    WHERE `api_key` is not null and `validity` <= '{}' and `is_Active` = True and `username` = '{}'""" \
                                .format(yesterday_date, user_list[0])
                            db_update = db_util.queryExecution(connection, update_query, 'update')
                            query = """SELECT `username`, `role`, `exchange_name`, `api_key`, `api_secret`, `max_invest`, 
                            `validity_status`, `is_tool_running` FROM `ant_cryptotradingbot`.`ant_user_data`  
                            WHERE `is_tool_running`=False and `validity_status`='Expired' and `is_Active` = True and `username` = '{}'""" \
                                .format(user_list[0])
                            checking = db_util.queryExecution(connection, query, 'select')
                            if len(checking) > 0:
                                logger.writeLogs('{} - tool running status changed ::: False and validity_status ::: Expired, DB Update ::: {}'
                                      .format(user_list[0], db_update), 'info', log_filename)
                    logger.writeLogs('Time sleep for : 1 hour......', 'info', log_filename)
                    time.sleep(3600)
        except Exception as ex:
            error_log = str(ex).replace('\'', '\'\'') + " - main :: line ::" \
                        + str(sys.exc_info()[2].tb_lineno)
            logger.writeLogs('Error: - Main error - {}'.format(error_log), 'error', log_filename)
            logger.writeLogs('Time sleep for : 1 min......', 'error', log_filename)
            time.sleep(60)
            continue
