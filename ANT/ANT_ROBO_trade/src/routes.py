from datetime import datetime, timedelta
import urllib.request
import pandas as pd
import ccxt, re, sys
from pytz import timezone
from flask import Flask, escape, session, request, render_template, send_from_directory, redirect, url_for, make_response, Response
from flask_caching import CachedResponse
from src import app, cache
from src.utils import db_util
from src.utils import chart_data
from src.utils.chart_data import get_chart_data_simple
from src.utils.utility import remove_tail_dot_zeros
import warnings
warnings.filterwarnings('ignore')


@app.route("/static/<path:path>")
def static_dir(path):
    return send_from_directory("static", path)


@app.route("/assets/<path:path>")
def assets_dir(path):
    return send_from_directory("assets", path)


@app.route('/sw.js', methods=['GET'])
def sw():
    return app.send_static_file('sw.js')


@app.route('/sw_delete.js', methods=['GET'])
def sw_delete():
    return app.send_static_file('sw_delete.js')


@app.errorhandler(404)
def not_found(e):
    return render_template('404.html')


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html')


@app.route('/offline', methods=['GET'])
def offline():
    return render_template('offline.html')


def is_internet():
    try:
        urllib.request.urlopen('https://www.google.com') #Python 3.x
        return True
    except Exception as error:
        return False


@app.route('/register', methods=['GET', 'POST'])
def register():
    if not is_internet():
        return render_template('offline.html')
    refcode = request.args.get('refcode', '')
    data = {"fullname": '', "useremail": '', "username": '', "password": '', "refcode": refcode}
    style = {"fullname": '', "useremail": '', "username": '', "password": ''}
    style_valid = {"useremail": '', "username": '', "password": '', "refcode": ''}
    pass_valid = {"length": "valid", "CapitalLetter": "valid", "SmallLetter": "valid", "Number": "valid"}
    disp_block = 'display : block !important;'
    is_valid = True
    e_pat = r"\"?([-a-zA-Z0-9.`?{}]+@\w+\.\w+)\"?"
    pattern = re.compile(e_pat)
    if request.method == 'GET':
        session.clear()
        return render_template('register.html', data=data, style=style, style_valid=style_valid, pass_valid=pass_valid)
    else:
        data["fullname"] = request.form.get('fullname', True)
        data["useremail"] = request.form.get('useremail', True)
        data["username"] = request.form.get('username', True)
        data["username"] = data["username"].replace(' ', '').lower().strip()
        data["password"] = request.form.get('password', True)
        data["refcode"] = request.form.get('refcode', True)
        if data["fullname"] == '':
            style["fullname"] = disp_block
            is_valid = False
        if data["useremail"] == '':
            style["useremail"] = disp_block
            is_valid = False
        elif not re.match(pattern, data["useremail"]):
            style_valid["useremail"] = disp_block
            is_valid = False
        if data["username"] == '':
            style["username"] = disp_block
            is_valid = False
        elif data["username"].lower().replace('admin', '') != data["username"].lower():
            data["username"] = ''
            style["username"] = disp_block
            is_valid = False
        if data["password"] == '':
            style["password"] = disp_block
            is_valid = False
        else:
            is_pass_valid = True
            if len(data["password"]) < 8:
                pass_valid["length"] = "invalid"
                is_pass_valid = False
            if data["password"].lower() == data["password"]:
                pass_valid["CapitalLetter"] = "invalid"
                is_pass_valid = False
            if data["password"].upper() == data["password"]:
                pass_valid["SmallLetter"] = "invalid"
                is_pass_valid = False
            if re.sub('([0-9]+)', r'\1', data["password"]) == '':
                pass_valid["Number"] = "invalid"
                is_pass_valid = False
            if not(is_pass_valid):
                style_valid["password"] = disp_block
                is_valid = False
        if is_valid:
            dt_today = datetime.today()  # Local time
            dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
            trade_date = str(dt_India.strftime('%Y-%m-%d %H:%M:%S'))
            connection = db_util.connect_database()
            if connection.is_connected():
                usr_check_query = """SELECT count(`username`) from `ant_cryptotradingbot`.`ant_user_data` where `username` = '{}'"""\
                    .format(data["username"])
                usr_check_query_result = db_util.queryExecution(connection, usr_check_query, 'select')
                if usr_check_query_result[0][0] > 0:
                    style_valid["username"] = disp_block
                    return render_template('register.html', data=data, style=style, style_valid=style_valid, pass_valid=pass_valid)
                if data["refcode"] == '':
                    data["refcode"] = 'thouship_ant_2'
                if data["refcode"] != '':
                    sel_query = """SELECT `username`, `level_tree` from `ant_cryptotradingbot`.`ant_user_data` where `referal_code`='{}'"""\
                        .format(data["refcode"])
                    sel_query_result = db_util.queryExecution(connection, sel_query, 'select')
                    if len(sel_query_result) == 1:
                        ref_code = "{}_ant_{}".format(data["username"].lower(), (sel_query_result[0][1] + 1))
                        query = """INSERT `ant_cryptotradingbot`.`ant_user_data` (`full_name`, `email_id`, `username`, `password`, `role`, `exchange_name`, `api_key`, `api_secret`, `max_invest`, `validity`, `validity_status`, `usdt_bnb_address`, `referal_code`, `referal_by`, `level_tree`, `created_date`) 
                        VALUES (N'{}', N'{}', N'{}', N'{}', N'User', N'', N'', N'', 0, null, N'register', N'', '{}', '{}', {}, '{}');"""\
                                    .format(data["fullname"], data["useremail"], data["username"], data["password"], ref_code, data["refcode"], (sel_query_result[0][1] + 1), trade_date)
                        is_inserted = db_util.queryExecution(connection, query, 'insert')
                        if is_inserted:
                            w_ins_query = """INSERT `ant_cryptotradingbot`.`ant_user_wallet` (`username`, `initial_investment`, `binance_exchange_usdt`) VALUES ('{}', {}, {});""" \
                                .format(data["username"], 0.00, 0.00)
                            wallet_query_result = db_util.queryExecution(connection, w_ins_query, 'insert')
                            session['username'] = data["username"]
                            session['full_name'] = data["fullname"]
                            session['role'] = "User"
                            session['display_mode'] = 'dark-mode'
                            session['energy_power'] = 0
                            session['wallet_balance'] = 0
                            session['lock_status'] = 'unlocked'
                            session['user_status'] = 'register'
                            return redirect('./dashboard-crypto')
                    else:
                        style_valid["refcode"] = disp_block
                return render_template('register.html', data=data, style=style, style_valid=style_valid, pass_valid=pass_valid)
        else:
            return render_template('register.html', data=data, style=style, style_valid=style_valid, pass_valid=pass_valid)


@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    next = request.args.get('next', '')
    data = {"username": '', "password": ''}
    style_valid = {"login": ''}
    disp_block = 'display : block !important;'
    login_req = 'display : none !important;'
    if request.method == 'GET':
        if next != '':
            login_req = 'display : block !important;'
        session.clear()
        return render_template('login.html', data=data, style_valid=style_valid, login_req=login_req)
    else:
        data["username"] = request.form.get('username', True)
        data["password"] = request.form.get('password', True)
        connection = db_util.connect_database()
        if connection.is_connected():
            query = "select `full_name`, `role`, `validity_status`, `validity`, `referal_code`, `referal_by`, `display_mode`, `energy_power` FROM `ant_cryptotradingbot`.`ant_user_data` " + \
                    "WHERE `is_Active` = True and `username` = '{}' and `password` = '{}'"\
                        .format(data["username"].lower(), data["password"])
            user_data = db_util.queryExecution(connection, query, 'select')
            if len(user_data) > 0:
                session['username'] = data["username"].lower()
                session['full_name'] = user_data[0][0]
                session['role'] = user_data[0][1]
                session['referral_by'] = 'ANT Admin (Admin)'
                session['lock_status'] = 'unlocked'
                session['user_status'] = user_data[0][2]
                session['validity'] = user_data[0][3]
                session['referral_code'] = user_data[0][4]
                session['referral_code_encode'] = user_data[0][4].replace('#', '%23')
                session['display_mode'] = user_data[0][6]
                session['energy_power'] = user_data[0][7]
                query = """select `full_name`, `username` from `ant_cryptotradingbot`.`ant_user_data` 
                where referal_code = '{}'""" \
                    .format(user_data[0][5])
                query_data = db_util.queryExecution(connection, query, 'select')
                if len(query_data) == 1:
                    session['referral_by'] = str(query_data[0][0]) + "({})".format(query_data[0][1])
                query = """select `ant_wallet_balance`  from `ant_cryptotradingbot`.`ant_user_wallet` 
                where username = '{}'""" \
                    .format(data["username"].lower())
                query_data = db_util.queryExecution(connection, query, 'select')
                if len(query_data) == 1:
                    session['wallet_balance'] = query_data[0][0]
                else:
                    session['wallet_balance'] = 0

                if session['validity'] is not None:
                    dt_today = datetime.today()  # Local time
                    dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
                    today_date = str(dt_India.strftime('%Y/%m/%d'))
                    validity = str(session['validity'].strftime('%Y/%m/%d'))
                    # convert string to date object
                    d1 = datetime.strptime(today_date, "%Y/%m/%d")
                    d2 = datetime.strptime(validity, "%Y/%m/%d")
                    # difference between dates in timedelta
                    delta = d1 - d2
                    query = """UPDATE `ant_cryptotradingbot`.`ant_user_data` SET `valid_days_left`={}  WHERE `username`='{}';""" \
                        .format(delta.days, data["username"].lower())
                    is_inserted = db_util.queryExecution(connection, query, 'update')
                if next == '':
                    return redirect('./dashboard-crypto')
                else:
                    return redirect('./{}'.format(next))
            else:
                style_valid["login"] = disp_block
            return render_template('login.html', data=data, style_valid=style_valid, login_req=login_req)


@app.route('/logout')
def logout():
    session.clear()
    return render_template('logout.html')


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'GET':
        return render_template('forgot-password.html', emailsent=False)
    else:
        email = request.form.get('email', '')
        return render_template('forgot-password.html', emailsent=True)


@app.route('/lockscreen', methods=['GET', 'POST'])
def lockscreen():
    if 'username' in session:
        next = request.args.get('next', '')
        style_valid = {"login": ''}
        disp_block = 'display : block !important;'
        if request.method == 'GET':
            session['lock_status'] = 'locked'
            return render_template('lockscreen.html', style_valid=style_valid)
        else:
            password = request.form.get('password', '')
            connection = db_util.connect_database()
            if connection.is_connected():
                query = "select `full_name`, `role`, `exchange_name`, `api_key`, `api_secret` FROM `ant_cryptotradingbot`.`ant_user_data` " + \
                        "WHERE `is_Active` = True and `username` = '{}' and `password` = '{}'"\
                            .format(session["username"].lower(), password)
                user_data = db_util.queryExecution(connection, query, 'select')
                if len(user_data) > 0:
                    session['lock_status'] = 'unlocked'
                    if next == '':
                        return redirect('./dashboard-crypto')
                    else:
                        return redirect('./{}'.format(next))
                else:
                    style_valid["login"] = disp_block
            return render_template('lockscreen.html', style_valid=style_valid)
    else:
        return redirect('./login?next={}'.format('dashboard-crypto'))


@app.route('/dashboard-admin', methods=['GET', 'POST'])
@cache.cached()
def dashboard_admin():
    try:
        if 'username' in session:
            if session['role'] == 'Admin':
                if session['lock_status'] == 'locked':
                    return redirect('lockscreen')
                session['curr_page'] = 'dashboard-admin'
                return CachedResponse(
        response=make_response(render_template('dashboard-admin.html')), timeout=30,)
            else:
                return redirect('./dashboard-crypto')
        else:
            return redirect('./login?next={}'.format('dashboard-admin'))
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - dashboard-admin :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print(error_log)
        return CachedResponse(
        response=make_response(render_template('error.html', error=error_log)), timeout=30,)


@app.route('/dashboard-crypto', methods=['GET', 'POST'])
@cache.cached()
def dashboard_user():
    try:
        if 'username' in session:
            if session['lock_status'] == 'locked':
                return redirect('lockscreen')
            session['curr_page'] = 'dashboard-crypto'
            username = session['username']
            data = {
                "total_invested": 0,
                "initial_invested": 0,
                "total_changes": 0,
                "total_changes_percent": 0,
                "month_changes": 0,
                "month_changes_percent": 0,
                "today_changes": 0,
                "today_changes_percent": 0
            }
            top_coin_data = []
            coin_data = {
                "symbol_name": '',
                "symbol_full_name": '',
                "current_price": '',
                "24h_change": '',
                "sparkline_charts": ''
            }
            exchange = ccxt.binance()
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
                        data["total_diffs"] = round(
                            float(query_data[0][1]) + float(query_data[1][0]) - float(query_data[0][1]), 2)
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
            connection.close()
            return CachedResponse(
        response=make_response(render_template('crypto-dashboard.html', data=data, top_coin=top_coin_data)), timeout=30,)
        else:
            return redirect('./login?next={}'.format('dashboard-crypto'))
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - user_dashboard :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print(error_log)
        return CachedResponse(
        response=make_response(render_template('error.html', error=error_log)), timeout=30,)


@app.route('/crypto-wallet', methods=['GET', 'POST'])
@cache.cached()
def crypto_wallet():
    try:
        if 'username' in session:
            if session['lock_status'] == 'locked':
                return redirect('lockscreen')
            session['curr_page'] = 'crypto-wallet'
            username = session['username']
            data = {
                "wallet_balance": 0.00,
                "total_deposit": 0.00,
                "total_withdrawal": 0.00,
                "referral_income": 0.00,
                "activation_balance": 0.00,
                "withdrawal_eligible": 0.00,
                "level_profit_share": 0.00
            }
            connection = db_util.connect_database()
            if connection.is_connected():
                query = """select `ant_wallet_balance`, `total_deposit`, `total_withdrawal`, `referal_income`, 
                `activation_balance`, `withdrawal_eligible`, `level_share_income`  from `ant_cryptotradingbot`.`ant_user_wallet` 
                where username = '{}'""" \
                    .format(username)
                query_data = db_util.queryExecution(connection, query, 'select')
                if len(query_data) == 1:
                    session['wallet_balance'] = round(float(query_data[0][0]), 2)
                    data = {
                        "wallet_balance": round(float(query_data[0][0]), 2),
                        "total_deposit": round(float(query_data[0][1]), 2),
                        "total_withdrawal": round(float(query_data[0][2]), 2),
                        "referral_income": round(float(query_data[0][3]), 2),
                        "activation_balance": round(float(query_data[0][4]), 2),
                        "withdrawal_eligible": round(float(query_data[0][5]), 2),
                        "level_profit_share": round(float(query_data[0][6]), 2),
                    }
            return CachedResponse(
        response=make_response(render_template('crypto-wallet.html', data=data)), timeout=30,)
        else:
            return redirect('./login?next={}'.format('crypto-wallet'))
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - crypto_wallet :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print(error_log)
        return CachedResponse(
        response=make_response(render_template('error.html', error=error_log)), timeout=30,)


@app.route('/crypto-orders', methods=['GET', 'POST'])
@cache.cached()
def crypto_orders():
    try:
        if 'username' in session:
            if session['lock_status'] == 'locked':
                return redirect('lockscreen')
            session['curr_page'] = 'crypto-orders'
            return CachedResponse(
        response=make_response(render_template('crypto-orders.html')), timeout=30,)
        else:
            return redirect('./login?next={}'.format('crypto-orders'))
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - crypto_orders :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print(error_log)
        return CachedResponse(
        response=make_response(render_template('error.html', error=error_log)), timeout=30,)


@app.route('/crypto-reports', methods=['GET', 'POST'])
@cache.cached()
def crypto_reports():
    try:
        if 'username' in session:
            if session['lock_status'] == 'locked':
                return redirect('lockscreen')
            session['curr_page'] = 'crypto-reports'
            return CachedResponse(
        response=make_response(render_template('crypto-reports.html')), timeout=30,)
        else:
            return redirect('./login?next={}'.format('crypto-reports'))
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - crypto_reports :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print(error_log)
        return CachedResponse(
        response=make_response(render_template('error.html', error=error_log)), timeout=30,)


@app.route('/faqs', methods=['GET'])
@cache.cached()
def faqs_help():
    try:
        if 'username' in session:
            if session['lock_status'] == 'locked':
                return redirect('lockscreen')
            session['curr_page'] = 'faqs'
            return CachedResponse(
        response=make_response(render_template('faqs.html')), timeout=30,)
        else:
            return redirect('./login?next={}'.format('faqs'))
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - faqs :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print(error_log)
        return CachedResponse(
        response=make_response(render_template('error.html', error=error_log)), timeout=30,)


@app.route('/referral-page', methods=['GET'])
@cache.cached()
def referral_page():
    try:
        if 'username' in session:
            if session['lock_status'] == 'locked':
                return redirect('lockscreen')
            session['curr_page'] = 'faqs'
            if session['user_status'] == 'valid':
                return CachedResponse(
        response=make_response(render_template('referral-page.html')), timeout=30,)
            else:
                return CachedResponse(
        response=make_response(render_template('404.html', error='Access Denied')), timeout=30,)
        else:
            return redirect('./login?next={}'.format('referral-page'))
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - referral-page :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print(error_log)
        return CachedResponse(
        response=make_response(render_template('error.html', error=error_log)), timeout=30,)


@app.route('/plan-pricing', methods=['GET'])
@cache.cached()
def plan_pricing():
    try:
        if 'username' in session:
            if session['lock_status'] == 'locked':
                return redirect('lockscreen')
            session['curr_page'] = 'plan-pricing'
            username = session['username']
            data = {"currentPlan": '', "purchaseDate": '', "activation_balance": 0, "energy_power": 0, "planMethod": 'bot'}
            style_valid = {"config": '', "is_enough_balance": ''}
            disp_block = 'display : block !important;'
            connection = db_util.connect_database()
            if connection.is_connected():
                query = "select `validity_status`, `validity`, `current_plan`, `energy_power` FROM `ant_cryptotradingbot`.`ant_user_data` " + \
                        "WHERE `API_Key` <> '' and `is_Active` = True and `username` = '{}'"\
                            .format(username)
                user_data = db_util.queryExecution(connection, query, 'select')
                if len(user_data) == 1:
                    session['user_status'] = user_data[0][0]
                    data["currentPlan"] = user_data[0][2]
                    data["energy_power"] = user_data[0][3]
                    if user_data[0][1] is not None:
                        data["purchaseDate"] = "Purchased at " + str(user_data[0][1].strftime('%d %b, %Y'))
                    if data["currentPlan"] == '':
                        data["planMethod"] = 'bot'
                    else:
                        data["planMethod"] = 'month'
                else:
                    style_valid["config"] = disp_block
                query = "select `activation_balance` FROM `ant_cryptotradingbot`.`ant_user_wallet` " + \
                        "WHERE `username` = '{}'"\
                            .format(username)
                user_data = db_util.queryExecution(connection, query, 'select')
                if len(user_data) == 1:
                    data["activation_balance"] = user_data[0][0]
                if data["activation_balance"] < 15 and data["currentPlan"] == '' and style_valid["config"] == '':
                    style_valid["is_enough_balance"] = disp_block
            return CachedResponse(
        response=make_response(render_template('plan-pricing.html', data=data, style_valid=style_valid)), timeout=30,)
        else:
            return redirect('./login?next={}'.format('plan-pricing'))
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - plan-pricing :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print(error_log)
        return CachedResponse(
        response=make_response(render_template('error.html', error=error_log)), timeout=30,)


@app.route('/configuration', methods=['GET', 'POST'])
@cache.cached()
def configuration():
    try:
        if 'username' in session:
            if session['lock_status'] == 'locked':
                return redirect('lockscreen')
            session['curr_page'] = 'configuration'
            username = session['username']
            editmode = request.args.get('edit', '')
            ip_confirm = request.form.get('ip_confirm', False)
            data = {"api_key": '', "secret_key": '', "ip_address": '108.175.13.203', "currentPlan": '', "expireDate": ''}
            style = {"api_key": '', "secret_key": '', "ip_address": '', "is_exist": '', "is_edit": ''}
            style_valid = {"api_key": '', "secret_key": ''}
            disp_block = 'display : block !important;'
            disp_none = 'display : none !important;'
            is_valid = True
            if request.method == 'GET':
                connection = db_util.connect_database()
                if connection.is_connected():
                    sel_query = """SELECT `exchange_name`, `api_key`, `api_secret`, `current_plan`, `validity`, `validity_status` 
                    from `ant_cryptotradingbot`.`ant_user_data` where `api_key` <> '' and `username`='{}'""" \
                        .format(username)
                    sel_query_result = db_util.queryExecution(connection, sel_query, 'select')
                    if len(sel_query_result) == 1:
                        data["exchange_name"] = sel_query_result[0][0]
                        data["api_key"] = sel_query_result[0][1]
                        data["secret_key"] = sel_query_result[0][2]
                        data["currentPlan"] = sel_query_result[0][3]
                        session['user_status'] = sel_query_result[0][5]
                        if sel_query_result[0][4] is not None:
                            data["expireDate"] = "Expire at " + str(sel_query_result[0][4].strftime('%d %b, %Y'))
                        if session['user_status'] == "Expired":
                            data["expireDate"] = "Expired at " + str(sel_query_result[0][4].strftime('%d %b, %Y'))
                        if editmode == '':
                            style["is_exist"] = disp_block
                            style["is_edit"] = disp_none
                        else:
                            style["is_exist"] = disp_none
                            style["is_edit"] = disp_block
                        connection.close()
                        return CachedResponse(
        response=make_response(render_template('configuration.html', data=data, style=style, style_valid=style_valid)), timeout=30,)
                style["is_exist"] = disp_none
                style["is_edit"] = disp_block
                return CachedResponse(
        response=make_response(render_template('configuration.html', data=data, style=style, style_valid=style_valid)), timeout=30,)
            else:
                data["api_key"] = request.form.get('api_key', '')
                data["secret_key"] = request.form.get('secret_key', '')
                if data["api_key"] == '':
                    style["api_key"] = disp_block
                    is_valid = False

                if data["secret_key"] == '':
                    style["secret_key"] = disp_block
                    is_valid = False

                if not ip_confirm:
                    style["ip_address"] = disp_block
                    is_valid = False

                if is_valid:
                    connection = db_util.connect_database()
                    if connection.is_connected():
                        usr_check_query = """SELECT count(`username`) from `ant_cryptotradingbot`.`ant_user_data` where `api_key`='{}' and `api_secret`='{}';""" \
                            .format(data["api_key"], data["secret_key"])
                        usr_check_query_result = db_util.queryExecution(connection, usr_check_query, 'select')
                        if usr_check_query_result[0][0] == 0:
                            query = """UPDATE `ant_cryptotradingbot`.`ant_user_data` SET `exchange_name`='{}', `api_key`='{}', `api_secret`='{}'
                             WHERE `username`='{}';""" \
                                .format('Binance', data["api_key"], data["secret_key"], username)
                            is_inserted = db_util.queryExecution(connection, query, 'update')
                            if is_inserted:
                                query = """UPDATE `ant_cryptotradingbot`.`ant_user_data` SET `validity_status`='{}'
                                 WHERE `username`='{}' and `validity_status`='register';""" \
                                    .format('configured', username)
                                is_inserted = db_util.queryExecution(connection, query, 'update')
                                if is_inserted:
                                    session['user_status'] = 'configured'
                                else:
                                    sel_query = """SELECT `validity_status` from `ant_cryptotradingbot`.`ant_user_data` 
                                     WHERE `username`='{}';""" \
                                        .format(username)
                                    sel_result = db_util.queryExecution(connection, sel_query, 'select')
                                    if len(sel_result) > 0:
                                        session['user_status'] = sel_result[0][0]
                                    else:
                                        session['user_status'] = 'register'
                            return redirect('./configuration')
                        else:
                            style_valid["api_key"] = disp_block
                            return CachedResponse(
        response=make_response(render_template('configuration.html', data=data, style=style,
                                                   style_valid=style_valid)), timeout=30,)
                    return CachedResponse(
        response=make_response(render_template('configuration.html', data=data, style=style, style_valid=style_valid)), timeout=30,)
                else:
                    return CachedResponse(
        response=make_response(render_template('configuration.html', data=data, style=style, style_valid=style_valid)), timeout=30,)
        else:
            return redirect('./login?next={}'.format('configuration'))
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - configuration :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print(error_log)
        return CachedResponse(
        response=make_response(render_template('error.html', error=error_log)), timeout=30,)
