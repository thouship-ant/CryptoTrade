SELECT symbol_name, price_breakOut_entry from `ant_cryptotradingbot`.`crypto_symbols_data` where is_active = true and is_Future_Trade = true and `price_breakOut_entry` != 0;
-- Future
call `ant_cryptotradingbot`.`db_future_trade_entry`('thouship');
call `ant_cryptotradingbot`.`db_future_trade_exit`('RENUSDT', 'thouship');
select * FROM `ant_cryptotradingbot`.`crypto_symbols_data` WHERE symbol_name='LUNAUSDT'
select * FROM `ant_cryptotradingbot`.`crypto_symbols_macd_st_data` WHERE symbol_name='MINAUSDT'
call `ant_cryptotradingbot`.`order_reports`('thouship', '', '');

select * FROM `ant_cryptotradingbot`.`crypto_symbols_data` WHERE symbol_name='FETUSDT'

select * FROM `ant_cryptotradingbot`.`crypto_symbols_name` WHERE symbol_name='KAVA'
-- DELETE FROM `ant_cryptotradingbot`.`crypto_symbols_name` WHERE symbol_seq_id=647

-- old Future Entry
SELECT dblts.symbol_name, dblts.signal_type, dblts.signal_side, dblts.entry_price, dbdt.exit_price, dbdt.stop_price, dbdt.qty_per_usdt, dblts.trade_id FROM `ant_cryptotradingbot`.`db_live_trade_signals` as dblts
                    INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_data` as csd on csd.symbol_name = dblts.symbol_name 
                    INNER JOIN `ant_cryptotradingbot`.`db_demo_trade` as dbdt on dblts.trade_id = dbdt.trade_id 
                    LEFT OUTER JOIN `ant_cryptotradingbot`.`current_buy_order_report_future` as cborf on dblts.symbol_name = cborf.symbol_name and cborf.signal_type = concat(dblts.signal_type, ' - ', dblts.signal_side) and cborf.username = 'thouship'
                    WHERE dblts.trade_closed=False and dblts.is_tradeable=True and csd.`is_Future_Trade` = True and cborf.symbol_name is null and (((csd.current_askPrice <= dblts.entry_price or csd.price_breakOut = 1) and dblts.signal_side = 'BUY') or ((csd.current_bidPrice >= dblts.entry_price or csd.price_breakOut = -1) and dblts.signal_side = 'SELL'));


SELECT dblts.symbol_name, dblts.signal_type, dblts.signal_side, case when dblts.signal_side = 'BUY' THEN cborf.buy_price ELSE cborf.sell_price END as entry_price, dbdt.exit_price, dbdt.stop_price, dbdt.qty_per_usdt, cborf.trade_id FROM `ant_cryptotradingbot`.`db_live_trade_signals` as dblts
                                    INNER JOIN `ant_cryptotradingbot`.`current_buy_order_report_future` as cborf on dblts.symbol_name = cborf.symbol_name and cborf.signal_type = concat(dblts.signal_type, ' - ', dblts.signal_side) and cborf.username = 'thouship' and dblts.trade_id = cborf.trade_id
                                    INNER JOIN `ant_cryptotradingbot`.`db_demo_trade` as dbdt on dblts.trade_id = dbdt.trade_id
                                    WHERE dblts.trade_closed=False and dbdt.exit_date is null and dbdt.symbol_name ='TRXUSDT';

call `ant_cryptotradingbot`.`user_recent_activity`('thouship', '2024-01-21', '2024-01-22 23:59:59');

SELECT DISTINCT orp.symbol_name, csd.current_askPrice, cbor.profit_percent as current_percent, orp.order_quantity, 
            orp.buy_price, orp.buy_amount, ifnull(orp.sell_price, 0) as sell_price, ifnull(orp.sell_amount, 0) as sell_amount, 
            ifnull(cbor.target_price, 0) as target_price, ifnull(cbor.stoploss_price, 0) as stoploss_price, orp.order_date, cbor.order_seq_id, cbor.signal_type
            from `ant_cryptotradingbot`.`current_buy_order_report_future` as cbor 
            inner join `ant_cryptotradingbot`.`crypto_symbols_data` as csd on cbor.symbol_name = csd.symbol_name
            inner join `ant_cryptotradingbot`.`order_report_future` as orp on cbor.symbol_name = orp.symbol_name and cbor.username = orp.username and cbor.order_date = orp.order_date
            where cbor.username = 'thouship'
            order by cbor.order_seq_id asc;
                    
                    
SELECT dblts.symbol_name, dblts.signal_type, dblts.signal_side, case when dblts.signal_side = 'BUY' THEN cborf.buy_price ELSE cborf.sell_price END as entry_price, dbdt.exit_price, dbdt.stop_price, dbdt.qty_per_usdt, cborf.trade_id FROM `ant_cryptotradingbot`.`db_live_trade_signals` as dblts
                                    INNER JOIN `ant_cryptotradingbot`.`current_buy_order_report_future` as cborf on dblts.symbol_name = cborf.symbol_name and cborf.signal_type = concat(dblts.signal_type, ' - ', dblts.signal_side) and cborf.username = 'thouship' and dblts.trade_id = cborf.trade_id
                                    INNER JOIN `ant_cryptotradingbot`.`db_demo_trade` as dbdt on dblts.trade_id = dbdt.trade_id
                                    WHERE dblts.trade_closed=False and dbdt.exit_date is null and dbdt.symbol_name ='TRUUSDT';
                                    
                                    
	select order_seq_id from `ant_cryptotradingbot`.`current_buy_order_report_future` WHERE `username`='thouship' order by order_seq_id asc;
    
SELECT csd.`symbol_name`, csd.`current_askPrice`, csema.ema_7 as `entry_price`, 'PRICEBREAKOUT' as `signal_type`, CASE WHEN csd.price_breakOut_entry = 1 THEN 'BUY' ELSE 'SELL' END as `signal_side`, csd.`is_Margin_Trade`, csd.`last_update_DateTime` as `update_datetime` 
	FROM `ant_cryptotradingbot`.`crypto_symbols_data` as csd
	INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_ema_data` as csema on csd.symbol_name = csema.symbol_name 
	WHERE csd.is_Active = True and csd.is_Margin_Trade = True and (csd.price_breakOut_entry = 1 or csd.price_breakOut_entry = -1)
    ;
    
SELECT csn.symbol_name as symbol, replace(csn.symbol_full_name, '_', '') as symbol_full_name, csdm.order_quantity, 
            (csdm.buy_amount / csdm.order_quantity) as avg_buy_price, (csdm.sell_amount / csdm.order_quantity) as avg_sell_price,
            (csdm.sell_amount - csdm.buy_amount) as profit_amount, ((csdm.sell_amount - csdm.buy_amount) / (csdm.buy_amount / 100)) as profit_percent from
            (SELECT csd.symbol_name as symbol_name, sum(csd.`order_quantity`) as order_quantity, sum(csd.`buy_amount`) as buy_amount, sum(csd.`sell_amount`) as sell_amount from `ant_cryptotradingbot`.`order_report_future` as csd
            where csd.`username` = 'thouship' and csd.`sell_amount` is not null group by symbol_name) as csdm
            inner join `ant_cryptotradingbot`.`crypto_symbols_name` as csn on csn.symbol_name = replace(csdm.symbol_name, 'USDT', '')
            where csdm.sell_amount is not null order by csdm.symbol_name asc;
            
SELECT DISTINCT orp.symbol_name, csd.current_askPrice, cbor.profit_percent as current_percent, orp.order_quantity, 
            orp.buy_price, orp.buy_amount, ifnull(orp.sell_price, 0) as sell_price, ifnull(orp.sell_amount, 0) as sell_amount, 
            ifnull(cbor.target_price, 0) as target_price, ifnull(cbor.stoploss_price, 0) as stoploss_price, orp.order_date, cbor.order_seq_id, cbor.signal_type
            from `ant_cryptotradingbot`.`current_buy_order_report_future` as cbor 
            inner join `ant_cryptotradingbot`.`crypto_symbols_data` as csd on cbor.symbol_name = csd.symbol_name
            inner join `ant_cryptotradingbot`.`order_report_future` as orp on cbor.symbol_name = orp.symbol_name and cbor.username = orp.username and orp.profit_amount is null
            where cbor.username = 'thouship'
            order by cbor.order_seq_id asc;