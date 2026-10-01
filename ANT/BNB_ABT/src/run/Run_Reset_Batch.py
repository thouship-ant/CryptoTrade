import time
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from src.utils import db_util


if __name__ == '__main__':
    while True:
        try:
            connection = db_util.connect_database()
            if connection.is_connected():
                query = """UPDATE `ant_cryptotradingbot`.`ant_user_data` SET `is_tool_running`=False 
                WHERE `is_Active` = True and `validity_status`='valid' and username='thouship'"""
                is_update = db_util.queryExecution(connection, query, 'update')
                if is_update:
                    print('Batch running status reset successfully!!!!')
                    sys.exit()
        except Exception as ex:
            error_log = str(ex).replace('\'', '\'\'') + " - main :: line ::" \
                        + str(sys.exc_info()[2].tb_lineno)
            print('Error: - Main error - {}'.format(error_log))
            print('Time sleep for : 1 min......')
            time.sleep(60)
            continue
