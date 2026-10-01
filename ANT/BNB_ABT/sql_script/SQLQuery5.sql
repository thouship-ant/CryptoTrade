-- truncate table `ant_cryptotradingbot`.`db_demo_trade`
SELECT * FROM `ant_cryptotradingbot`.`crypto_symbols_data` where is_Margin_Trade = True ;

call `ant_cryptotradingbot`.`db_signal_query_entry`(null);
call `ant_cryptotradingbot`.`db_signal_query_exit`(3282, 'VTHOUSDT');

call `ant_cryptotradingbot`.`gen_dailywise_future_trade_report`();

SELECT dblts.symbol_name, dblts.signal_type, dblts.signal_side, dblts.entry_price, dbdt.exit_price, dbdt.stop_price, dbdt.qty_per_usdt, dblts.trade_id 
					FROM `ant_cryptotradingbot`.`db_live_trade_signals` as dblts
                    INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_data` as csd on csd.symbol_name = dblts.symbol_name 
                    INNER JOIN `ant_cryptotradingbot`.`db_demo_trade` as dbdt on dblts.trade_id = dbdt.trade_id 
                    LEFT OUTER JOIN `ant_cryptotradingbot`.`current_buy_order_report_future` as cborf on dblts.symbol_name = cborf.symbol_name and cborf.signal_type = concat(dblts.signal_type, ' - ', dblts.signal_side) and cborf.username = 'thouship'
                    WHERE dblts.trade_closed=False and dblts.is_tradeable=True and csd.`is_Future_Trade` = True and cborf.symbol_name is null and (((csd.current_askPrice <= dblts.entry_price or csd.price_breakOut = 1) and dblts.signal_side = 'BUY') or ((csd.current_bidPrice >= dblts.entry_price or csd.price_breakOut = -1) and dblts.signal_side = 'SELL'));

SELECT * FROM `ant_cryptotradingbot`.`db_query_data`;

SELECT csd.`symbol_name`, csd.`current_bidPrice`, csema.ema_7 as `entry_price`, 'TELEGRAM' as `signal_type`, 'SELL' as `signal_side`, csd.`is_Margin_Trade`, csd.`last_update_DateTime` as `update_datetime` 
	FROM `ant_cryptotradingbot`.`db_telegram_trade_signals` as dtts
    INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_data` as csd on csd.symbol_name = dtts.symbol_name
	INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_ema_data` as csema on csd.symbol_name = csema.symbol_name 
	WHERE csd.is_Active = True and csd.is_Margin_Trade = True and csd.price_breakOut = -1 
    and dtts.trade_id = 0 and  dtts.trade_closed=False and dtts.is_tradeable=True and dtts.signal_side = 'SHORT'

SELECT * FROM `ant_cryptotradingbot`.`db_telegram_trade_signals` as dtts
    INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_data` as csd on csd.symbol_name = dtts.symbol_name
WHERE csd.is_Active = True and csd.is_Margin_Trade = True 
    and dtts.trade_id = 0  and dtts.trade_closed=False and dtts.is_tradeable=True and dtts.signal_side = 'SHORT'


-- DELETE FROM `ant_cryptotradingbot`.`db_demo_trade` where `exit_date` is null
-- DELETE FROM `ant_cryptotradingbot`.`db_demo_trade` where `entry_date` is not null and `exit_date` is null 
-- where `exit_price` is null and `trade_date`='2023-12-26';

-- UPDATE `ant_cryptotradingbot`.`db_demo_trade` SET `entry_date`='2023-12-28 00:00:00' , `qty_per_usdt`=(1/`entry_price`) where `entry_date` is null and `exit_date` is not null 
SELECT `trade_date`,csd.`symbol_name`,`entry_signal_type`,`signal_side`,qty_per_usdt,csd.current_bidPrice,`entry_price`,`exit_price`,`entry_date` FROM `ant_cryptotradingbot`.`db_demo_trade` as dbdt 
INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_data` as csd on csd.symbol_name = dbdt.symbol_name 
where `entry_date` is not null and exit_date is null
ORDER BY `trade_id`;

SELECT `trade_date`,sum(profit)  as `profit` from (
SELECT `trade_date`,csd.`symbol_name`,`entry_signal_type`,`signal_side`,csd.current_bidPrice,`entry_price`,`exit_price`,
qty_per_usdt * (CASE WHEN dbdt.signal_side = 'BUY' THEN (csd.current_bidPrice - `entry_price`)
ELSE (`entry_price` - csd.current_askPrice) END) as `profit`
 FROM `ant_cryptotradingbot`.`db_demo_trade` as dbdt 
INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_data` as csd on csd.symbol_name = dbdt.symbol_name 
where `entry_date` >= '2024-01-06 16:30:00'
) as t
group by `trade_date`

ORDER BY `trade_id` asc;
`entry_date` is not null and `exit_date` is null
 and `trade_date`='2024-01-02'
ORDER BY `entry_date` desc;

SELECT `trade_id`,`trade_date`,`symbol_name`,`entry_signal_type`,`signal_side`,`entry_price`,`entry_date`,`exit_price` FROM `ant_cryptotradingbot`.`db_demo_trade` where `exit_date` is null;

-- UPDATE `ant_cryptotradingbot`.`db_demo_trade` set `pnl_per_usdt`= (CASE WHEN signal_side = 'BUY' THEN exit_price - entry_price ELSE entry_price - exit_price END) * qty_per_usdt, `exit_signal_type`=`entry_signal_type`,`exit_date`='2024-03-20 00:00:00'
-- where `trade_date`='2024-03-17' and `exit_date` is not null;

-- UPDATE `ant_cryptotradingbot`.`db_demo_trade` set `pnl_per_usdt`= (CASE WHEN signal_side = 'BUY' THEN exit_price - entry_price ELSE entry_price - exit_price END) * qty_per_usdt, `exit_signal_type`=`entry_signal_type`,`exit_date`='2024-03-20 00:00:00'
-- where `trade_date`='2024-03-19' and `exit_date` is null;

-- UPDATE `ant_cryptotradingbot`.`db_demo_trade` set `pnl_per_usdt`= null, `exit_signal_type`=null,`exit_date`=null
-- where `trade_date`='2024-03-19' and `exit_date` = '2024-03-20 00:00:00' and symbol_name in ('RENUSDT','MANAUSDT','LITUSDT','CHZUSDT','CELOUSDT','C98USDT');

SELECT `trade_id`,`trade_date`,`symbol_name`,`entry_signal_type`,`signal_side`,`entry_price`,`entry_date`,`exit_price` FROM `ant_cryptotradingbot`.`db_demo_trade` 
where `trade_date`='2024-03-18' and `exit_date` = '2024-03-20 00:00:00' and symbol_name in ('DGBUSDT');
-- DGBUSDT
-- DELETE FROM `ant_cryptotradingbot`.`db_demo_trade`
-- -- where `pnl_per_usdt` is not null 
-- -- order by trade_id desc
-- where `exit_date` is null 
-- and `trade_date`='2024-01-05';

call `ant_cryptotradingbot`.`db_signal_query_entry`(null)

SELECT * FROM `ant_cryptotradingbot`.`db_live_trade_signals` where `trade_date`='2024-01-04' and `symbol_name`='JASMYUSDT' and 
                    `signal_type`='MACD' and `signal_side`='BUY' and `entry_price`=0.005835 and `trade_closed` = False and `is_tradeable` = True;

SELECT * FROM `ant_cryptotradingbot`.`db_demo_trade` as dbdt
where dbdt.`entry_date` is null and dbdt.`exit_date` is null
and `trade_date`='2024-01-07';

SELECT * FROM `ant_cryptotradingbot`.`db_demo_trade` as dbdt
where dbdt.`entry_date` is not null and dbdt.`exit_date` is null
and `trade_date`='2023-12-31';

SELECT * from `ant_cryptotradingbot`.`order_report_future` as orf
inner join `ant_cryptotradingbot`.`db_live_trade_signals` as lts on lts.symbol_name = orf.symbol_name   and lts.entry_price = case when lts.signal_side = 'BUY' then orf.buy_price else orf.sell_price end
inner join `ant_cryptotradingbot`.`db_demo_trade` as dbdt on dbdt.trade_id = lts.trade_id
where date(order_date) = dbdt.trade_date;

-- UPDATE `ant_cryptotradingbot`.`db_demo_trade` set exit_signal_type = entry_signal_type, entry_price = 0.65600000, exit_price = 0.65700000,  pnl_per_usdt = 0.15/5,  exit_date = '2024-01-20 00:53:20'  where trade_id=1576;
-- UPDATE `ant_cryptotradingbot`.`db_demo_trade` set exit_signal_type = entry_signal_type, entry_price = 0.61370000, exit_price = 0.61540000,  pnl_per_usdt = 0.28/5,  exit_date = '2024-01-20 01:23:07'  where trade_id=1578;
-- UPDATE `ant_cryptotradingbot`.`db_demo_trade` set exit_signal_type = entry_signal_type, entry_price = 0.04661000, exit_price = 0.04670000,  pnl_per_usdt = 0.19/5,  exit_date = '2024-01-20 02:02:37'  where trade_id=1582;
-- UPDATE `ant_cryptotradingbot`.`db_demo_trade` set exit_signal_type = entry_signal_type, entry_price = 0.31870000, exit_price = 0.32170000,  pnl_per_usdt = 0.94/5,  exit_date = '2024-01-23 02:35:35'  where trade_id=1680;
-- UPDATE `ant_cryptotradingbot`.`db_demo_trade` set exit_signal_type = entry_signal_type, entry_price = 0.00049560, exit_price = 0.00050050,  pnl_per_usdt = 0.99/5,  exit_date = '2024-01-25 02:51:24'  where trade_id=1679;

-- UPDATE `ant_cryptotradingbot`.`db_demo_trade` set pnl_per_usdt = pnl_per_usdt/100  where trade_id >= 1679 and pnl_per_usdt is not null;

SELECT * FROM `ant_cryptotradingbot`.`db_demo_trade` as dbdt
-- where dbdt.`exit_date` is null
order by `trade_id` desc
-- DELETE FROM `ant_cryptotradingbot`.`db_demo_trade` WHERE `exit_date` is null and trade_id != 1685 and `trade_date`='2024-01-21';
-- DELETE FROM `ant_cryptotradingbot`.`db_demo_trade` WHERE `entry_date` is null and `exit_date` is null
-- DELETE FROM `ant_cryptotradingbot`.`db_demo_trade` WHERE `entry_date` is not null and `exit_date` is null and symbol_name = 'ARPAUSDT'
-- UPDATE `ant_cryptotradingbot`.`crypto_symbols_ema_data` set ema_200 = 0.3852 where symbol_name='ONGUSDT'
-- UPDATE `ant_cryptotradingbot`.`db_demo_trade` set exit_price = 0.3852 where symbol_name='ONGUSDT' and exit_date is null
-- UPDATE `ant_cryptotradingbot`.`db_demo_trade` set entry_price = 0.009070 where symbol_name='IOSTUSDT' and exit_date is null

-- DELETE FROM `ant_cryptotradingbot`.`db_demo_trade` WHERE `trade_id` = 298

DELETE FROM `ant_cryptotradingbot`.`db_demo_trade`
where `exit_date` is null and `trade_date`='2024-01-10';

SELECT `trade_id` FROM `ant_cryptotradingbot`.`db_demo_trade` order by `trade_id` desc limit 1;

SELECT * FROM `ant_cryptotradingbot`.`crypto_symbols_ema_data` where symbol_name = 'XRPUSDT'
AND ema_200 > ema_25 > ema_7;

SELECT `signal_side`, `entry_price` FROM `ant_cryptotradingbot`.`db_demo_trade` where `exit_date` is null;


SELECT DISTINCT dbdt.`symbol_name`, csema.ema_7 FROM `ant_cryptotradingbot`.`db_demo_trade` as dbdt
                        INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_data` as csd on dbdt.symbol_name = csd.symbol_name 
                        INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_ema_data` as csema on dbdt.symbol_name = csema.symbol_name 
                        WHERE ((dbdt.signal_side = 'BUY' and csema.ema_7 < csd.current_askPrice and csd.MACD_macd > 0  
                        and ((csd.MACD_dem < 0 and csd.MACD_dif > 0) or ((csema.ema_200 < csema.ema_7 and (csema.ema_200 > csema.ema_25 or csema.ema_200 > csema.ema_99)) or 
                        (csema.ema_7 > csema.ema_25 and ((csema.ema_7 < csema.ema_99 and  csema.ema_7 < csema.ema_200) or csema.ema_7 < csema.ema_200)))))
                        or (dbdt.signal_side = 'SELL' and csema.ema_7 > csd.current_bidPrice and csd.MACD_macd < 0 
                        and ((csd.MACD_dem > 0 and csd.MACD_dif < 0) or ((csema.ema_200 > csema.ema_7 and (csema.ema_200 > csema.ema_25 or csema.ema_200 > csema.ema_99)) or 
                        (csema.ema_7 > csema.ema_25 and ((csema.ema_7 < csema.ema_99 and csema.ema_7 < csema.ema_200) or csema.ema_7 < csema.ema_200))))))
						and dbdt.`entry_date` is null and dbdt.`exit_date` is null
 
-- UPDATE `ant_cryptotradingbot`.`db_demo_trade` SET `stop_price`=`exit_price` where `entry_date` is not null and `exit_date` is not null 
