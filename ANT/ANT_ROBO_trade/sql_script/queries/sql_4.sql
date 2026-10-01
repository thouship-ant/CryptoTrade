select bcsd.order_date as 'Date', 'Buy' as side, concat('Bought ', bcsn.symbol_full_name) as activity, bcsd.signal_type as 'type', concat(FLOOR(bcsd.order_quantity), ' ', bcsn.symbol_name) as quantity, concat(bcsd.buy_amount, ' USDT') as amount from `ant_cryptotradingbot`.`order_report`  as bcsd
inner join `ant_cryptotradingbot`.`crypto_symbols_name` as bcsn on bcsn.symbol_name = replace(bcsd.symbol_name, 'USDT', '')
union all
select csd.update_date as 'Date', 'Sell' as side, concat('Sell ', csn.symbol_full_name) as activity, csd.sell_reason as 'type', concat(FLOOR(csd.order_quantity), ' ', csn.symbol_name) as quantity, concat(csd.sell_amount, ' USDT') as amount from `ant_cryptotradingbot`.`order_report`  as csd
inner join `ant_cryptotradingbot`.`crypto_symbols_name` as csn on csn.symbol_name = replace(csd.symbol_name, 'USDT', '')
order by `Date` desc;


select cast(`Date` as Date) as 'Date', side, activity, quantity, amount from (
select bcsd.order_date as 'Date', 'Buy' as side, concat('Bought ', replace(bcsn.symbol_full_name, '_', '')) as activity, bcsd.signal_type as 'type', concat(FLOOR(bcsd.order_quantity), ' ', bcsn.symbol_name) as quantity, concat(bcsd.buy_amount, ' USDT') as amount from `ant_cryptotradingbot`.`order_report`  as bcsd
inner join `ant_cryptotradingbot`.`crypto_symbols_name` as bcsn on bcsn.symbol_name = replace(bcsd.symbol_name, 'USDT', '')
where bcsd.username = 'Admin' and bcsd.order_date >= '2022-07-01' and bcsd.order_date < '2022-07-07'
union all
select csd.update_date as 'Date', 'Sell' as side, concat('Sell ', replace(csn.symbol_full_name, '_', '')) as activity, csd.sell_reason as 'type', concat(FLOOR(csd.order_quantity), ' ', csn.symbol_name) as quantity, concat(csd.sell_amount, ' USDT') as amount from `ant_cryptotradingbot`.`order_report`  as csd
inner join `ant_cryptotradingbot`.`crypto_symbols_name` as csn on csn.symbol_name = replace(csd.symbol_name, 'USDT', '')
where csd.username = 'Admin' and csd.order_date >= '2022-07-01' and csd.order_date < '2022-07-07'
order by `Date` desc) as cte;


call `ant_cryptotradingbot`.`user_recent_activity`('thouship', '2022-07-28', '2022-07-29');

-- update `ant_cryptotradingbot`.`ant_user_data` set full_name = 'Naseera Fathima' where username='nasira';
-- update `ant_cryptotradingbot`.`ant_user_wallet` set activation_balance = 100  where username='nasira';
-- update `ant_cryptotradingbot`.`ant_user_data` set referal_by='thouship_ant#2', validity_status='configured', current_plan = '', energy_power=0 where username='nasira';

-- delete from `ant_cryptotradingbot`.`transaction_history` where s_no > 2;

-- Update `ant_cryptotradingbot`.`ant_user_wallet` set `ant_wallet_balance`=0, `referal_income`=0
--                                     WHERE `username` = 'Admin'