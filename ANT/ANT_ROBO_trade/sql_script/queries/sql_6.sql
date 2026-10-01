SELECT orp.symbol_name, cbor.current_price, cbor.profit_percent as current_percent, orp.order_quantity, 
            orp.buy_price, orp.buy_amount, ifnull(orp.sell_price, 0) as sell_price, ifnull(orp.sell_amount, 0) as sell_amount, 
            ifnull(cbor.target_price, 0) as target_price, ifnull(cbor.stoploss_price, 0) as stoploss_price, orp.order_date
            from `ant_cryptotradingbot`.`order_report` as orp
            left join `ant_cryptotradingbot`.`current_buy_order_report` as cbor on cbor.symbol_name = orp.symbol_name and cbor.username = orp.username
            where orp.username = 'thouship'
            order by orp.order_seq_id desc limit 1;
            
-- update 
-- INSERT INTO `ant_cryptotradingbot`.`current_buy_order_report` (`order_seq_id`,`symbol_name`,`signal_type`,
     --                       `order_quantity`,`buy_price`,`current_price`,`profit_percent`,`target_price`,`username`,`order_date`) 
       --                     VALUES(3,'ASTRUSDT','MACD',1126.00,0.04460000,null,null,null,'Admin','2022-07-23 01:01:37');
            
-- UPDATE `ant_cryptotradingbot`.`current_buy_order_report` SET `order_quantity`=931,`buy_price`=0.107011 ,`order_date`='2022-07-24 00:22:23' 
--                             WHERE `symbol_name`='COTIUSDT' and `signal_type`='MACD' and `username`='Admin';
-- UPDATE `ant_cryptotradingbot`.`order_report` SET `order_quantity`=931,`buy_price`=0.107011,`buy_amount`=99.6268,
--                             `order_date`='2022-07-24 00:22:23',`commission_price`=`commission_price`+0.000 
--                             WHERE `username`='Admin' and `symbol_name`='COTIUSDT' and `signal_type`='MACD' and `sell_amount` is null;
                            
SELECT 22.52+sum(`buy_price`*`order_quantity`) FROM `ant_cryptotradingbot`.`current_buy_order_report` WHERE `username`='Admin';
select * from `ant_cryptotradingbot`.`current_buy_order_report` WHERE `username`='Admin' order by order_seq_id asc;
-- delete from `ant_cryptotradingbot`.`current_buy_order_report` where order_seq_id=5 and `username`='Admin';
-- update `ant_cryptotradingbot`.`current_buy_order_report` set order_seq_id=order_seq_id-2 where `username`='thouship';
select * from `ant_cryptotradingbot`.`order_report`
 WHERE `username`='Admin' order by s_no desc
;
-- delete from `ant_cryptotradingbot`.`order_report` where s_no=456;


select cbor.* from `ant_cryptotradingbot`.`current_buy_order_report` as cbor 
left join `ant_cryptotradingbot`.`order_report` as ort on ort.symbol_name = cbor.symbol_name 
and ort.signal_type = cbor.signal_type and ort.order_quantity = cbor.order_quantity 
and ort.buy_price = cbor.buy_price and ort.order_date = cbor.order_date and ort.username = cbor.username
where ort.buy_amount is null and cbor.username = 'thouship';

-- delete from `ant_cryptotradingbot`.`current_buy_order_report` where symbol_name = 'REIUSDT' and username = 'thouship';

select cbor.symbol_name, cbor.signal_type, cbor.order_quantity, cbor.buy_price, cbor.order_date 
from `ant_cryptotradingbot`.`current_buy_order_report` as cbor 
inner join `ant_cryptotradingbot`.`order_report` as ort on ort.symbol_name = cbor.symbol_name 
and ort.signal_type = cbor.signal_type and ort.order_quantity = cbor.order_quantity 
and ort.buy_price = cbor.buy_price and ort.order_date = cbor.order_date and ort.username = cbor.username
where ort.sell_amount is null and ort.sell_price is not null and cbor.username = 'Admin';

update `ant_cryptotradingbot`.`order_report` set sell_price = null 
where symbol_name = '{}' and signal_type = '{}' and order_quantity = {} 
and buy_price = {} and order_date = '{}' and username = '{}';

select * from `ant_cryptotradingbot`.`bnb_report`;


select * from `ant_cryptotradingbot`.`daily_profit_report` where `username` = 'Admin' order by `date` desc;
select * from `ant_cryptotradingbot`.`daily_profit_report` where `username` = 'thouship' order by `date` desc;
select * from `ant_cryptotradingbot`.`daily_profit_report` where `username` = 'najik' order by `date` desc;
-- update `ant_cryptotradingbot`.`daily_profit_report` set start_amount=570.1600, end_amount=570.1600+1.52 where `username` = 'Admin' and `date` = '2022-08-25';
