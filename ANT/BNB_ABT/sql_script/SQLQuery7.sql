-- truncate table `ant_cryptotradingbot`.`db_live_trade_signals` 
-- DELETE from `ant_cryptotradingbot`.`order_report_future` where profit_amount is null;
-- truncate table `ant_cryptotradingbot`.`current_buy_order_report_future` 
-- DELETE from `ant_cryptotradingbot`.`current_buy_order_report_future` where symbol_name = 'SCUSDT';
-- DELETE from `ant_cryptotradingbot`.`order_report_future` where profit_amount is null and symbol_name = 'SCUSDT';
SELECT * from `ant_cryptotradingbot`.`ADAUSDT` order by `DateTime` desc;
SELECT * from `ant_cryptotradingbot`.`db_demo_trade` where exit_date is not null order by `exit_date` desc;
SELECT * from `ant_cryptotradingbot`.`db_demo_trade` order by `entry_date` desc;
SELECT * from `ant_cryptotradingbot`.`db_telegram_trade_signals` order by `entry_date` desc;
SELECT * from `ant_cryptotradingbot`.`db_telegram_trade_signals` where is_tradeable = True AND trade_closed = False  order by `entry_date` desc;
SELECT * from `ant_cryptotradingbot`.`db_live_trade_signals` order by `trade_id` desc;
SELECT * from `ant_cryptotradingbot`.`db_demo_trade` where exit_date is null order by `trade_id` desc;
SELECT * from `ant_cryptotradingbot`.`db_live_trade_signals` where is_tradeable = True AND trade_closed = False order by `trade_id` desc;
SELECT * from `ant_cryptotradingbot`.`db_live_trade_signals` where symbol_name = 'LINAUSDT' order by `trade_id` desc;
SELECT * from `ant_cryptotradingbot`.`crypto_symbols_data` where symbol_name = 'IOTXUSDT';
SELECT * from `ant_cryptotradingbot`.`db_demo_trade` where `trade_id` = 3048;
SELECT * from `ant_cryptotradingbot`.`current_buy_order_report_future` order by `symbol_name` desc;
SELECT * from `ant_cryptotradingbot`.`order_report_future` where profit_amount is null order by `symbol_name` desc;
SELECT * from `ant_cryptotradingbot`.`order_report_future` where profit_amount is not null order by `update_date` desc;
SELECT * from `ant_cryptotradingbot`.`order_report_future` where profit_amount is not null and order_date = update_date;
select symbol_name from `ant_cryptotradingbot`.`current_buy_order_report_future` WHERE `username`='thouship' order by trade_id asc;

SELECT CASE WHEN dbdt.signal_side = 'BUY' THEN cbor.buy_price ELSE cbor.sell_price END from `ant_cryptotradingbot`.`db_demo_trade` as dbdt 
INNER JOIN `ant_cryptotradingbot`.`current_buy_order_report_future` as cbor on cbor.trade_id = dbdt.trade_id and (cbor.username = 'thouship')
WHERE cbor.symbol_name is not null AND ((dbdt.entry_price <= cbor.buy_price AND dbdt.signal_side = 'BUY') OR (dbdt.entry_price <= cbor.sell_price AND dbdt.signal_side = 'SELL'));


UPDATE `ant_cryptotradingbot`.`db_demo_trade` as dbdt 
INNER JOIN `ant_cryptotradingbot`.`current_buy_order_report_future` as cbor on cbor.trade_id = dbdt.trade_id and (cbor.username = 'thouship' or 'thouship' is null)
SET dbdt.entry_price = CASE WHEN dbdt.signal_side = 'BUY' THEN cbor.buy_price ELSE cbor.sell_price END
WHERE cbor.symbol_name is not null AND ((dbdt.entry_price > cbor.buy_price AND dbdt.signal_side = 'BUY') OR (dbdt.entry_price < cbor.sell_price AND dbdt.signal_side = 'SELL'));

-- orig
--     UPDATE `ant_cryptotradingbot`.`db_demo_trade` as dbdt 
-- 		INNER JOIN `ant_cryptotradingbot`.`current_buy_order_report_future` as cbor on cbor.trade_id = dbdt.trade_id and (cbor.username = username or username is null)
-- 		SET dbdt.entry_price = CASE WHEN dbdt.signal_side = 'BUY' THEN cbor.buy_price ELSE cbor.sell_price END
-- 		WHERE cbor.symbol_name is not null AND ((dbdt.entry_price > cbor.buy_price AND dbdt.signal_side = 'BUY') OR (dbdt.entry_price < cbor.sell_price AND dbdt.signal_side = 'SELL'));


-- UPDATE `ant_cryptotradingbot`.`order_report_future` 
-- SET update_date = ADDTIME(update_date, "510")
-- where profit_amount is not null and order_date = update_date;

-- INSERT `ant_cryptotradingbot`.`db_live_trade_signals` (`trade_id`, `trade_date`, `symbol_name`, `signal_type`, `signal_side`, `entry_price`, `exit_price`, `stop_price`) VALUES (2487,'2024-03-14','DATAUSDT','MACD','SELL',0.08410000,0.08397000,0.08326000);
-- INSERT `ant_cryptotradingbot`.`db_live_trade_signals` (`trade_id`, `trade_date`, `symbol_name`, `signal_type`, `signal_side`, `entry_price`, `exit_price`, `stop_price`) VALUES (2488,'2024-03-14','PEOPLEUSDT','MACD','SELL',0.04841000,0.04834000,0.04793000);
-- UPDATE `ant_cryptotradingbot`.`db_live_trade_signals` as dblts SET dblts.is_tradeable = True WHERE trade_id in (2488,2487)
-- UPDATE `ant_cryptotradingbot`.`db_live_trade_signals` as dblts 
-- INNER JOIN `ant_cryptotradingbot`.`db_demo_trade` as dbdt on dblts.trade_id = dbdt.trade_id 
-- SET dblts.is_tradeable = False 
-- WHERE (dbdt.exit_date is null AND ADDTIME(dbdt.entry_date, "10000") < ADDTIME(CONCAT(CURDATE(), ' ', CURRENT_TIME()), "53000")) OR dbdt.exit_date is not null;


-- UPDATE `ant_cryptotradingbot`.`db_telegram_trade_signals` as dblts SET dblts.is_tradeable = False, dblts.trade_closed = True WHERE trade_id in (3233)
-- UPDATE `ant_cryptotradingbot`.`db_demo_trade` SET exit_date = entry_date WHERE trade_id = 3233
-- UPDATE `ant_cryptotradingbot`.`db_live_trade_signals` as dblts SET dblts.is_tradeable = False, dblts.trade_closed = True WHERE trade_id in (3233)
-- UPDATE `ant_cryptotradingbot`.`db_live_trade_signals` SET is_tradeable = False WHERE 
-- DELETE from `ant_cryptotradingbot`.`current_buy_order_report_future` where order_seq_id in (0,2)
-- UPDATE `ant_cryptotradingbot`.`current_buy_order_report_future` set order_quantity=2225, buy_price=0.08568 where order_seq_id=3;

SELECT cborf.order_seq_id from `ant_cryptotradingbot`.`current_buy_order_report_future`  as cborf
left join `ant_cryptotradingbot`.`order_report_future` as orf on cborf.symbol_name = orf.symbol_name and orf.profit_amount is null
where orf.symbol_name is null


SELECT * from `ant_cryptotradingbot`.`order_report_future` where `symbol_name`='STMXUSDT' order by `order_seq_id` desc;
SELECT * from `ant_cryptotradingbot`.`order_report_future` order by `order_seq_id` desc;
-- DELETE from `ant_cryptotradingbot`.`db_live_trade_signals` where trade_id > 1685;

-- UPDATE `ant_cryptotradingbot`.`current_buy_order_report_future` set trade_id=1686 where order_seq_id=1 -- XLMUSDT
-- UPDATE `ant_cryptotradingbot`.`current_buy_order_report_future` set trade_id=1686 where order_seq_id=1 -- XLMUSDT
-- UPDATE `ant_cryptotradingbot`.`current_buy_order_report_future` set trade_id=1771 where order_seq_id=3 -- CELRUSDT
-- UPDATE `ant_cryptotradingbot`.`current_buy_order_report_future` set trade_id=1770 where order_seq_id=0 -- MATICUSDT

-- UPDATE `ant_cryptotradingbot`.`db_live_trade_signals` set exit_price=0.7242,stop_price=0.7242 where `trade_id` =1770;

-- UPDATE `ant_cryptotradingbot`.`db_live_trade_signals` set exit_price=0.7242,stop_price=0.7242 where `trade_id` =1770;

SELECT dblts.symbol_name, dblts.signal_type, dblts.signal_side, case when dblts.signal_side = 'BUY' THEN cborf.buy_price ELSE cborf.sell_price END as entry_price, dbdt.exit_price, dbdt.stop_price, dbdt.qty_per_usdt FROM `ant_cryptotradingbot`.`db_live_trade_signals` as dblts
                            INNER JOIN `ant_cryptotradingbot`.`current_buy_order_report_future` as cborf on dblts.symbol_name = cborf.symbol_name and cborf.signal_type = concat(dblts.signal_type, ' - ', dblts.signal_side) and cborf.username = 'thouship'
                            INNER JOIN `ant_cryptotradingbot`.`db_demo_trade` as dbdt on dblts.trade_id = dbdt.trade_id
                            WHERE dblts.trade_closed=False and dbdt.exit_date is null and dbdt.symbol_name ='MATICUSDT';

SELECT dblts.symbol_name, dblts.signal_type, dblts.signal_side, csd.current_bidPrice,dblts.entry_price, dbdt.exit_price, dbdt.stop_price, dbdt.qty_per_usdt FROM `ant_cryptotradingbot`.`db_live_trade_signals` as dblts
                    INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_data` as csd on csd.symbol_name = dblts.symbol_name 
                    INNER JOIN `ant_cryptotradingbot`.`db_demo_trade` as dbdt on dblts.trade_id = dbdt.trade_id 
                    LEFT OUTER JOIN `ant_cryptotradingbot`.`current_buy_order_report_future` as cborf on dblts.symbol_name = cborf.symbol_name and cborf.signal_type = concat(dblts.signal_type, ' - ', dblts.signal_side) and cborf.username = 'thouship'
                    WHERE dblts.trade_closed=False and dblts.is_tradeable=True and csd.`is_Future_Trade` = True and cborf.symbol_name is null and ((csd.current_askPrice <= dblts.entry_price and dblts.signal_side = 'BUY') or (csd.current_bidPrice >= dblts.entry_price and dblts.signal_side = 'SELL'));
                    
SELECT * from `ant_cryptotradingbot`.`ant_user_data`;
SELECT * from `ant_cryptotradingbot`.`ant_user_wallet`;
SELECT * from `ant_cryptotradingbot`.`daily_profit_report_future`;
-- UPDATE `ant_cryptotradingbot`.`ant_user_data` set `energy_power` = 1000000 where username = 'thouship'
-- UPDATE `ant_cryptotradingbot`.`ant_user_data` set `is_tool_running` = 0 where username = 'thouship'
-- UPDATE `ant_cryptotradingbot`.`daily_profit_report_future` set `profit_amount` = 1.32,`profit_percent` = 0.44,`commission_price` = 0.1 where username = 'thouship' and `date`='2024-01-06'

SELECT * from `ant_cryptotradingbot`.`order_report_future` order by `order_seq_id` desc;
--  INSERT INTO `ant_cryptotradingbot`.`order_report_future` (`order_seq_id`,`symbol_name`,`signal_type`,`order_quantity`,`buy_price`,
--  `buy_amount`,`sell_price`,`sell_amount`,`profit_amount`,`profit_percent`,`username`,`order_date`,`update_date`,`commission_price`) 
--                     VALUES (77,'XLMUSDT','MACD - SELL',861.00,null,null,0.11595,0.11595*861.00,null,null,'thouship','2024-01-27 22:32:46',null, 0.4991);
SELECT dblts.symbol_name, dblts.signal_type, dblts.signal_side, case when dblts.signal_side = 'BUY' THEN cborf.buy_price ELSE cborf.sell_price END as entry_price, dbdt.exit_price, dbdt.stop_price, dbdt.qty_per_usdt FROM `ant_cryptotradingbot`.`db_live_trade_signals` as dblts
                            INNER JOIN `ant_cryptotradingbot`.`current_buy_order_report_future` as cborf on dblts.symbol_name = cborf.symbol_name and cborf.signal_type = concat(dblts.signal_type, ' - ', dblts.signal_side) and cborf.username = 'thouship'
                            INNER JOIN `ant_cryptotradingbot`.`db_demo_trade` as dbdt on dblts.trade_id = dbdt.trade_id
                            WHERE dblts.trade_closed=False and dbdt.exit_date is null and dbdt.symbol_name ='IOSTUSDT';

-- UPDATE `ant_cryptotradingbot`.`ant_user_wallet` set `initial_investment_spot` = 34.33,`initial_investment_future` = 281.30, `binance_exchange_usdt` = 315.53 where username = 'thouship'
-- UPDATE `ant_cryptotradingbot`.`ant_user_wallet` set `binance_exchange_usdt` = 212.5 where username = 'thouship'
-- UPDATE `ant_cryptotradingbot`.`daily_profit_report_future` set `start_amount` = 296.17 where username = 'thouship' and `date`='2024-01-04'
SELECT DISTINCT orp.symbol_name, cbor.current_price, cbor.profit_percent as current_percent, orp.order_quantity, 
            orp.buy_price, orp.buy_amount, ifnull(orp.sell_price, 0) as sell_price, ifnull(orp.sell_amount, 0) as sell_amount, 
            ifnull(cbor.target_price, 0) as target_price, ifnull(cbor.stoploss_price, 0) as stoploss_price, orp.order_date, cbor.order_seq_id
            from `ant_cryptotradingbot`.`current_buy_order_report_future` as cbor 
            inner join `ant_cryptotradingbot`.`order_report_future` as orp on cbor.symbol_name = orp.symbol_name and cbor.username = orp.username and cbor.order_date = orp.order_date
            where cbor.username = 'thouship'
            order by cbor.order_seq_id asc;
            
-- UPDATE `ant_cryptotradingbot`.`ant_user_wallet` SET `binance_exchange_usdt`=0
SELECT * FROM `ant_cryptotradingbot`.`db_live_trade_signals` WHERE symbol_name='SFPUSDT' ;
SELECT * FROM `ant_cryptotradingbot`.`crypto_symbols_data` WHERE symbol_name='LUNAUSDT' ;
SELECT * FROM `ant_cryptotradingbot`.`db_live_trade_signals` WHERE  trade_closed=False AND is_tradeable = True;
SELECT * from `ant_cryptotradingbot`.`db_telegram_trade_signals`;
-- UPDATE `ant_cryptotradingbot`.`db_telegram_trade_signals` SET trade_closed = False, is_tradeable = True
-- UPDATE `ant_cryptotradingbot`.`db_telegram_trade_signals` SET signal_side='SHORT' where signal_side=''
-- UPDATE `ant_cryptotradingbot`.`db_telegram_trade_signals` SET target_price_2=0.032204 where symbol_name='PEOPLEUSDT' and exit_date is null
-- UPDATE `ant_cryptotradingbot`.`db_live_trade_signals` SET is_tradeable = False
-- UPDATE `ant_cryptotradingbot`.`db_live_trade_signals` SET trade_id = 1144 where symbol_name='LUNAUSDT' and trade_closed=False and is_tradeable = True;
-- UPDATE `ant_cryptotradingbot`.`db_live_trade_signals` SET trade_id = 0 WHERE  trade_closed=True or is_tradeable = False;
-- UPDATE `ant_cryptotradingbot`.`db_live_trade_signals` SET entry_price = 0.7103, exit_price= 0.7150 WHERE trade_id = 1144;
SELECT * from `ant_cryptotradingbot`.`current_buy_order_report_future` ;-- 4029703141,
SELECT * from `ant_cryptotradingbot`.`order_report_future` where profit_amount is null; 
SELECT * from `ant_cryptotradingbot`.`order_report_future` order by order_seq_id desc; 
-- DELETE from `ant_cryptotradingbot`.`order_report_future` where profit_amount is null;
-- truncate table `ant_cryptotradingbot`.`current_buy_order_report_future` 
-- DELETE from `ant_cryptotradingbot`.`current_buy_order_report_future` where symbol_name='ZILUSDT';
-- DELETE from `ant_cryptotradingbot`.`order_report_future` where symbol_name='ZILUSDT' and profit_amount is null; 
-- UPDATE `ant_cryptotradingbot`.`current_buy_order_report_future` set buy_orderID=5264263572, sell_orderID=0 where order_seq_id=0
-- UPDATE `ant_cryptotradingbot`.`current_buy_order_report_future` set stop_orderID=3011406924 where order_seq_id=1
-- UPDATE `ant_cryptotradingbot`.`current_buy_order_report_future` set buy_price=0.11595 where order_seq_id=7
-- UPDATE `ant_cryptotradingbot`.`order_report_future` set sell_price=0.00721, sell_amount=0.00721*13895, commission_price=commission_price+0.05009 where s_no=107
-- UPDATE `ant_cryptotradingbot`.`order_report_future` set buy_price=0.11570, buy_amount=0.11570*861 where s_no=77
-- UPDATE `ant_cryptotradingbot`.`order_report_future` set order_quantity=282, buy_price=0.687, buy_amount=0.687*282, sell_price=0.692, sell_amount=0.692*282, commission_price=0.1 where s_no=17
-- UPDATE `ant_cryptotradingbot`.`order_report_future` set profit_amount=(sell_amount - buy_amount), profit_percent=(sell_amount - buy_amount)*20, update_date ='2024-01-27 21:39:44', sell_reason='Target Reached'  where s_no=107
-- UPDATE `ant_cryptotradingbot`.`order_report_future` set commission_price=((buy_amount / 20)/100 + (sell_amount / 20)/100)  where commission_price > 0.5
-- UPDATE `ant_cryptotradingbot`.`order_report_future` set buy_amount=buy_price*order_quantity, sell_amount=sell_price*order_quantity
-- UPDATE `ant_cryptotradingbot`.`order_report_future` set profit_percent=profit_percent*20
-- UPDATE `ant_cryptotradingbot`.`current_buy_order_report_future` set buy_price=0.09004
-- UPDATE `ant_cryptotradingbot`.`order_report_future` set update_date =order_date, sell_reason='Target Reached'  where update_date is null and profit_amount is not null

SELECT dblts.symbol_name, dblts.signal_type, dblts.signal_side, dblts.entry_price, dbdt.exit_price, dbdt.stop_price, dbdt.qty_per_usdt FROM `ant_cryptotradingbot`.`db_live_trade_signals` as dblts
                    INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_data` as csd on csd.symbol_name = dblts.symbol_name 
                    INNER JOIN `ant_cryptotradingbot`.`db_demo_trade` as dbdt on dblts.trade_id = dbdt.trade_id 
                    LEFT OUTER JOIN `ant_cryptotradingbot`.`current_buy_order_report_future` as cborf on dblts.symbol_name = cborf.symbol_name and cborf.signal_type = concat(dblts.signal_type, ' - ', dblts.signal_side) and cborf.username = '{}'
                    WHERE dblts.trade_closed=False and dblts.is_tradeable=True and csd.`is_Future_Trade` = True and cborf.symbol_name is null and ((csd.current_askPrice <= dblts.entry_price and dblts.signal_side = 'BUY') or (csd.current_bidPrice >= dblts.entry_price and dblts.signal_side = 'SELL'));

SELECT dblts.symbol_name, dblts.signal_type, dblts.signal_side, dblts.entry_price, dblts.exit_price, dblts.stop_price, dbdt.qty_per_usdt, dblts.is_tradeable FROM `ant_cryptotradingbot`.`db_live_trade_signals` as dblts
                        INNER JOIN `ant_cryptotradingbot`.`current_buy_order_report_future` as cborf on dblts.symbol_name = cborf.symbol_name and cborf.signal_type = concat(dblts.signal_type, ' - ', dblts.signal_side) and cborf.username = 'thouship'
                        INNER JOIN `ant_cryptotradingbot`.`db_demo_trade` as dbdt on dblts.trade_date = dbdt.trade_date and dblts.symbol_name = dbdt.symbol_name and dblts.signal_type = dbdt.entry_signal_type and dblts.signal_side = dbdt.signal_side 
                        WHERE dblts.trade_closed=False and dbdt.exit_date is null;

SELECT * FROM `ant_cryptotradingbot`.`current_buy_order_report_future`;

SELECT (sum(ifnull(cbor.`buy_price`,0)*cbor.`order_quantity`)  + sum(ifnull(cbor.`sell_price`,0) * cbor.`order_quantity`))/20 from `ant_cryptotradingbot`.`current_buy_order_report_future` as cbor inner join `ant_cryptotradingbot`.`order_report_future` as ort on ort.username=cbor.username and ort.symbol_name=cbor.symbol_name and (ort.`buy_price`=cbor.`buy_price` or ort.`sell_price`=cbor.`sell_price`) and ort.`order_quantity`=cbor.`order_quantity` and ort.`signal_type`=cbor.`signal_type` and ort.`order_date`=cbor.`order_date` where cbor.username = 'thouship';

select (sum(cbor.`buy_price`*cbor.`order_quantity`)  + sum(cbor.`sell_price`*cbor.`order_quantity`))/20 from `ant_cryptotradingbot`.`current_buy_order_report_future` as cbor inner join `ant_cryptotradingbot`.`order_report_future` as ort on ort.username=cbor.username and ort.symbol_name=cbor.symbol_name and (ort.`buy_price`=cbor.`buy_price` or ort.`sell_price`=cbor.`sell_price`) and ort.`order_quantity`=cbor.`order_quantity` and ort.`signal_type`=cbor.`signal_type` and ort.`order_date`=cbor.`order_date` where cbor.username = 'thouship';

(select (sum(ifnull(cbor.`buy_price`,0)*cbor.`order_quantity`)  + sum(ifnull(cbor.`sell_price`,0) * cbor.`order_quantity`))/20 from `ant_cryptotradingbot`.`current_buy_order_report_future` as cbor inner join `ant_cryptotradingbot`.`order_report_future` as ort on ort.username=cbor.username and ort.symbol_name=cbor.symbol_name and ort.`buy_price`=cbor.`buy_price`and ort.`sell_price`=cbor.`sell_price` and ort.`order_quantity`=cbor.`order_quantity` and ort.`signal_type`=cbor.`signal_type` and ort.`order_date`=cbor.`order_date` where cbor.username = 'thouship')

/*					union all
                    (select distinct auw.`initial_investment_future` as invest_amount, auw.`binance_exchange_usdt` as final_amount from `ant_cryptotradingbot`.`ant_user_wallet` as auw left join `ant_cryptotradingbot`.`order_report_future` as ort on auw.username = ort.username left join `ant_cryptotradingbot`.`order_report_future` as ortf on auw.username = ortf.username where ort.username = '{}' and (ort.sell_price is not null or (ortf.buy_price is not null and ortf.sell_price is not null)) and (((select count(buy_amount) from `ant_cryptotradingbot`.`order_report_future` where username = '{}' and sell_price is null) = 0) or (select count(buy_amount) from `ant_cryptotradingbot`.`order_report_future` where username = '{}' and not(buy_price is not null and sell_price is not null)) = 0))
                    */