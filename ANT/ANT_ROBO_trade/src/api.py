import time
from datetime import datetime, timedelta
import pandas as pd
import ccxt, re, sys
from pytz import timezone
from flask import Flask, jsonify, escape, session, request, render_template, send_from_directory, redirect, url_for
from src import app, cache
from binance.client import Client
from src.utils import config
from src.utils import db_util
from src.utils import chart_data
import warnings
from src.utils.utility import remove_tail_dot_zeros

warnings.filterwarnings('ignore')

@app.route('/display_mode', methods=['POST'])
@cache.cached(timeout=30)
def get_display_mode():
    temp_display_mode = session['display_mode']
    if temp_display_mode == 'dark-mode':
        session['display_mode'] = 'light-mode'
    else:
        session['display_mode'] = 'dark-mode'
    connection = db_util.connect_database()
    if connection.is_connected():
        update_query = """UPDATE `ant_cryptotradingbot`.`ant_user_data` SET `display_mode`='{}' where `username` = '{}'""" \
            .format(session['display_mode'], session["username"].lower())
        update_query_result = db_util.queryExecution(connection, update_query, 'update')
        if update_query_result:
            return jsonify(session['display_mode'])
        connection.close()
    session['display_mode'] = temp_display_mode
    return jsonify(session['display_mode'])


@app.route('/energy_power', methods=['GET'])
@cache.cached(timeout=30)
def get_energy_power():
    temp_display_mode = session['energy_power']
    connection = db_util.connect_database()
    if connection.is_connected():
        sel_query = """SELECT `energy_power` from `ant_cryptotradingbot`.`ant_user_data` where `username` = '{}'""" \
            .format(session["username"].lower())
        sel_query_result = db_util.queryExecution(connection, sel_query, 'select')
        if len(sel_query_result) > 0:
            session['energy_power'] = sel_query_result[0][0]
            return jsonify(True)
        connection.close()
    session['energy_power'] = temp_display_mode
    return jsonify(False)


@app.route('/user_list', methods=['GET'])
@cache.cached(timeout=30)
def get_user_list():
    if 'username' in session:
        if session['role'] != 'Admin':
            return jsonify([])
        lst_user_list = []
        connection = db_util.connect_database()
        if connection.is_connected():
            query = "select `user_id`, `username`, `full_name`, `role`, `validity`, `validity_status`, `is_tool_running`, `current_plan`, `is_Active` FROM `ant_cryptotradingbot`.`ant_user_data`;"
            query_data = db_util.queryExecution(connection, query, 'select')
            if len(query_data) > 0:
                for cpd in query_data:
                    val_date = ''
                    if cpd[4] is not None:
                        val_date = str(cpd[4].strftime('%d %b, %Y'))
                    status = 'Active'
                    if cpd[8] == 0:
                        status = 'In Active'
                    user_list = {"user_id": cpd[0],
                                 "username": cpd[1],
                                 "full_name": cpd[2],
                                 "role": cpd[3],
                                 "validity": val_date,
                                 "validity_status": cpd[5],
                                 "is_tool_running": cpd[6],
                                 "current_plan": cpd[7],
                                 "status": status
                                 }
                    lst_user_list.append(user_list)
                return jsonify(lst_user_list)
        return jsonify([])


@app.route('/dashboard_data', methods=['GET'])
@cache.cached(timeout=30)
def get_dashboard_data():
    if 'username' in session:
        username = session['username']
        data = {
            "total_invested": 0.00,
            "initial_invested": 0.00,
            "total_diffs": 0.00,
            "total_changes": 0.00,
            "total_changes_percent": 0.00,
            "month_changes": 0.00,
            "month_changes_percent": 0.00,
            "today_diffs": 0.00,
            "today_changes": 0.00,
            "today_changes_percent": 0.00
        }
        dt_today = datetime.today()  # Local time
        dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
        monthyear = str(dt_India.strftime('%Y-%m'))
        today_date = str(dt_India.strftime('%Y-%m-%d'))
        connection = db_util.connect_database()
        if connection.is_connected():
            query = """(select distinct auw.`initial_investment_future` as invest_amount, (auw.`binance_exchange_usdt`+ifnull((SELECT (sum(ifnull(cbor.`buy_price`,0)*cbor.`order_quantity`)  + sum(ifnull(cbor.`sell_price`,0) * cbor.`order_quantity`))/20 from `ant_cryptotradingbot`.`current_buy_order_report_future` as cbor inner join `ant_cryptotradingbot`.`order_report_future` as ort on ort.username=cbor.username and ort.symbol_name=cbor.symbol_name and (ort.`buy_price`=cbor.`buy_price` or ort.`sell_price`=cbor.`sell_price`) and ort.`order_quantity`=cbor.`order_quantity` and ort.`signal_type`=cbor.`signal_type` and ort.`order_date`=cbor.`order_date` where cbor.username = '{}'), 0)) as final_amount from `ant_cryptotradingbot`.`ant_user_wallet` as auw where auw.username = '{}')
                    union all
                    (select sum(profit_amount - commission_price) as invest_amount, sum(profit_percent) as final_amount from `ant_cryptotradingbot`.`daily_profit_report_future` where username = '{}')
                    union all
                    (select sum(profit_amount - commission_price) as invest_amount, sum(profit_percent) as final_amount from `ant_cryptotradingbot`.`daily_profit_report_future` where username = '{}' and `date` >= '{}-01')
                    union all
                    (select sum(profit_amount - commission_price) as invest_amount, sum(profit_percent) as final_amount from `ant_cryptotradingbot`.`daily_profit_report_future` where username = '{}' and `date` = '{}')""" \
                .format(username, username, username, username, monthyear, username, today_date)
            query_data = db_util.queryExecution(connection, query, 'select')
            if len(query_data) > 2:
                if query_data[0][0] is not None:
                    data["initial_invested"] = round(float(query_data[0][0]), 2)
                    data["total_invested"] = round(float(query_data[0][1]), 2)
                if query_data[1][0] is not None:
                    data["total_changes"] = round(float(query_data[1][0]), 2)
                    if data["total_changes"] < 0:
                        data["total_changes"] = -1 * data["total_changes"]
                    data["total_changes_percent"] = round(float(query_data[1][1]), 2)
                    data["total_diffs"] = round(float(query_data[0][1]) - float(query_data[0][0]) - float(query_data[1][0]), 2)
                    if int(data["total_diffs"]) == 0:
                        data["total_diffs"] = 0.00
                if query_data[2][0] is not None:
                    data["month_changes"] = round(float(query_data[2][0]), 2)
                    if data["month_changes"] < 0:
                        data["month_changes"] = -1 * data["month_changes"]
                    data["month_changes_percent"] = round(float(query_data[2][1]), 2)
                if len(query_data) > 3:
                    if query_data[3][0] is not None:
                        data["today_changes"] = round(float(query_data[3][0]), 2)
                        if data["today_changes"] < 0:
                            data["today_changes"] = -1 * data["today_changes"]
                        data["today_changes_percent"] = round(float(query_data[3][1]), 2)
                        # data["today_diffs"] = round(float(query_data[0][1]) - float(query_data[3][0]) - float(data["today_changes_percent"]), 2)
                return jsonify(data)
    return jsonify([])


@app.route('/current_position', methods=['GET'])
@cache.cached(timeout=30)
def get_current_position():
    if 'username' in session:
        username = session['username']
        exchange = ccxt.binance()
        lst_current_position_data = []
        current_position_data = {
            "symbolname": '',
            "symbol_pair": '',
            "signal_side": 'BUY',
            "current_price": '-',
            "current_percent": 0,
            "order_quantity": '-',
            "open_price": '-',
            "open_amount": '-',
            "close_price": '-',
            "final_amount": '-',
            "target_price": '-',
            "stoploss_price": '-',
            "position": 'No'#,
            # "chart_data": [],
            # "chart_ann_data": "",
        }
        connection = db_util.connect_database()
        if connection.is_connected():
            query = """SELECT DISTINCT orp.symbol_name, csd.current_askPrice, cbor.profit_percent as current_percent, orp.order_quantity, 
            orp.buy_price, orp.buy_amount, ifnull(orp.sell_price, 0) as sell_price, ifnull(orp.sell_amount, 0) as sell_amount, 
            ifnull(cbor.target_price, 0) as target_price, ifnull(cbor.stoploss_price, 0) as stoploss_price, orp.order_date, cbor.order_seq_id, cbor.signal_type
            from `ant_cryptotradingbot`.`current_buy_order_report_future` as cbor 
            inner join `ant_cryptotradingbot`.`crypto_symbols_data` as csd on cbor.symbol_name = csd.symbol_name
            inner join `ant_cryptotradingbot`.`order_report_future` as orp on cbor.symbol_name = orp.symbol_name and cbor.username = orp.username and orp.profit_amount is null
            where cbor.username = '{}'
            order by cbor.order_seq_id asc;""" \
                .format(username)
            query_data = db_util.queryExecution(connection, query, 'select')

            if len(query_data) > 0:
                for cpd in query_data:
                    signal_side = cpd[12].split('-')[1].strip()

                    current_position_data = {"symbolname": cpd[0].replace("USDT", ""),
                                             "symbol_pair": cpd[0],
                                             "signal_side": signal_side}
                    if cpd[1] is not None:
                        current_position_data["current_price"] = remove_tail_dot_zeros(str(cpd[1]))
                    else:
                        symbol_info = exchange.fetch_ticker(cpd[0])['info']
                        cur_ask_price = round(float(symbol_info['askPrice']), 8)
                        current_position_data["current_price"] = remove_tail_dot_zeros(str(cur_ask_price))

                    if cpd[2] is not None:
                        current_position_data["current_percent"] = cpd[2]
                    else:
                        current_position_data["current_percent"] = round(((float(current_position_data["current_price"]) - float(cpd[4])) / (float(cpd[4]) / 100)) * 20, 2)
                        if signal_side == 'SELL':
                            current_position_data["current_percent"] = round(((float(cpd[6]) - float(current_position_data["current_price"])) / (float(cpd[6]) / 100)) * 20, 2)

                    current_position_data["position"] = 'Open'
                    current_position_data["order_quantity"] = remove_tail_dot_zeros(str(cpd[3]))
                    current_position_data["open_price"] = remove_tail_dot_zeros(str(cpd[4]))
                    current_position_data["open_amount"] = str(round(float(cpd[5])/20, 2))
                    current_position_data["target_price"] = remove_tail_dot_zeros(str(cpd[6]))
                    if signal_side == 'SELL':
                        current_position_data["open_price"] = remove_tail_dot_zeros(str(cpd[6]))
                        current_position_data["open_amount"] = str(round(float(cpd[7])/20, 2))
                        current_position_data["target_price"] = remove_tail_dot_zeros(str(cpd[4]))
                    
                    current_position_data["final_amount"] = remove_tail_dot_zeros(str(round(float(cpd[3])*float(current_position_data["current_price"]),2)))
                    #if cpd[6] > 0:
                    #    current_position_data["close_price"] = remove_tail_dot_zeros(str(cpd[6]))
                    #    current_position_data["position"] = 'Closed'
                    if cpd[9] > 0:
                        current_position_data["stoploss_price"] = remove_tail_dot_zeros(str(cpd[9]))
                    #if cpd[7] > 0:
                    #    current_position_data["final_amount"] = remove_tail_dot_zeros(str(cpd[7]))
                    #else:
                    #    current_position_data["final_amount"] = remove_tail_dot_zeros(str(cpd[3]*cpd[1]))
                    # order_date = str(cpd[10].strftime('%Y-%m-%d %H:%M'))
                    # last_mins = int(order_date[-2:])
                    # i_last_mins = int(last_mins / 15)
                    # dif_last_mins = round(float(last_mins / 15), 2) - i_last_mins
                    # if 0.5 <= dif_last_mins < 0.99:
                    #     order_date = order_date[:-2] + str((i_last_mins-1)*15)
                    # else:
                    #     order_date = order_date[:-2] + str(i_last_mins*15)
                    # order_date += ':00'
                    # print(order_date)
                    # chartdata, volume_data = chart_data.get_chart_data(cpd[0], '15m')
                    # current_position_data["chart_data"] = list(chartdata)
                    # current_position_data["chart_ann_data"] = "{xaxis:[{x: '" + order_date + "',borderColor:MarketchartColors[0],label:{borderColor:MarketchartColors[0],style:{fontSize:'12px',color:'#fff',background:MarketchartColors[0]},orientation:'vertical',offsetY:7,text:'B'}}]}"
                    lst_current_position_data.append(current_position_data)
                return jsonify(lst_current_position_data)
        connection.close()
        return jsonify([])


@app.route('/daily_profit_report', methods=['GET'])
@cache.cached(timeout=30)
def get_daily_profit_report():
    if 'username' in session:
        username = session['username']
        dpr_data = {
            "min_date": '',
            "month_start_date": '',
            "month_end_date": '',
            "six_month_start_date": '',
            "six_month_end_date": '',
            "year_start_date": '',
            "year_end_date": '',
            "all_start_date": '',
            "all_end_date": '',
            "chart_data": []
        }
        connection = db_util.connect_database()
        if connection.is_connected():
            query = """select dpr.`date`, uw.`initial_investment_future`, dpr.`profit_amount` as amount from `ant_cryptotradingbot`.`daily_profit_report_future` as dpr
            inner join `ant_cryptotradingbot`.`ant_user_wallet` as uw on dpr.`username`=uw.`username` where dpr.`username` = '{}' order by dpr.`date` asc;""" \
                .format(username)
            query_data = db_util.queryExecution(connection, query, 'select')
            lst_chart_datas = []
            if len(query_data) > 0:
                initial_investment = round(float(query_data[0][1]), 2)
                cum_investment = initial_investment
                dpr_data["min_date"] = str(query_data[0][0].strftime('%d %b %Y'))
                last_date = query_data[-1][0]
                month_start_date = query_data[-1][0] - timedelta(days=30)
                if month_start_date < query_data[0][0]:
                    month_start_date = query_data[0][0]
                six_month_start_date= query_data[-1][0] - timedelta(days=30*6)
                if six_month_start_date < query_data[0][0]:
                    six_month_start_date = query_data[0][0]
                year_start_date= query_data[-1][0] - timedelta(days=365)
                if year_start_date < query_data[0][0]:
                    year_start_date = query_data[0][0]
                dpr_data["month_start_date"]=str(month_start_date.strftime('%d %b %Y'))
                dpr_data["month_end_date"]= str(last_date.strftime('%d %b %Y'))
                dpr_data["six_month_start_date"]=str(six_month_start_date.strftime('%d %b %Y'))
                dpr_data["six_month_end_date"]= str(last_date.strftime('%d %b %Y'))
                dpr_data["year_start_date"]= str(year_start_date.strftime('%d %b %Y'))
                dpr_data["year_end_date"] = str(last_date.strftime('%d %b %Y'))
                dpr_data["all_start_date"]= dpr_data["min_date"]
                dpr_data["all_end_date"]= str(last_date.strftime('%d %b %Y'))

                if len(query_data) > 0:
                    prev_date = query_data[0][0]
                    lst_chart_data_val = [str(prev_date.strftime('%d %b %Y')), round(cum_investment, 2)]
                    lst_chart_datas.append(lst_chart_data_val)

                for dpr in query_data:
                    cum_investment += float(dpr[2])
                    next_date = dpr[0] + timedelta(days=1)
                    lst_chart_data_val = [str(next_date.strftime('%d %b %Y')), round(cum_investment, 2)]
                    lst_chart_datas.append(lst_chart_data_val)
                dpr_data["chart_data"] = lst_chart_datas
                return jsonify(dpr_data)
    return jsonify([])


@app.route('/market_status', methods=['GET'])
@cache.cached(timeout=30)
def get_market_status():
    if 'username' in session:
        lst_market_status_data = []
        market_status_data = {
            "symbol": '',
            "symbolname": '',
            "symbol_pair": '',
            "current_price": 0,
            "current_change": 0,
            "current_percent": 0,
            "volume": 0
        }
        connection = db_util.connect_database()
        if connection.is_connected():
            coins_query = """SELECT csn.symbol_name as symbol, replace(csn.symbol_full_name, '_', '') as symbol_full_name, csd.`current_askPrice`, csd.`24hrs_price_change`, csd.`24hrs_change`, csd.`Volumes` from `ant_cryptotradingbot`.`crypto_symbols_data` as csd
                inner join `ant_cryptotradingbot`.`crypto_symbols_name` as csn on csn.symbol_name = replace(csd.symbol_name, 'USDT', '')
                where csd.is_Active = true order by csd.`24hrs_change` desc limit 10;"""
            query_data = db_util.queryExecution(connection, coins_query, 'select')
            if len(query_data) > 0:
                for cpd in query_data:
                    market_status_data = {"symbol": cpd[0].replace("USDT", ""),
                                          "symbolname": cpd[1].replace("USDT", ""),
                                          "symbol_pair": cpd[0] + "USDT",
                                          "current_price": remove_tail_dot_zeros(str(cpd[2])),
                                          "current_change": remove_tail_dot_zeros(str(cpd[3])),
                                          "current_percent": cpd[4],
                                          "volume": cpd[5]
                                          }
                    lst_market_status_data.append(market_status_data)
                return jsonify(lst_market_status_data)
    return jsonify([])


@app.route('/chart_data', methods=['GET'])
@cache.cached(timeout=30)
def get_chart_data():
    if 'username' in session:
        symbol = request.args.get('symbol', '')
        chartdata, volume_data = chart_data.get_chart_data(symbol, '15m')
        return jsonify(list(chartdata))
    return jsonify([])


@app.route('/sparkline_charts', methods=['GET'])
@cache.cached(timeout=30)
def get_sparkline_charts():
    if 'username' in session:
        symbol = request.args.get('symbol', '')
        sparkline_charts = []
        connection = db_util.connect_database()
        if connection.is_connected():
            coins_query = """SELECT Close from `ant_cryptotradingbot`.`{}` limit 96 offset 384;""".format(symbol+'usdt')
            query_data = db_util.queryExecution(connection, coins_query, 'select')
            if len(query_data) > 0:
                for cpd in query_data:
                    sparkline_charts.append(float(remove_tail_dot_zeros(str(cpd[0]))))
            return jsonify(sparkline_charts)
    return jsonify([])


@app.route('/recent_profit', methods=['GET'])
@cache.cached(timeout=30)
def get_recent_profit():
    if 'username' in session:
        username = session['username']
        lst_recent_profit = []
        recent_profit_data = {
            "symbol": '',
            "symbolname": '',
            "profit_amount": 0,
            "date": '',
        }
        dt_today = datetime.today()  # Local time
        dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
        today_date = str(dt_India.strftime('%d %b %Y'))
        dt_yesterday = datetime.today() - timedelta(days=1)  # Local time
        dt_India_yesterday = dt_yesterday.astimezone(timezone('Asia/Kolkata'))
        yesterday_date = str(dt_India_yesterday.strftime('%d %b %Y'))
        connection = db_util.connect_database()
        if connection.is_connected():
            coins_query = """SELECT csn.symbol_name as symbol, replace(csn.symbol_full_name, '_', '') as symbol_full_name, csd.`profit_amount`, cast(csd.`update_date` as Date) as `Date` from `ant_cryptotradingbot`.`order_report_future` as csd
                inner join `ant_cryptotradingbot`.`crypto_symbols_name` as csn on csn.symbol_name = replace(csd.symbol_name, 'USDT', '')
                where csd.`username` = '{}' and csd.`profit_amount` is not null order by csd.`update_date` desc limit 8;"""\
                .format(username)
            query_data = db_util.queryExecution(connection, coins_query, 'select')
            if len(query_data) > 0:
                for cpd in query_data:
                    date = str(cpd[3].strftime('%d %b %Y'))
                    if today_date == date:
                        date = "Today"
                    elif yesterday_date == date:
                        date = "Yesterday"
                    recent_profit_data = {"symbol": cpd[0].replace("USDT", ""),
                                          "symbolname": cpd[1].replace("USDT", ""),
                                          "profit_amount": round(float(cpd[2]), 2),
                                          "date": date
                                          }
                    lst_recent_profit.append(recent_profit_data)
            return jsonify(lst_recent_profit)
    return jsonify([])


@app.route('/coinwise_profit', methods=['GET'])
@cache.cached(timeout=30)
def get_coinwise_profit():
    if 'username' in session:
        username = session['username']
        type = request.args.get('type', 'today')
        lst_coinwise_profit = []
        coinwise_profit_data = {
            "symbol": '',
            "symbolname": '',
            "quantity": 0,
            "avg_buy": 0.00,
            "avg_sell": 0.00,
            "profit_amount": 0.00,
            "profit_percent": 0.00,
        }
        dt_today = datetime.today()  # Local time
        dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
        today_date = str(dt_India.strftime('%Y-%m-%d'))
        month_start_date = str(dt_India.strftime('%Y-%m')) + '-01'
        connection = db_util.connect_database()
        if connection.is_connected():
            if type == 'today':
                condition = "csd.`username` = '{}' and csd.update_date > '{}'".format(username, today_date)
            if type == 'thismonth':
                condition = "csd.`username` = '{}' and csd.update_date > '{}' and csd.update_date <= '{}'".format(username, month_start_date, today_date)
            else:
                condition = "csd.`username` = '{}'".format(username)
            coins_query = """SELECT csn.symbol_name as symbol, replace(csn.symbol_full_name, '_', '') as symbol_full_name, csdm.order_quantity, 
            (csdm.buy_amount / csdm.order_quantity) as avg_buy_price, (csdm.sell_amount / csdm.order_quantity) as avg_sell_price,
            (csdm.sell_amount - csdm.buy_amount) as profit_amount, ((csdm.sell_amount - csdm.buy_amount) / (csdm.buy_amount / 100)) as profit_percent from
            (SELECT csd.symbol_name as symbol_name, sum(csd.`order_quantity`) as order_quantity, sum(csd.`buy_amount`) as buy_amount, sum(csd.`sell_amount`) as sell_amount from `ant_cryptotradingbot`.`order_report_future` as csd
            where {} and csd.`sell_amount` is not null group by symbol_name) as csdm
            inner join `ant_cryptotradingbot`.`crypto_symbols_name` as csn on csn.symbol_name = replace(csdm.symbol_name, 'USDT', '')
            where csdm.sell_amount is not null order by csdm.symbol_name asc;"""\
                .format(condition)
            query_data = db_util.queryExecution(connection, coins_query, 'select')
            if len(query_data) > 0:
                for cpd in query_data:
                    coinwise_profit_data = {"symbol": cpd[0].replace("USDT", ""),
                                            "symbolname": cpd[1].replace("USDT", ""),
                                            "quantity": round(float(cpd[2]), 2),
                                            "avg_buy": float(remove_tail_dot_zeros(str(cpd[3]))),
                                            "avg_sell": float(remove_tail_dot_zeros(str(cpd[4]))),
                                            "profit_amount": round(float(cpd[5]), 2),
                                            "profit_percent": round(float(cpd[6]), 2)
                                            }
                    lst_coinwise_profit.append(coinwise_profit_data)
            return jsonify(lst_coinwise_profit)
    return jsonify([])


@app.route('/ant_coin_data', methods=['GET'])
@cache.cached(timeout=30)
def get_ant_coin_data():
    if 'username' in session:
        lst_ant_coin_data = []
        ant_coin_data = {
            "symbol": '',
            "symbolname": '',
            "current_askPrice": 0.00,
            "price_change": 0.00,
            "changes": 0.00,
            "Volumes": 0
        }
        connection = db_util.connect_database()
        if connection.is_connected():
            coins_query = """SELECT csn.symbol_name as symbol, replace(csn.symbol_full_name, '_', '') as symbolname, csd.`current_askPrice`, csd.`24hrs_price_change` as price_change, csd.`24hrs_change` as changes, csd.`Volumes` from `ant_cryptotradingbot`.`crypto_symbols_data` as csd
            inner join `ant_cryptotradingbot`.`crypto_symbols_name` as csn on csn.symbol_name = replace(csd.symbol_name, 'USDT', '')
            where csd.`Volumes` is not null and csd.is_Active = true order by csn.symbol_name asc;"""
            query_data = db_util.queryExecution(connection, coins_query, 'select')
            if len(query_data) > 0:
                for cpd in query_data:
                    vol_sort = float(cpd[5])
                    if int(cpd[5]) >= 1000000000:
                        vol_sort = round(float(cpd[5]/1000000000), 2)
                    elif int(cpd[5]) >= 1000000:
                        vol_sort = round(float(cpd[5]/1000000), 2)
                    elif int(cpd[5]) >= 1000:
                        vol_sort = round(float(cpd[5]/1000), 2)
                    ant_coin_data = {"symbol": cpd[0].replace("USDT", ""),
                                     "symbolname": cpd[1].replace("USDT", ""),
                                     "current_askPrice": float(remove_tail_dot_zeros(str(cpd[2]))),
                                     "price_change": float(remove_tail_dot_zeros(str(cpd[3]))),
                                     "changes": round(float(cpd[4]), 2),
                                     "Volumes": int(cpd[5]),
                                     "Vol_sort": vol_sort
                                    }
                    lst_ant_coin_data.append(ant_coin_data)
            return jsonify(lst_ant_coin_data)
    return jsonify([])


@app.route('/recent-activity', methods=['GET'])
@cache.cached(timeout=30)
def get_recent_activity():
    if 'username' in session:
        username = session['username']
        type = request.args.get('type', '')
        connection = db_util.connect_database()
        if connection.is_connected():
            dt_yesterday = datetime.today() - timedelta(days=1)  # Local time
            dt_India_yesterday = dt_yesterday.astimezone(timezone('Asia/Kolkata'))
            dt_today = datetime.today()  # Local time
            dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
            year, week_num, day_of_week = dt_India.isocalendar()
            dt_lastWeekStart = dt_India - timedelta(days=((day_of_week-7) - 1))
            dt_lastWeekEnd = dt_India - timedelta(days=((day_of_week) - 2))
            dt_weekStart = dt_India - timedelta(days=(day_of_week - 1))
            if type == 'currentweek':
                start_date = str(dt_weekStart.strftime('%Y-%m-%d'))
                end_date = str(dt_India.strftime('%Y-%m-%d 23:59:59'))
            elif type == 'currentmonth':
                start_date = str(dt_India.strftime('%Y-%m-'))+'01'
                end_date = str(dt_India.strftime('%Y-%m-%d 23:59:59'))
            elif type == 'currentyear':
                start_date = str(dt_India.strftime('%Y'))+'-01-01'
                end_date = str(dt_India.strftime('%Y-%m-%d 23:59:59'))
            elif type == 'yesterday':
                start_date = str(dt_India_yesterday.strftime('%Y-%m-%d'))
                end_date = str(dt_India_yesterday.strftime('%Y-%m-%d 23:59:59'))
            elif type == 'lastweek':
                start_date = str(dt_lastWeekStart.strftime('%Y-%m-%d'))
                end_date = str(dt_lastWeekEnd.strftime('%Y-%m-%d 23:59:59'))
            else:
                start_date = str(dt_India.strftime('%Y-%m-%d'))
                end_date = str(dt_India.strftime('%Y-%m-%d 23:59:59'))
            ra_query = """call `ant_cryptotradingbot`.`user_recent_activity`('{}', '{}', '{}')""" \
                .format(username, start_date, end_date)
            ra_df = pd.read_sql(ra_query, connection)
            # ra_df = ra_df.groupby('date')
            ra_data = ra_df.values.tolist()
            date = ''
            result = []
            ra_result = {}
            lst_ra_result = []
            for ra in ra_data:
                trim_data = [ra[1], ra[2], ra[3], ra[4], ra[5], ra[6]]
                ra_date = str(ra[0])
                if date != ra_date:
                    if date != '':
                        ra_result["date"] = date
                        ra_result["result"] = result
                        lst_ra_result.append(ra_result)
                    ra_result = {}
                    result = []
                    date = ra_date
                result.append(trim_data)

            ra_result["date"] = date
            ra_result["result"] = result
            lst_ra_result.append(ra_result)
            return jsonify(lst_ra_result)
    return jsonify([])


@app.route('/order_report', methods=['GET'])
@cache.cached(timeout=30)
def get_order_report():
    if 'username' in session:
        username = session['username']
        type = request.args.get('type', 'today')
        lst_order_report = []
        order_report = {
            "date": '',
            "date_text": '',
            "symbol": '',
            "symbolname": '',
            "bs_type": '',
            "order_quantity": 0,
            "avg_price": 0,
            "order_value": 0,
            "status": ''
        }
        dt_today = datetime.today()  # Local time
        dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
        if type == 'today':
            start_date = str(dt_India.strftime('%Y-%m-%d'))
            end_date = str(dt_India.strftime('%Y-%m-%d 23:59:59'))
        else:
            start_date = ''
            end_date = ''
        connection = db_util.connect_database()
        if connection.is_connected():
            query = """call `ant_cryptotradingbot`.`order_reports`('{}', '{}', '{}')""" \
                .format(username, start_date, end_date)
            query_data = db_util.queryExecution(connection, query, 'select')
            if len(query_data) > 0:
                for cpd in query_data:
                    order_report = {"date": str(cpd[0].strftime('%Y-%m-%d %H:%M:%S')),
                                    "date_text": str(cpd[0].strftime('%d %b, %Y')),
                                    "time_text": str(cpd[0].strftime('%I:%M%p')),
                                    "symbol": cpd[1].replace("USDT", ""),
                                    "symbolname": cpd[2].replace("USDT", ""),
                                    "bs_type": cpd[3],
                                    "order_quantity": float(remove_tail_dot_zeros(str(cpd[4]))),
                                    "avg_price": float(remove_tail_dot_zeros(str(cpd[5]))),
                                    "order_value": round(float(remove_tail_dot_zeros(str(cpd[6]))), 2),
                                    "status": cpd[7]
                                    }
                    lst_order_report.append(order_report)
                return jsonify(lst_order_report)
        return jsonify([])


@app.route('/check_transaction', methods=['GET'])
@cache.cached(timeout=30)
def get_check_transaction():
    if 'username' in session:
        username = session['username']
        txId = request.args.get('txId', '')
        tx_details = {
            "amount": 0.00,
            "coin": '',
            "address": '',
            "txId": '',
            "from": '',
            "to": '',
            "type": '',
            "details": '',
            "status": '',
            "error": ''
        }
        timeout = 180
        while timeout >= 0:
            dt_today = datetime.today()  # Local time
            dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
            today_date = str(dt_India.strftime('%Y-%m-%d %H:%M:%S'))
            client = Client(config.BINANCE_API_KEY, config.BINANCE_API_SECRET)
            lstDH = client.get_deposit_history()
            for dh in lstDH:
                if dh["coin"] == "BUSD" and dh["txId"] == txId and dh["network"] == "BSC":
                    # confirmTimes = dh["confirmTimes"]
                    # total_times = confirmTimes.split('/')[1]
                    # if dh["confirmTimes"] == str(total_times)+'/'+str(total_times):
                    #     status = 'Successful'
                    # else:
                    #     status = 'Pending'
                    status = 'Successful'
                    connection = db_util.connect_database()
                    if connection.is_connected():
                        coins_query = """SELECT count(s_no) from `ant_cryptotradingbot`.`transaction_history` where `txID` = '{}';""".format(txId)
                        query_data = db_util.queryExecution(connection, coins_query, 'select')
                        if query_data[0][0] == 0:
                            w_ins_query = """INSERT `ant_cryptotradingbot`.`transaction_history` (`symbol_name`, `amount`, `address`, `txID`, `from`, `to`, `type`, `details`, `status`, `username`, `txn_date`) 
                            VALUES ('{}', {}, '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}');""" \
                                .format(dh["coin"], round(float(dh["amount"]), 2), dh["address"], dh["txId"], 'Myself', 'Wallet', 'Deposit', 'Activation Wallet for BOT Purchase', status, username, today_date)
                            wallet_query_result = db_util.queryExecution(connection, w_ins_query, 'insert')
                            if wallet_query_result:
                                w_upd_query = """UPDATE `ant_cryptotradingbot`.`ant_user_wallet` set `activation_balance` = `activation_balance`+{}, `total_deposit` = `total_deposit`+{} WHERE `username` = '{}';""" \
                                    .format(round(float(dh["amount"]), 2), round(float(dh["amount"]), 2), username)
                                wallet_query_result = db_util.queryExecution(connection, w_upd_query, 'insert')
                                tx_details = {
                                    "amount": round(float(dh["amount"]), 2),
                                    "coin": dh["coin"] + "("+dh["network"]+")",
                                    "address": dh["address"],
                                    "txId": dh["txId"],
                                    "from": 'Myself',
                                    "to": 'Wallet',
                                    "type": 'Deposit',
                                    "details": 'Activation Wallet for BOT Purchase',
                                    "status": status,
                                    "error": ''
                                }
                                return jsonify(tx_details)
                            else:
                                tx_details['error'] = 'Something went wrong!!!'
                        else:
                            tx_details['error'] = 'Transaction ID already exist in our record(s)!!!'
                    break
            timeout -= 60
            time.sleep(60)
        if timeout <= 0:
            tx_details['status'] = 'error'
            tx_details['error'] = 'Transaction timeout!!!'
        return jsonify(tx_details)


@app.route('/initiate_withdrawal', methods=['GET'])
@cache.cached(timeout=30)
def get_initiate_withdrawal():
    if 'username' in session:
        username = session['username']
        address = request.args.get('addr', '')
        amount = request.args.get('amt', 0)
        tx_details = {
            "amount": amount,
            "coin": "",
            "type": 'Withdrawal',
            "details": '',
            "status": '',
            "error": ''
        }
        dt_today = datetime.today()  # Local time
        dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
        today_date = str(dt_India.strftime('%Y-%m-%d %H:%M:%S'))
        status = 'Pending'
        connection = db_util.connect_database()
        if connection.is_connected():
            coins_query = """SELECT ant_wallet_balance from `ant_cryptotradingbot`.`ant_user_wallet` where `username` = '{}';""".format(username)
            query_data = db_util.queryExecution(connection, coins_query, 'select')
            if float(query_data[0][0]) >= float(amount) >= 10:
                txId = str(dt_India.strftime('%Y%m%d%H%M%S')) + '_' + username + '_' + str(amount)
                w_ins_query = """INSERT `ant_cryptotradingbot`.`transaction_history` (`symbol_name`, `amount`, `address`, `txID`, `from`, `to`, `type`, `details`, `status`, `username`, `txn_date`) 
                VALUES ('{}', {}, '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}');""" \
                    .format('BUSD', ("-"+amount), address, txId, 'Wallet', 'Binance Exchange', 'Withdrawal', ('Withdrawal request for ' + amount + ' BUSD'), status, username, today_date)
                wallet_query_result = db_util.queryExecution(connection, w_ins_query, 'insert')
                if wallet_query_result:
                    w_upd_query = """UPDATE `ant_cryptotradingbot`.`ant_user_wallet` set `ant_wallet_balance` = `ant_wallet_balance`-{}, `total_withdrawal` = `total_withdrawal`+{} WHERE `username` = '{}';""" \
                        .format(amount, amount, username)
                    wallet_query_result = db_util.queryExecution(connection, w_upd_query, 'insert')
                    tx_details = {
                        "amount": str(amount),
                        "coin": "BUSD (BSC - BEP20)",
                        "address": address,
                        "type": 'Withdrawal',
                        "details": 'Withdrawal request for ' + amount + ' BUSD',
                        "status": status,
                        "error": ''
                    }
                    return jsonify(tx_details)
                else:
                    tx_details['error'] = 'Something went wrong!!!'
            else:
                tx_details['error'] = 'Insufficient Balance in your Available Balance!!!'
        return jsonify(tx_details)


@app.route('/transaction_history', methods=['GET'])
@cache.cached(timeout=30)
def get_transaction_history():
    if 'username' in session:
        username = session['username']
        lst_tx_details = []
        connection = db_util.connect_database()
        if connection.is_connected():
            txn_query = """SELECT `txn_date`, `symbol_name`, `amount`, `address`, `txID`, `from`, `to`, `type`, `details`, `status` from `ant_cryptotradingbot`.`transaction_history` where `username` = '{}';"""\
                .format(username)
            query_data = db_util.queryExecution(connection, txn_query, 'select')
            if len(query_data) > 0:
                for cpd in query_data:
                    tx_details = {
                        "date": str(cpd[0].strftime('%Y-%m-%d %H:%M:%S')),
                        "date_text": str(cpd[0].strftime('%d %b, %Y')),
                        "time_text": str(cpd[0].strftime('%I:%M%p')),
                        "coin": cpd[1],
                        "amount": round(float(cpd[2]), 2),
                        "address": cpd[3],
                        "txId": cpd[4],
                        "from": cpd[5],
                        "to": cpd[6],
                        "type": cpd[7],
                        "details": cpd[8],
                        "status": cpd[9],
                        "error": ''
                    }
                    lst_tx_details.append(tx_details)
                return jsonify(lst_tx_details)
    return jsonify([])


@app.route('/activate-plan', methods=['GET'])
@cache.cached(timeout=30)
def get_activate_plan():
    if 'username' in session:
        if session['lock_status'] == 'locked':
            return redirect('lockscreen')
        session['curr_page'] = 'plan-pricing'
        username = session['username']
        plan_name = request.args.get('plan', '')
        data = {"currentPlan": '', "purchaseDate": '', "activation_balance": 0}
        addon_days = 0
        current_plan = ''
        connection = db_util.connect_database()
        if connection.is_connected():
            query = "select `validity`, `energy_power`, `current_plan` FROM `ant_cryptotradingbot`.`ant_user_data` " + \
                    "WHERE `username` = '{}' and `validity_status` = 'valid'"\
                        .format(username)
            user_data = db_util.queryExecution(connection, query, 'select')
            if len(user_data) == 1:
                session["energy_power"] = user_data[0][1]
                current_plan = user_data[0][2]
                # if user_data[0][0] is not None:
                #     dt_today = datetime.today()  # Local time
                #     dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
                #     today_date = str(dt_India.strftime('%Y/%m/%d'))
                #     validity = str(user_data[0][0].strftime('%Y/%m/%d'))
                #     # convert string to date object
                #     d1 = datetime.strptime(today_date, "%Y/%m/%d")
                #     d2 = datetime.strptime(validity, "%Y/%m/%d")
                #     # difference between dates in timedelta
                #     delta = d1 - d2
                #     addon_days = int(delta.days)
            connection.close()

        price = 0
        max_invest = 0
        KP = 0
        if plan_name == 'CryptoBot':
            price = 100
        elif plan_name == 'halfKP' and session['user_status'] == 'valid' and current_plan == 'CryptoBot':
            price = 0
            max_invest = 300
            KP = 500
        elif plan_name == '2PhalfKP':
            price = 25
            max_invest = 300
            KP = 2500
        elif plan_name == '5KP':
            price = 50
            max_invest = 500
            KP = 5000
        elif plan_name == '10KP':
            price = 100
            max_invest = 500
            KP = 10000
        elif plan_name == '100KP':
            price = 1000
            max_invest = 750
            KP = 100000
        elif plan_name == '1MP':
            price = 7000
            max_invest = 1000
            KP = 1000000
        elif plan_name == '2MP':
            price = 14000
            max_invest = 1500
            KP = 2000000
        elif plan_name == '5MP':
            price = 35000
            max_invest = 2000
            KP = 5000000

        dt_today = datetime.today()
        dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
        valid_date = str(dt_India.strftime('%Y-%m-%d 23:59:59'))
        purchaseDate = "Purchase at " + str(dt_India.strftime('%d %b, %Y'))

        dt_txn_today = datetime.today()
        dt_txn_India = dt_txn_today.astimezone(timezone('Asia/Kolkata'))
        txId = str(dt_txn_India.strftime('%Y%m%d%H%M%S')) + plan_name + str(price) + str(dt_India.strftime('%Y%m%d%H%M%S'))
        txn_date = str(dt_txn_India.strftime('%Y-%m-%d %H:%M:%S'))
        connection = db_util.connect_database()
        if connection.is_connected():
            query = "select `activation_balance` FROM `ant_cryptotradingbot`.`ant_user_wallet` " + \
                    "WHERE `username` = '{}'"\
                        .format(username)
            user_data = db_util.queryExecution(connection, query, 'select')
            if (user_data[0][0] >= price > 0) or (plan_name == 'halfKP' and session['user_status'] == 'valid'):
                act_bal = (user_data[0][0] - price)
                query = """UPDATE `ant_cryptotradingbot`.`ant_user_wallet` set `activation_balance`=`activation_balance`-{}  
                WHERE `username` = '{}'""".format(price, username)
                user_data = db_util.queryExecution(connection, query, 'update')
                if user_data:
                    session["energy_power"] = session["energy_power"] + KP
                    ins_query = """Update `ant_cryptotradingbot`.`ant_user_data` set `validity_status`='{}', `validity`='{}', `current_plan`='{}', `max_invest`={}, `energy_power`={}
                    WHERE `api_key` <> '' and `is_Active` = True and `username` = '{}'""" \
                        .format('valid', valid_date, plan_name, max_invest, session["energy_power"], username)
                    ins_user_data = db_util.queryExecution(connection, ins_query, 'update')
                    if ins_user_data:
                        w_ins_query = """INSERT `ant_cryptotradingbot`.`transaction_history` (`symbol_name`, `amount`, `address`, `txID`, `from`, `to`, `type`, `details`, `status`, `username`, `txn_date`) 
                        VALUES ('{}', {}, '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}');""" \
                            .format('BUSD', (-1*price), 'No address', txId, 'Wallet',
                                    'ANTBot', 'Purchase', ('ANTBot_'+plan_name), 'Successful', username,
                                    txn_date)
                        wallet_query_result = db_util.queryExecution(connection, w_ins_query, 'insert')
                        if wallet_query_result:
                            level_incomes = []
                            if price > 0:
                                share_price = price
                                level1 = round(float(price * 15 / 100),2)
                                level2 = round(float(price * 10 / 100),2)
                                level3 = round(float(price * 5 / 100),2)
                                level_incomes = [level1, level2, level3]
                                curr_user = username
                                level_num = 1
                                for level in level_incomes:
                                    query = "select `referal_by` FROM `ant_cryptotradingbot`.`ant_user_data` " + \
                                            "WHERE `username` = '{}'" \
                                                .format(curr_user)
                                    user_data = db_util.queryExecution(connection, query, 'select')
                                    query = "select `username` FROM `ant_cryptotradingbot`.`ant_user_data` " + \
                                            "WHERE `referal_code` = '{}'" \
                                                .format(user_data[0][0])
                                    user_data = db_util.queryExecution(connection, query, 'select')
                                    prev_user = curr_user
                                    curr_user = user_data[0][0]
                                    if plan_name == 'CryptoBot':
                                        ins_query = """Update `ant_cryptotradingbot`.`ant_user_wallet` set `ant_wallet_balance`=`ant_wallet_balance`+{}, `referal_income`=`referal_income`+{}
                                        WHERE `username` = '{}'""" \
                                            .format(level, level, curr_user)
                                    else:
                                        ins_query = """Update `ant_cryptotradingbot`.`ant_user_wallet` set `ant_wallet_balance`=`ant_wallet_balance`+{}, `level_share_income`=`level_share_income`+{}
                                        WHERE `username` = '{}'""" \
                                            .format(level, level, curr_user)
                                    ins_user_data = db_util.queryExecution(connection, ins_query, 'update')
                                    if ins_user_data:
                                        txId = str(dt_txn_India.strftime('%Y%m%d%H%M%S')) + prev_user + str(
                                            level)
                                        if plan_name == 'CryptoBot':
                                            income_type = 'Referral Income'
                                        else:
                                            income_type = 'Level Income'
                                        w_ins_query = """INSERT `ant_cryptotradingbot`.`transaction_history` (`symbol_name`, `amount`, `address`, `txID`, `from`, `to`, `type`, `details`, `status`, `username`, `txn_date`) 
                                        VALUES ('{}', {}, '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}');""" \
                                            .format('BUSD', level, 'No address', txId, prev_user,
                                                    'Wallet', income_type, ('Referral_level_'+str(level_num)), 'Received', curr_user,
                                                    txn_date)
                                        wallet_query_result = db_util.queryExecution(connection, w_ins_query, 'insert')
                                        if wallet_query_result:
                                            share_price = share_price - level
                                            level_num += 1

                                if plan_name == 'CryptoBot':
                                    ins_query = """Update `ant_cryptotradingbot`.`ant_user_wallet` set `ant_wallet_balance`=`ant_wallet_balance`+{}, `referal_income`=`referal_income`+{}
                                    WHERE `username` = '{}'""" \
                                        .format(share_price, share_price, 'Admin')
                                else:
                                    ins_query = """Update `ant_cryptotradingbot`.`ant_user_wallet` set `ant_wallet_balance`=`ant_wallet_balance`+{}, `level_share_income`=`level_share_income`+{}
                                    WHERE `username` = '{}'""" \
                                        .format(share_price, share_price, 'Admin')
                                ins_user_data = db_util.queryExecution(connection, ins_query, 'update')
                                if ins_user_data:
                                    txId = str(dt_txn_India.strftime('%Y%m%d%H%M%S')) + username + str(
                                        share_price)
                                    if plan_name == 'CryptoBot':
                                        income_type = 'CryptoBot Income'
                                    else:
                                        income_type = 'Power Income'
                                    w_ins_query = """INSERT `ant_cryptotradingbot`.`transaction_history` (`symbol_name`, `amount`, `address`, `txID`, `from`, `to`, `type`, `details`, `status`, `username`, `txn_date`) 
                                    VALUES ('{}', {}, '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}');""" \
                                        .format('BUSD', share_price, 'No address', txId, username,
                                                'Wallet', income_type, (plan_name + '_' + username), 'Received', 'Admin',
                                                txn_date)
                                    wallet_query_result = db_util.queryExecution(connection, w_ins_query, 'insert')

                            session['user_status'] = 'valid'
                            data = {"currentPlan": plan_name, "purchaseDate": purchaseDate, "activation_balance": act_bal,
                                    "user_status": 'valid'}
            connection.close()
        return jsonify(data)
    return jsonify({})


@app.route('/validate_username', methods=['GET'])
def get_validate_username():
    isValid = False
    if 'username' in session:
        check_username = request.args.get('username', '')
        val_details = {
            "full_name": '',
            "status": isValid,
            "error": ''
        }
        connection = db_util.connect_database()
        if connection.is_connected():
            query = "select `full_name` FROM `ant_cryptotradingbot`.`ant_user_data` " + \
                    "WHERE `is_Active` = True and `username` = '{}'"\
                        .format(check_username)
            user_data = db_util.queryExecution(connection, query, 'select')
            if len(user_data) > 0:
                isValid = True
                val_details = {
                    "full_name": user_data[0][0],
                    "status": isValid,
                    "error": ''
                }
        return jsonify(val_details)
    return jsonify([])


@app.route('/initiate_transfer', methods=['GET'])
@cache.cached(timeout=30)
def get_initiate_transfer():
    if 'username' in session:
        username = session['username']
        trn_username = request.args.get('username', '')
        amount = request.args.get('amt', 0)
        tx_details = {
            "amount": amount,
            "coin": "BUSD",
            "type": 'Transfer',
            "status": '',
            "error": ''
        }
        dt_today = datetime.today()  # Local time
        dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
        today_date = str(dt_India.strftime('%Y-%m-%d %H:%M:%S'))
        status = 'Successful'
        connection = db_util.connect_database()
        if connection.is_connected():
            coins_query = """SELECT `activation_balance` from `ant_cryptotradingbot`.`ant_user_wallet` where `username` = '{}';""".format(username)
            query_data = db_util.queryExecution(connection, coins_query, 'select')
            if float(query_data[0][0]) >= float(amount) >= 1:
                txId = str(dt_India.strftime('%Y%m%d%H%M%S')) + '_' + username + '_' + trn_username + '_' + str(amount)
                w_ins_query = """INSERT `ant_cryptotradingbot`.`transaction_history` (`symbol_name`, `amount`, `address`, `txID`, `from`, `to`, `type`, `details`, `status`, `username`, `txn_date`) 
                VALUES ('{}', {}, '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}');""" \
                    .format('BUSD', ("-"+amount), 'No Address', txId, username, trn_username, 'Transfer', ('Transferred ' + amount + ' BUSD to ' + trn_username), status, username, today_date)
                wallet_query_result = db_util.queryExecution(connection, w_ins_query, 'insert')
                if wallet_query_result:
                    w_upd_query = """UPDATE `ant_cryptotradingbot`.`ant_user_wallet` set `activation_balance` = `activation_balance`-{}, `total_deposit` = `total_deposit`-{} WHERE `username` = '{}';""" \
                        .format(amount, amount, username)
                    wallet_query_result = db_util.queryExecution(connection, w_upd_query, 'update')
                    if wallet_query_result:
                        w_ins_query = """INSERT `ant_cryptotradingbot`.`transaction_history` (`symbol_name`, `amount`, `address`, `txID`, `from`, `to`, `type`, `details`, `status`, `username`, `txn_date`) 
                        VALUES ('{}', {}, '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}');""" \
                            .format('BUSD', amount, 'No Address', txId, username, trn_username, 'Transfer',
                                    ('Received ' + amount + ' BUSD from ' + username), status, trn_username,
                                    today_date)
                        wallet_query_result = db_util.queryExecution(connection, w_ins_query, 'insert')
                        if wallet_query_result:
                            w_upd_query = """UPDATE `ant_cryptotradingbot`.`ant_user_wallet` set `activation_balance` = `activation_balance`+{}, `total_deposit` = `total_deposit`+{} WHERE `username` = '{}';""" \
                                .format(amount, amount, trn_username)
                            wallet_query_result = db_util.queryExecution(connection, w_upd_query, 'update')
                            tx_details = {
                                "amount": str(amount),
                                "coin": "BUSD (BSC - BEP20)",
                                "status": status,
                                "error": ''
                            }
                    return jsonify(tx_details)
                else:
                    tx_details['error'] = 'Unable to transfer amount {} to {}!!!'.format(amount, trn_username)
            else:
                tx_details['error'] = 'Insufficient Balance in your Available Balance!!!'
        return jsonify(tx_details)

