SELECT csn.symbol_name, csn.symbol_full_name, csd.`current_askPrice` from `ant_cryptotradingbot`.`crypto_symbols_data` as csd
inner join `ant_cryptotradingbot`.`crypto_symbols_name` as csn on csn.symbol_name = replace(csd.symbol_name, 'USDT', '');

-- INSERT `ant_cryptotradingbot`.`crypto_symbols_name` (symbol_name, symbol_full_name) (
-- SELECT symbol_name, concat('_',symbol_name) as symbol_full_name from `ant_cryptotradingbot`.`crypto_symbols_data`
-- where symbol_name not in (
SELECT csd.symbol_name from `ant_cryptotradingbot`.`crypto_symbols_data` as csd
inner join `ant_cryptotradingbot`.`crypto_symbols_name` as csn on csn.symbol_name = replace(csd.symbol_name, 'USDT', '');
-- );
SELECT count(*) FROM `ant_cryptotradingbot`.`ant_user_wallet` where `username` = '{}';

-- update `ant_cryptotradingbot`.`ant_user_data` set `validity_status`='register', `exchange_name` = '', `api_key` = '', `api_secret`='', max_invest=0 where username='nasira';
-- INSERT `ant_cryptotradingbot`.`ant_user_wallet` (`username`, `initial_investment`, `binance_exchange_usdt`) VALUES ('Admin', 300.69, 428.46);
-- update `ant_cryptotradingbot`.`ant_user_data` set `single_trade_amount`=15 where username='najik';

-- UPDATE `ant_cryptotradingbot`.`ant_user_wallet` set `binance_exchange_usdt` = `binance_exchange_usdt`-49.91 WHERE `username` = 'thouship';
-- UPDATE `ant_cryptotradingbot`.`ant_user_wallet` set `initial_investment` = 268 WHERE `username` = 'thouship';
-- update `ant_cryptotradingbot`.`order_report` set commission_price = 'Stop loss hit' where s_no = 0;
select 375.08-50.2196;
SELECT symbol_name, symbol_full_name from `ant_cryptotradingbot`.`crypto_symbols_name` 
where symbol_name in ('BTC', 'ETH', 'LTC', 'BNB', 'DASH', 'USDT', 'NEO');

select * from `ant_cryptotradingbot`.`current_buy_order_report` 
-- where symbol_name = 'FRONTUSDT' and username='thouship' -- and update_date < '2022-07-19'
where username='thouship' 
order by username, order_date asc
;

	select * from `ant_cryptotradingbot`.`order_report` 
	-- where symbol_name = 'FRONTUSDT' and username='thouship' -- and update_date < '2022-07-19'
	-- where sell_reason is null
 where username='thouship' and sell_reason is null
-- 	order by s_no desc
 order by  order_date desc
;
-- 268.2365

-- INSERT INTO `ant_cryptotradingbot`.`current_buy_order_report` (`order_seq_id`,`symbol_name`,`signal_type`,`order_quantity`,`buy_price`,`current_price`,`profit_percent`,`target_price`,`username`,`order_date`) 
-- VALUES(4,'WINUSDT','MACD',753855.00,0.00013265,null,null,null,'Admin','2022-09-02 18:10:41');
-- INSERT INTO `ant_cryptotradingbot`.`order_report` (`order_seq_id`,`symbol_name`,`signal_type`,`order_quantity`,`buy_price`,
--                        `buy_amount`,`sell_price`,`sell_amount`,`profit_amount`,`profit_percent`,`username`,`order_date`,`update_date`,`commission_price`) 
--                        VALUES (128,'VIDTUSDT','MACD',185.00,0.26980000,49.913,null,null,null,null,'thouship','2022-09-06 10:43:04',null, 0.00);
-- update `ant_cryptotradingbot`.`current_buy_order_report` set buy_orderid = 0 where username='thouship' and order_seq_id = 1;
-- update `ant_cryptotradingbot`.`current_buy_order_report` set sell_orderid = 0 , sell_orderdate = null where username='thouship' and order_seq_id = 2;

-- INSERT INTO `ant_cryptotradingbot`.`current_buy_order_report` (`order_seq_id`,`symbol_name`,`signal_type`,`order_quantity`,`buy_price`,`current_price`,`profit_percent`,`target_price`,`username`,`order_date`) 
-- VALUES(2,'ICXUSDT','MACD',146.00,0.34300000,null,null,null,'Admin','2022-08-09 09:21:31');

-- update `ant_cryptotradingbot`.`current_buy_order_report` set buy_price = 0.06749000 where username='Admin' and order_seq_id = 5;
-- update `ant_cryptotradingbot`.`current_buy_order_report` set order_quantity= 149.00, buy_price = 0.33450000, order_date='2022-07-31 23:44:36' where username='najik' and symbol_name = 'FRONTUSDT';
-- update `ant_cryptotradingbot`.`current_buy_order_report` set order_quantity= 445, buy_price = 0.22450000, order_date='2022-09-14 08:45:40' where username='thouship' and order_seq_id = 1;
-- update `ant_cryptotradingbot`.`order_report` set order_quantity= 445, buy_price = 0.22450000, buy_amount = 99.8839, order_date='2022-09-14 08:45:40' where username='thouship' and order_seq_id = 172;

-- update `ant_cryptotradingbot`.`order_report` set sell_price=0.00388100, sell_amount= 50.6781, profit_amount = 0.67, profit_percent= 1.35, update_date='2022-09-09 06:38:09' , sell_reason='Target Acheived', commission_price=(0 + commission_price) where s_no=740;
-- update `ant_cryptotradingbot`.`order_report` set sell_price=0.12890000, sell_amount= 50.9155, profit_amount = 0.79, profit_percent= 1.58, update_date='2022-08-10 12:51:09' , sell_reason='RSI - Overbought', commission_price=(0 + commission_price) where s_no=623;
-- 50.945+50.9155
-- update `ant_cryptotradingbot`.`order_report` set sell_price = 0.7313, sell_amount= 291.2166, profit_amount = 3.34, profit_percent= 1.10, update_date='2022-07-15 18:37:39' , sell_reason='RSI - Overbought', commission_price=(0.218104 + commission_price) where s_no=381;
-- update `ant_cryptotradingbot`.`order_report` set sell_price = 0.00508, sell_amount= 51.0032, profit_amount = 1.00, profit_percent= 2, update_date='2022-07-27 17:17:55' , sell_reason='Target Achieved', commission_price=(0 + commission_price) where s_no=448;

-- update `ant_cryptotradingbot`.`order_report` set sell_price = null where username='thouship' and s_no = 778;
-- delete from `ant_cryptotradingbot`.`current_buy_order_report` where order_seq_id = 3 and username = 'thouship'
-- delete from `ant_cryptotradingbot`.`order_report` where buy_price = sell_price and username = 'thouship'
-- delete from `ant_cryptotradingbot`.`order_report` where s_no = 823 and username = 'thouship'

select * from `ant_cryptotradingbot`.`ant_user_wallet`;
select * from `ant_cryptotradingbot`.`ant_user_data`;

-- update `ant_cryptotradingbot`.`ant_user_data` set energy_power = energy_power-24 where username='thouship'
-- update `ant_cryptotradingbot`.`ant_user_data` set max_invest = 1000 where user_id=4
-- 49.8480
select * from `ant_cryptotradingbot`.`order_report` where username='thouship' and update_date  is null;-- update_date >= '2022-07-08' and update_date <= concat('2022-08-01', ' 23:59:59');
-- update `ant_cryptotradingbot`.`order_report` set sell_price = null where username='thouship' and update_date  is null;
SELECT * FROM `ant_cryptotradingbot`.`crypto_symbols_name` where symbol_full_name like '_%';
-- UPDATE `ant_cryptotradingbot`.`crypto_symbols_name` set symbol_full_name='_LEVER' where symbol_full_name='_LEVERUSDT';
select SUM(Volume) as Volume from `ant_cryptotradingbot`.`acausdt` limit 96 offset 384;

SELECT concat(csn.symbol_name, '-', replace(csn.symbol_full_name, '_', '')) as symbols, csd.`current_askPrice`, csd.`24hrs_price_change`, csd.`24hrs_change`, csd.`Volumes` from `ant_cryptotradingbot`.`crypto_symbols_data` as csd
inner join `ant_cryptotradingbot`.`crypto_symbols_name` as csn on csn.symbol_name = replace(csd.symbol_name, 'USDT', '')
where csd.is_Active = true;

ALTER TABLE `ant_cryptotradingbot`.`ant_user_data` ADD `current_plan` varchar(50) NOT NULL default '';
ALTER TABLE `ant_cryptotradingbot`.`ant_user_data` ADD `valid_days_left` bigint NOT NULL default 0;
ALTER TABLE `ant_cryptotradingbot`.`ant_user_data` ADD `energy_power` bigint NOT NULL default 0;

-- Update `ant_cryptotradingbot`.`ant_user_data` set energy_power=5000000 where user_id=1;
-- Update `ant_cryptotradingbot`.`ant_user_data` set energy_power=1000000 where user_id=2;
-- Update `ant_cryptotradingbot`.`ant_user_data` set energy_power=1000000 where user_id=4;
-- Update `ant_cryptotradingbot`.`ant_user_data` set current_plan='5year' where user_id=1;
-- Update `ant_cryptotradingbot`.`ant_user_data` set current_plan='1year' where user_id=2;
-- Update `ant_cryptotradingbot`.`ant_user_wallet` set activation_balance=135 where wallet_seq_id=4;
-- Update `ant_cryptotradingbot`.`transaction_history` set `amount`=100  where s_no=1;
-- Update `ant_cryptotradingbot`.`transaction_history` set `to`='ANTBot',`details`='ANTBot_1MP', `amount`=-100  where s_no=2;
select * from `ant_cryptotradingbot`.`transaction_history`;

-- Update `ant_cryptotradingbot`.`ant_user_data` set validity='2022-04-02 10:15:00' where user_id=1;
-- Update `ant_cryptotradingbot`.`ant_user_data` set validity='2022-06-01 15:10:00' where user_id=2;
-- Update `ant_cryptotradingbot`.`ant_user_data` set validity=null where user_id=3;
-- Update `ant_cryptotradingbot`.`ant_user_data` set validity='2022-07-30 23:59:59' where user_id=4;

select * from `ant_cryptotradingbot`.`ant_user_data`;

-- Update `ant_cryptotradingbot`.`current_buy_order_report` set sell_orderID=0, sell_orderDate=null;
