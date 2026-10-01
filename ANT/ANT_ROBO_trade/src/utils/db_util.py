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
        # cnxn = pyodbc.connect("DRIVER={SQL Server};SERVER=localhost\SQLEXPRESS;DATABASE=ant_cryptotradingbot;")
        cnxn = mysql.connector.connect(host='127.0.0.1', database='ant_cryptotradingbot', user='ahsanahamad', password='Ahsan@1912')
        # cursor = cnxn.cursor()
        # print("Database Connection Established..!")
        return cnxn
    except Exception as e:
        print("Database Connection Failed..!")
        print(e)
        return 0
