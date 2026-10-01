(select distinct auw.`initial_investment` as invest_amount, (auw.`binance_exchange_usdt`+(select sum(`buy_price`*`order_quantity`) from `ant_cryptotradingbot`.`current_buy_order_report` where username = 'Admin')) as final_amount from `ant_cryptotradingbot`.`order_report` as ort inner join `ant_cryptotradingbot`.`current_buy_order_report` as cort on cort.username = ort.username inner join `ant_cryptotradingbot`.`ant_user_wallet` as auw on auw.username = ort.username where ort.username = 'Admin' and ort.sell_price is null)
                union all
				(select distinct auw.`initial_investment` as invest_amount, auw.`binance_exchange_usdt` as final_amount from `ant_cryptotradingbot`.`order_report` as ort inner join `ant_cryptotradingbot`.`ant_user_wallet` as auw on auw.username = ort.username where ort.username = 'Admin' and ort.sell_price is not null
                 and (select count(buy_amount) from `ant_cryptotradingbot`.`order_report` where username = 'Admin' and sell_price is null) = 0)
                union all
                (select sum(profit_amount - commission_price) as invest_amount, sum(profit_percent) as final_amount from `ant_cryptotradingbot`.`daily_profit_report` where username = 'Admin')
                union all
                (select sum(profit_amount - commission_price) as invest_amount, sum(profit_percent) as final_amount from `ant_cryptotradingbot`.`daily_profit_report` where username = 'Admin' and `date` >= '2022-07-01')
                union all
                (select sum(profit_amount - commission_price) as invest_amount, sum(profit_percent) as final_amount from `ant_cryptotradingbot`.`daily_profit_report` where username = 'Admin' and `date` = '2022-07-21')
;                
                
                
                
ALTER TABLE `ant_cryptotradingbot`.`ant_user_data` ADD `level_tree` bigint NOT NULL default 2;
ALTER TABLE `ant_cryptotradingbot`.`ant_user_data` ADD `display_mode` varchar(50) NOT NULL default 'light-mode';

ALTER TABLE `ant_cryptotradingbot`.`ant_user_data` ADD `single_trade_amount` bigint NOT NULL default 50;

ALTER TABLE `ant_cryptotradingbot`.`ant_user_data` ADD `current_plan` varchar(50) NOT NULL default '';
ALTER TABLE `ant_cryptotradingbot`.`ant_user_data` ADD `max_trade` bigint NOT NULL default 0;

ALTER TABLE `ant_cryptotradingbot`.`ant_user_wallet` MODIFY `level_share_income` DECIMAL(8, 2) NOT NULL default 0.00;
ALTER TABLE `ant_cryptotradingbot`.`current_buy_order_report` ADD `stoploss_percent` DECIMAL(8, 2) NULL;

ALTER TABLE `ant_cryptotradingbot`.`ant_user_data` ADD `max_trade` bigint NOT NULL default 0;
ALTER TABLE `ant_cryptotradingbot`.`current_buy_order_report` ADD `buy_orderID` bigint NOT NULL default 0;
ALTER TABLE `ant_cryptotradingbot`.`current_buy_order_report` ADD `sell_orderID` bigint NOT NULL default 0;
ALTER TABLE `ant_cryptotradingbot`.`current_buy_order_report` ADD `sell_orderDate` datetime NULL;

select * from `ant_cryptotradingbot`.`ant_user_data`;

select `single_trade_amount` from `ant_cryptotradingbot`.`ant_user_data` where `username`='';

-- update `ant_cryptotradingbot`.`ant_user_wallet` set total_deposit=100  where username='najik';

-- update `ant_cryptotradingbot`.`ant_user_data` set level_tree=1 where user_id=1;
-- update `ant_cryptotradingbot`.`ant_user_data` set referal_code='nasira_ant#2' where user_id=3;

-- update `ant_cryptotradingbot`.`ant_user_data` set referal_code=replace(referal_code, '#', '_'), referal_by=replace(referal_by, '#', '_') where user_id=3;

-- update `ant_cryptotradingbot`.`ant_user_data` set referal_code='periasamy_ant_3', level_tree=3 where user_id=9;

-- update `ant_cryptotradingbot`.`ant_user_data` set referal_by='thouship_ant#2' where user_id=4;

-- update `ant_cryptotradingbot`.`ant_user_data` set level_tree=3 where user_id=4;

-- update `ant_cryptotradingbot`.`crypto_symbols_name` set symbol_full_name='Celer Network' where symbol_name='CELR';
