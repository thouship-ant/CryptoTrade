import mysql.connector
# import pyodbc


@staticmethod
def queryExecution(cnxn, query, type):
    try:
        cursor = cnxn.cursor()
        if type == 'select':
            cursor.execute(query)
            data = cursor.fetchall()
            return data
        elif type == 'update' or type == 'insert':
            cursor.execute(query)
            cnxn.commit()
            return True
    except Exception as ex:
        print("DB Query error ::: {} - {}".format(ex, query))
        if type == 'select':
            return []
        else:
            return False


@staticmethod
def connect_database():
    try:
        # cnxn = pyodbc.connect("DRIVER={SQL Server};SERVER=localhost\SQLEXPRESS;DATABASE=ant_cryptotradingbot;") ANT_Web_Admin
        cnxn = mysql.connector.connect(host='187.127.154.130', database='ant_cryptotradingbot_v2', user='ahyan', password='Ahyan@1811')
        # cursor = cnxn.cursor()
        # print("Database Connection Established..!")
        return cnxn
    except Exception as e:
        print("Database Connection Failed..!")
        print(e)
        return 0
