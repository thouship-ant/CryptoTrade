import threading
import time, sys, os
from datetime import datetime
from pytz import timezone
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from src.utils.logger import logger
from src.utils.runner import run_script



if __name__ == '__main__':
    is_next_day = True
    dt_today = datetime.today()  # Local time
    dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
    start_date = str(datetime.strftime(dt_India, "%d%m%Y"))
    while True:
        if is_next_day:
            log_filename = "Run_TA_DATA_{}.log".format(start_date)
            try:
                nthread_count = 3
                for r in range(nthread_count):
                    x = threading.Thread(target=run_script, args=('src/data/DB_TA_Data.py',))
                    x.start()
                    logger.writeLogs('Time sleep for : 5 minutes......', 'info', log_filename)
                    time.sleep(300)
                is_next_day = False
            except Exception as ex:
                error_log = str(ex).replace('\'', '\'\'') + " - main :: line ::" \
                            + str(sys.exc_info()[2].tb_lineno)
                logger.writeLogs('Error: - Main error - {}'.format(error_log), 'error', log_filename)
                logger.writeLogs('Time sleep for : 1 min......', 'error', log_filename)
                time.sleep(60)
                continue
        else:
            dt_today = datetime.today()  # Local time
            dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
            check_date = str(datetime.strftime(dt_India, "%d%m%Y"))
            if start_date != check_date:
                is_next_day = True
                start_date = check_date
            print('Time sleep for : 15 minute......')
            time.sleep(900)
