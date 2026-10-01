SELECT csd.`symbol_name`, `current_askPrice`, `upper_BBand_price`, `middle_BBand_price`, `lower_BBand_price`, `MACD_dif`, `MACD_dem`, `MACD_macd`, `last_RSI`, `stoch`, `2hrs_ST`, csd.`last_update_DateTime`, csmsd.sum_dem_macd_prv, csmsd.sum_dem_macd_current FROM `ant_cryptotradingbot`.`crypto_symbols_data` as csd 
                INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_macd_st_data` as csmsd on csd.symbol_name = csmsd.symbol_name 
                WHERE (csd.upper_BBand_price > csd.current_askPrice 
                and (csd.middle_BBand_price < csd.current_askPrice or ((csd.middle_BBand_price + csd.lower_BBand_price)/2) < csd.current_askPrice)) and 
                csmsd.sum_dem_macd_current >= 0 and csmsd.sum_dem_macd_prv < csmsd.sum_dem_macd_current and csd.MACD_dem > 0 and
                csd.MACD_macd > 0 and csd.last_RSI > 50 and csd.last_RSI < 65 and csd.`stoch` = 1
                and csd.`2hrs_ST` = True and csd.is_Active = True;
                
select * from `ant_cryptotradingbot`.`crypto_symbols_data` where `stoch` = 1;
                
-- update `ant_cryptotradingbot`.`current_buy_order_report` set order_quantity= 113, buy_price = 0.439 where username='thouship' and order_seq_id = 5;
-- update `ant_cryptotradingbot`.`order_report` set order_quantity= 113, buy_price = 0.439, buy_amount = 49.607 where username='thouship' and s_no = 702;

ALTER TABLE `ant_cryptotradingbot`.`crypto_symbols_data` ADD `stoch` INT default 0;
