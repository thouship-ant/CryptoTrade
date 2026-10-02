import os
import logging
from datetime import datetime
from pytz import timezone


class logger:
    """
    write logging in logger file and also print in console
    """
    @staticmethod
    def writeLogs(msg, type_value, logFileName):
        """
        responsibility : This function write the Log file with msg and type of logs
        :param msg : string of message logs
        :param type_value : string of log type (Info or Error)
        :return : no return value
        """
        current_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..')
        # Override with the LOG_PATH env var (see batches/_env.sh); defaults to <project>/log_path/
        log_file = os.path.join(os.environ.get('LOG_PATH') or os.path.join(current_dir, 'log_path'), '')
        if not os.path.exists(os.path.dirname(log_file)):
            os.makedirs(os.path.dirname(log_file))
        log_file = log_file + logFileName
        logging.basicConfig(filename=log_file, level=logging.INFO)
        dt_today = datetime.today()  # Local time
        dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
        msg = str(datetime.strftime(dt_India, "%d-%m-%Y:%H:%M:%S") \
                  + "\t" + msg)
        print(msg)
        if type_value == 'info':
            logging.info(msg)
        else:
            logging.error(msg)
