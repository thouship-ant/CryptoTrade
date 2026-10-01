-- INSERT INTO `ant_cryptotradingbot`.`order_report` (`order_seq_id`,`symbol_name`,`signal_type`,`order_quantity`,`buy_price`,
   --                     `buy_amount`,`sell_price`,`sell_amount`,`profit_amount`,`profit_percent`,`username`,`order_date`,`update_date`,`commission_price`) 
     --                   VALUES (40,'SFPUSDT','MACD',143.00,0.3472,49.6496,null,null,null,null,'thouship','2022-07-21 20:04:46',null, 0.00);
                        
-- INSERT INTO `ant_cryptotradingbot`.`current_buy_order_report` (`order_seq_id`,`symbol_name`,`signal_type`,
   --                     `order_quantity`,`buy_price`,`current_price`,`profit_percent`,`target_price`,`username`,`order_date`) 
      --                  VALUES(3,'SFPUSDT','MACD',143.00,0.3472,null,null,null,'thouship','2022-07-21 20:04:46');
select * from `ant_cryptotradingbot`.`ant_user_wallet`;
-- UPDATE `ant_cryptotradingbot`.`ant_user_wallet` set `binance_exchange_usdt` = `binance_exchange_usdt`-49.6496 WHERE `username` = 'thouship';
select * from `ant_cryptotradingbot`.`ant_user_wallet`;


-- UPDATE `ant_cryptotradingbot`.`order_report` SET `sell_price`=0.3661,`sell_amount`=52.3523,`profit_amount`=2.70,`profit_percent`=5.44,`update_date`='2022-07-21 23:34:46', `sell_reason`='Target Achieved', `commission_price`=`commission_price`+0.00 
   --                     WHERE `symbol_name`='SFPUSDT' and `signal_type`='MACD' and `order_quantity`=143 and `update_date` is null and `username`='thouship';

-- DELETE FROM `ant_cryptotradingbot`.`current_buy_order_report` 
   --                     WHERE `symbol_name`='SFPUSDT' and `signal_type`='MACD' and `order_quantity`=143 and `username`='thouship';
                        
SELECT * from `ant_cryptotradingbot`.`ant_user_wallet`;
-- UPDATE `ant_cryptotradingbot`.`ant_user_wallet` set `binance_exchange_usdt` = `binance_exchange_usdt`+52.3523 WHERE `username` = 'thouship';
SELECT * from `ant_cryptotradingbot`.`ant_user_wallet`;

SELECT csn.symbol_name as symbol, replace(csn.symbol_full_name, '_', '') as symbol_full_name, csdm.order_quantity, 
(csdm.buy_amount / csdm.order_quantity) as avg_buy_price, (csdm.sell_amount / csdm.order_quantity) as avg_sell_price,
(csdm.sell_amount - csdm.buy_amount) as profit_amount, ((csdm.sell_amount - csdm.buy_amount) / (csdm.buy_amount / 100)) as profit_percent from
(SELECT csd.symbol_name as symbol_name, sum(csd.`order_quantity`) as order_quantity, sum(csd.`buy_amount`) as buy_amount, sum(csd.`sell_amount`) as sell_amount from `ant_cryptotradingbot`.`order_report` as csd
where csd.`username` = 'thouship' and csd.update_date > '2022-07-23' and csd.`sell_amount` is not null group by symbol_name) as csdm
inner join `ant_cryptotradingbot`.`crypto_symbols_name` as csn on csn.symbol_name = replace(csdm.symbol_name, 'USDT', '')
where csdm.sell_amount is not null order by csdm.symbol_name asc;

INSERT `ant_cryptotradingbot`.`crypto_symbols_name` (symbol_name, symbol_full_name) VALUES ('LEVER', '_LEVERUSDT');
SELECT csdm.symbol_name as symbol, replace(csn.symbol_full_name, '_', '') as symbol_full_name
from `ant_cryptotradingbot`.`crypto_symbols_data` as csdm
left join `ant_cryptotradingbot`.`crypto_symbols_name` as csn on csn.symbol_name = replace(csdm.symbol_name, 'USDT', '')
where csn.symbol_name is null;