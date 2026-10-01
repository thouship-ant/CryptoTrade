import pandas as pd
import numpy as np
import sys, os
import plotly.graph_objects as go
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from src.utils import db_util
import warnings
warnings.filterwarnings('ignore')


def get_data(symbol):
    try:
        connection = db_util.connect_database()
        if connection.is_connected():
            query_data = "SELECT DateTime as 'Date',Open,High,Low,Close from `ant_cryptotradingbot`.`{}` limit 96 offset 384;" \
                .format(symbol)
            df = pd.read_sql(query_data, connection)
            # pattern_list = db_util.queryExecution(connection, query_data, 'select')
            # if len(pattern_list) > 0:
            #     for line in pattern_list:
            #         # appendLine in correct format for candlesticks - date,open,close,high,low
            #         appendLine = date2num(line[0]), line[1], line[2], line[3], line[4]
            #         candleAr.append(appendLine)
            return df
    except Exception as e:
        error_log = str(e).replace('\'', '\'\'') + " - main :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print(error_log)


def support(df, i):
    support = df['Low'][i] < df['Low'][i-1] and df['Low'][i] < df['Low'][i+1] and df['Low'][i + 1] < df['Low'][i + 2] \
              and df['Low'][i-1] < df['Low'][i-2]
    return support


def  resistance(df, i):
    resistance = df['High'][i] > df['High'][i-1] and df['High'][i] > df['High'][i+1] and df['High'][i + 1] > df['High'][i + 2] \
              and df['High'][i-1] > df['High'][i-2]
    return  resistance


# def plot_levels(candleAr, ss, rr):
#     fig, ax = plt.subplots()
#     candlestick_ohlc(ax, candleAr, width=0.6, colorup='g', colordown='r', alpha=0.8)
#     date_format = mpl_dates.DateFormatter('%d %b %Y')
#     ax.xaxis.set_major_formatter(date_format)
#     fig.autofmt_xdate()
#     fig.tight_layout()
#
#     for s in ss:
#         plt.hlines(s[1], xmin=df['Date'][s[0]], xmax=max(df['Date']), colors='green')
#
#     for r in rr:
#         plt.hlines(r[1], xmin=df['Date'][r[0]], xmax=max(df['Date']), colors='red')
#
#     fig.show()


# def plot_levels(df, ss, rr):
#     s = 0
#     e = df.shape[0]
#     dfpl = df[s:e]
#
#     fig = go.Figure(data=[go.Candlestick(x=dfpl.index,
#                                          open=dfpl['Open'],
#                                          high=dfpl['High'],
#                                          low=dfpl['Low'],
#                                          close=dfpl['Close'])])
#
#     c = 0
#     while True:
#         if c > len(ss) - 1:
#             break
#         fig.add_shape(type='line', x0=ss[c][0], y0=ss[c][1],
#                       x1=e,
#                       y1=ss[c][1],
#                       line=dict(color="green", width=3)
#                       )
#         c += 1
#
#     c = 0
#     while True:
#         if c > len(rr) - 1:
#             break
#         fig.add_shape(type='line', x0=rr[c][0], y0=rr[c][1],
#                       x1=e,
#                       y1=rr[c][1],
#                       line=dict(color="red", width=1)
#                       )
#         c += 1
#
#     fig.show()


def distance_from_level(df, x, sr):
    mean = np.mean(df['High'] - df['Low'])
    return np.sum([abs(x - y) < mean for y in sr]) == 0


def main(symbol):
    df = get_data(symbol)
    ss = []
    rr = []
    for row in range(2, df.shape[0] - 2):
        if support(df, row):
            x = df['Low'][row]
            if distance_from_level(df, x, ss):
                ss.append((row, x))
        if resistance(df, row):
            x = df['High'][row]
            if distance_from_level(df, x, rr):
                rr.append((row, x))

    # plot_levels(df, ss, rr)
    return ss, rr


if __name__ == "__main__":
    main('TRXUSDT')
