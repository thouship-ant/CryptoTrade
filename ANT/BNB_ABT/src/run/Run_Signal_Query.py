import time, sys, os
from datetime import datetime
from pytz import timezone
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from src.utils.logger import logger
from src.utils.runner import run_script



if __name__ == '__main__':
    dt_today = datetime.today()  # Local time
    dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
    start_date = str(datetime.strftime(dt_India, "%d%m%Y"))
    log_filename = "Run_Signal_Query_{}.log".format(start_date)
    while True:
        try:
            logger.writeLogs('Batch Running......', 'info', log_filename)
            run_script('src/data/DB_Signal_Query.py')
            logger.writeLogs('Batch Stopped......', 'info', log_filename)
            logger.writeLogs('Time sleep for : 1 seconds......', 'info', log_filename)
            time.sleep(1)
        except Exception as ex:
            error_log = str(ex).replace('\'', '\'\'') + " - main :: line ::" \
                        + str(sys.exc_info()[2].tb_lineno)
            logger.writeLogs('Error: - Main error - {}'.format(error_log), 'error', log_filename)
            logger.writeLogs('Time sleep for : 1 min......', 'error', log_filename)
            time.sleep(60)
            continue
