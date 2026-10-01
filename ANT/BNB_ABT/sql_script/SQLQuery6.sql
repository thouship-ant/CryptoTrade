-- Sell Query
SELECT csd.`symbol_name`, dbdt.`entry_signal_type`, dbdt.`signal_side`, csd.current_bidPrice, dbdt.`entry_price`,dbdt.`entry_date`,
                    CASE WHEN dbdt.`entry_signal_type`='MACD' THEN CASE WHEN dbdt.`signal_side` = 'BUY' THEN 
                    CASE WHEN csd.upper_BBand_price > csd.current_bidPrice and csd.middle_BBand_price < csd.current_bidPrice and csd.upper_BBand_price > dbdt.entry_price THEN csd.upper_BBand_price
                    WHEN csmsd.sum_dem_macd_prv > csmsd.sum_dem_macd_current and csd.MACD_macd < 0 and csema.ema_7 > csd.current_bidPrice and csema.ema_7 > dbdt.entry_price THEN csema.ema_7 
                    WHEN csmsd.sum_dem_macd_prv < csmsd.sum_dem_macd_current and csema.ema_99 > csema.ema_7 and csema.ema_99 > csema.ema_25 and csema.ema_99 > csd.current_bidPrice and csema.ema_99 > dbdt.entry_price THEN csema.ema_99 
                    WHEN csmsd.sum_dem_macd_prv < csmsd.sum_dem_macd_current and csema.ema_200 > csema.ema_7 and csema.ema_200 > csema.ema_25 and csema.ema_200 > csema.ema_99 and csema.ema_200 > csd.current_bidPrice and csema.ema_200 > dbdt.entry_price THEN csema.ema_200 
                    ELSE (dbdt.entry_price + (dbdt.entry_price * 1 / 100)) END 
                    WHEN dbdt.`signal_side` = 'SELL' THEN 
                    CASE WHEN csd.lower_BBand_price > csd.current_askPrice and csd.middle_BBand_price > csd.current_askPrice and csd.lower_BBand_price < dbdt.entry_price THEN csd.lower_BBand_price
                    WHEN csmsd.sum_dem_macd_prv < csmsd.sum_dem_macd_current and csd.MACD_macd > 0 and csema.ema_7 < csd.current_askPrice and csema.ema_7 < dbdt.entry_price THEN csema.ema_7 
                    WHEN csmsd.sum_dem_macd_prv > csmsd.sum_dem_macd_current and csema.ema_99 < csema.ema_7 and csema.ema_99 < csema.ema_25 and csema.ema_99 < csd.current_bidPrice and csema.ema_99 < dbdt.entry_price THEN csema.ema_99 
                    WHEN csmsd.sum_dem_macd_prv > csmsd.sum_dem_macd_current and csema.ema_200 < csema.ema_7 and csema.ema_200 < csema.ema_25 and csema.ema_200 < csema.ema_99 and csema.ema_200 < csd.current_bidPrice and csema.ema_200 < dbdt.entry_price THEN csema.ema_200 
                    ELSE (dbdt.entry_price - (dbdt.entry_price * 1 / 100)) END 
                    ELSE (dbdt.entry_price + (dbdt.entry_price * 1 / 100)) END 
                    WHEN dbdt.`entry_signal_type`='EMA' THEN CASE WHEN dbdt.`signal_side` = 'BUY' THEN 
                    CASE WHEN csema.ema_7 < csd.current_bidPrice and csema.ema_25 < csd.current_bidPrice and csema.ema_99 > csd.current_bidPrice and csema.ema_99 > dbdt.entry_price THEN csema.ema_99
                    WHEN csema.ema_7 < csd.current_bidPrice and csema.ema_25 < csd.current_bidPrice and csema.ema_200 > csd.current_bidPrice THEN csema.ema_200
                    WHEN csema.ema_7 > csd.current_bidPrice and csema.ema_7 > dbdt.entry_price THEN csema.ema_7 WHEN csema.ema_25 > csd.current_bidPrice and csema.ema_25 > dbdt.entry_price THEN csema.ema_25 
                    WHEN csema.ema_99 > csd.current_bidPrice and csema.ema_99 > dbdt.entry_price THEN csema.ema_99 WHEN csema.ema_200 > csd.current_bidPrice and csema.ema_200 > dbdt.entry_price THEN csema.ema_200 
                    WHEN csema.ema_25 > csd.current_bidPrice and csema.ema_25 > csema.ema_7 and csema.ema_7 > dbdt.entry_price THEN csema.ema_7 
                    ELSE (dbdt.entry_price + (dbdt.entry_price * 1 / 100)) END 
                    WHEN dbdt.`signal_side` = 'SELL' THEN 
                    CASE WHEN csema.ema_7 > csd.current_askPrice and csema.ema_25 > csd.current_askPrice and csema.ema_99 < csd.current_askPrice and csema.ema_99 < dbdt.entry_price THEN csema.ema_99
                    WHEN csema.ema_7 > csd.current_askPrice and csema.ema_25 > csd.current_askPrice and csema.ema_200 < csd.current_askPrice and csema.ema_200 < dbdt.entry_price THEN csema.ema_200
                    WHEN csema.ema_7 < csd.current_askPrice and csema.ema_7 < dbdt.entry_price THEN csema.ema_7 WHEN csema.ema_25 < csd.current_askPrice and csema.ema_25 < dbdt.entry_price THEN csema.ema_25 
                    WHEN csema.ema_99 < csd.current_askPrice and csema.ema_99 < dbdt.entry_price THEN csema.ema_99 WHEN csema.ema_200 < csd.current_askPrice and csema.ema_200 < dbdt.entry_price THEN csema.ema_200 
                    WHEN csema.ema_25 < csd.current_askPrice and csema.ema_25 > csema.ema_7 and csema.ema_7 < dbdt.entry_price THEN csema.ema_7 
                    ELSE (dbdt.entry_price - (dbdt.entry_price * 1 / 100)) END 
                    ELSE (dbdt.entry_price + (dbdt.entry_price * 1 / 100)) END 
                    ELSE (dbdt.entry_price + (dbdt.entry_price * 1 / 100)) END  as `exit_price`, 
                    CASE WHEN dbdt.`entry_signal_type`='TELEGRAM' and dbtts.symbol_name is not null THEN CASE WHEN dbdt.`signal_side` = 'BUY' THEN 
                    CASE WHEN dbtts.target_price_4 < csd.current_bidPrice THEN dbtts.target_price_3
                    WHEN dbtts.target_price_3 < csd.current_bidPrice THEN dbtts.target_price_2
                    WHEN dbtts.target_price_2 < csd.current_bidPrice THEN dbtts.target_price_1
                    WHEN dbtts.target_price_1 < csd.current_bidPrice THEN dbdt.entry_price
                    ELSE 
                    CASE WHEN csd.price_breakOut = -1 and csd.current_bidPrice > dbdt.entry_price THEN csd.current_bidPrice
                    ELSE dbdt.`stop_price` END END 
                    WHEN dbdt.`signal_side` = 'SELL' THEN 
                    CASE WHEN dbtts.target_price_4 > csd.current_bidPrice THEN dbtts.target_price_3
                    WHEN dbtts.target_price_3 > csd.current_bidPrice THEN dbtts.target_price_2
                    WHEN dbtts.target_price_2 > csd.current_bidPrice THEN dbtts.target_price_1
                    WHEN dbtts.target_price_1 > csd.current_bidPrice THEN dbdt.entry_price
                    ELSE CASE WHEN csd.price_breakOut = 1 and csd.current_askPrice < dbdt.entry_price THEN csd.current_askPrice
                    ELSE dbdt.`stop_price` END END 
                    ELSE CASE WHEN csd.price_breakOut = -1 and csd.current_bidPrice > dbdt.entry_price and dbdt.`signal_side` = 'BUY' THEN csd.current_bidPrice
                    WHEN csd.price_breakOut = 1 and csd.current_askPrice < dbdt.entry_price and dbdt.`signal_side` = 'SELL' THEN csd.current_askPrice
                    ELSE dbdt.`stop_price` END END 
                    ELSE CASE WHEN csd.price_breakOut = -1 and csd.current_bidPrice > dbdt.entry_price and dbdt.`signal_side` = 'BUY' THEN csd.current_bidPrice
                    WHEN csd.price_breakOut = 1 and csd.current_askPrice < dbdt.entry_price and dbdt.`signal_side` = 'SELL' THEN csd.current_askPrice
                    ELSE dbdt.`stop_price` END END as `stop_price`, 
                    csema.ema_7, csema.ema_25, csema.ema_99, csema.ema_200
                    FROM `ant_cryptotradingbot`.`crypto_symbols_data` as csd 
                    INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_macd_st_data` as csmsd on csd.symbol_name = csmsd.symbol_name 
                    INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_ema_data` as csema on csd.symbol_name = csema.symbol_name 
                    INNER JOIN `ant_cryptotradingbot`.`db_demo_trade` as dbdt on csd.symbol_name = dbdt.symbol_name 
                    LEFT JOIN `ant_cryptotradingbot`.`db_telegram_trade_signals` as dbtts on csd.symbol_name = dbtts.symbol_name and dbtts.is_tradeable = True 
                    WHERE dbdt.`trade_id`= 3133 and dbdt.`entry_date` is not null and dbdt.`exit_date` is null  
                    and csd.symbol_name = 'RENUSDT'