-- Update `ant_cryptotradingbot`.`ant_user_data` set `current_plan`='5MP', energy_power=5000000 where user_id=1;
-- Update `ant_cryptotradingbot`.`ant_user_data` set `current_plan`='1MP', energy_power=1000000 where user_id=2;
-- Update `ant_cryptotradingbot`.`ant_user_data` set `current_plan`='1MP', energy_power=1000000 where user_id=4;

-- Update `ant_cryptotradingbot`.`ant_user_data` set energy_power=(energy_power-(207.99*30)) where user_id=1;
-- Update `ant_cryptotradingbot`.`ant_user_data` set energy_power=(energy_power-(43.55*30)) where user_id=2;
-- Update `ant_cryptotradingbot`.`ant_user_data` set energy_power=(energy_power-(7.23*30)) where user_id=4;


(select distinct auw.`initial_investment` as invest_amount, (auw.`binance_exchange_usdt`+ifnull((select sum(cbor.`buy_price`*cbor.`order_quantity`) from `ant_cryptotradingbot`.`current_buy_order_report` as cbor inner join `ant_cryptotradingbot`.`order_report` as ort on ort.username=cbor.username and ort.symbol_name=cbor.symbol_name and ort.`buy_price`=cbor.`buy_price` and ort.`order_quantity`=cbor.`order_quantity` and ort.`signal_type`=cbor.`signal_type` and ort.`order_date`=cbor.`order_date` where cbor.username = 'Admin'), 0)) as final_amount from `ant_cryptotradingbot`.`order_report` as ort inner join `ant_cryptotradingbot`.`current_buy_order_report` as cort on cort.username = ort.username inner join `ant_cryptotradingbot`.`ant_user_wallet` as auw on auw.username = ort.username where ort.username = 'Admin' and ort.sell_price is null)
;

-- update `ant_cryptotradingbot`.`ant_user_wallet` set activation_balance = 1000, total_deposit = 1000 where username='thouship';
-- INSERT `ant_cryptotradingbot`.`transaction_history` (`symbol_name`, `amount`, `address`, `txID`, `from`, `to`, `type`, `details`, `status`, `username`, `txn_date`) 
--                             VALUES ('BUSD', 1000, 'No Address', 'txn_initial', 'Admin', 'thouship', 'Deposit', 'Initial Deposit', 'Successful', 'thouship', '2022-08-01 15:10:30');

select sum(cbor.`buy_price`*cbor.`order_quantity`) from `ant_cryptotradingbot`.`current_buy_order_report` as cbor
 inner join `ant_cryptotradingbot`.`order_report` as ort on ort.username=cbor.username and ort.symbol_name=cbor.symbol_name 
 and ort.`buy_price`=cbor.`buy_price` and ort.`order_quantity`=cbor.`order_quantity` and ort.`signal_type`=cbor.`signal_type` 
 and ort.`order_date`=cbor.`order_date` where cbor.username = 'Admin'
 
 
 
 UPDATE `ant_cryptotradingbot`.`order_report` SET `sell_price`= null
                            WHERE `symbol_name`='ICXUSDT' and `signal_type`='MACD' and `order_quantity`=146.0 and `update_date` is null and `username`='thouship';
 UPDATE `ant_cryptotradingbot`.`current_buy_order_report` SET `sell_orderID`=0, `sell_orderDate`=null
                                    WHERE `symbol_name`='ICXUSDT' and `signal_type`='MACD' and `username`='thouship';
                                    
        -- sum(cbor.`buy_price`*cbor.`order_quantity`)                            
(select cbor.* from `ant_cryptotradingbot`.`current_buy_order_report` as cbor inner join `ant_cryptotradingbot`.`order_report` as ort on ort.username=cbor.username and ort.symbol_name=cbor.symbol_name and ort.`buy_price`=cbor.`buy_price` and ort.`order_quantity`=cbor.`order_quantity` and ort.`signal_type`=cbor.`signal_type` and ort.`order_date`=cbor.`order_date` where cbor.username = 'Admin')




