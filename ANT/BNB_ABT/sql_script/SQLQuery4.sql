SELECT csd.`symbol_name`, `current_askPrice`, csema.ema_7 as `entry_price`, 'MACD' as `signal_type`, 'BUY' as `signal_side`, csd.`is_Margin_Trade`, csd.`last_update_DateTime` as `update_datetime` 
                    FROM `ant_cryptotradingbot`.`crypto_symbols_data` as csd 
                    INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_macd_st_data` as csmsd on csd.symbol_name = csmsd.symbol_name 
                    INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_ema_data` as csema on csd.symbol_name = csema.symbol_name 
                    WHERE csd.upper_BBand_price > csd.current_askPrice and csd.middle_BBand_price < csd.current_askPrice 
                    and ((csema.ema_25 < csema.ema_7 and csema.ema_7 < csd.current_askPrice and csd.current_askPrice < csema.ema_99 and csema.ema_99 < csema.ema_200 and csd.MACD_dem < 0 and csd.MACD_dif > 0) 
                    or (csema.ema_99 < csema.ema_25 and csema.ema_25 < csema.ema_7 and csema.ema_7 < csd.current_askPrice and csd.current_askPrice < csema.ema_200 and csd.MACD_dem < 0 and csd.MACD_dif > 0) 
                    or (((csema.ema_25 < csema.ema_99 and csema.ema_99 < csema.ema_200) or (csema.ema_99 < csema.ema_25 and csema.ema_25 < csema.ema_200)) and csema.ema_200 < csema.ema_7 and csema.ema_7 < csd.current_askPrice and csd.MACD_dem > 0 and csd.MACD_dif > 0)) 
                    and csmsd.sum_dem_macd_prv < csmsd.sum_dem_macd_current and csd.MACD_macd > 0 and csd.is_Active = True and csd.is_Margin_Trade = True
                    union all
                    SELECT csd.`symbol_name`, `current_askPrice`, csema.ema_7 as `entry_price`, 'MACD' as `signal_type`, 'SELL' as `signal_side`, csd.`is_Margin_Trade`, csd.`last_update_DateTime` as `update_datetime` 
                    FROM `ant_cryptotradingbot`.`crypto_symbols_data` as csd 
                    INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_macd_st_data` as csmsd on csd.symbol_name = csmsd.symbol_name 
                    INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_ema_data` as csema on csd.symbol_name = csema.symbol_name 
                    WHERE csd.middle_BBand_price > csd.current_askPrice and csmsd.sum_dem_macd_prv > csmsd.sum_dem_macd_current and csd.MACD_macd < 0 
                    and ((csema.ema_25 > csema.ema_7 and csema.ema_7 > csema.ema_99 and csema.ema_99 > csema.ema_200 and csema.ema_200 > csd.current_askPrice and csd.MACD_dem > csd.MACD_dif and csd.MACD_dif > 0) 
                    or (csema.ema_25 > csema.ema_99 and csema.ema_99 > csema.ema_7 and csema.ema_7 > csema.ema_200 and csema.ema_200 > csd.current_askPrice and csd.MACD_dem > csd.MACD_dif and csd.MACD_dif > 0) 
                    or (((csema.ema_200 < csema.ema_99 and csema.ema_99 > csema.ema_25) or (csema.ema_200 < csema.ema_25 and csema.ema_99 < csema.ema_25)) and csema.ema_25 > csema.ema_7 and csema.ema_7 > csd.current_askPrice and csd.MACD_dem >= 0 and csd.MACD_dif <= 0)) and csd.is_Active = True and csd.is_Margin_Trade = True 
                    
                    union all
                    SELECT csd.`symbol_name`, `current_askPrice`, csema.ema_7 as `entry_price`, 'SuperTrend' as `signal_type`, 'BUY' as `signal_side`, csd.`is_Margin_Trade`, csd.`last_update_DateTime` as `update_datetime` 
                    FROM `ant_cryptotradingbot`.`crypto_symbols_data` as csd 
                    INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_macd_st_data` as csmsd on csd.symbol_name = csmsd.symbol_name 
                    INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_ema_data` as csema on csd.symbol_name = csema.symbol_name 
                    WHERE csd.upper_BBand_price > csd.current_askPrice and csd.middle_BBand_price < csd.current_askPrice 
                    and csmsd.`2hrs_ST_prv` = False and csmsd.`2hrs_ST_current` = True and csmsd.sum_dem_macd_prv < 0 and csmsd.sum_dem_macd_prv < csmsd.sum_dem_macd_current and csd.MACD_macd > 0 
                    and csd.last_RSI < 55 and csd.`2hrs_ST` = True and csd.is_Active = True and csd.is_Margin_Trade = True 
                    union all
                    SELECT csd.`symbol_name`, `current_askPrice`, csema.ema_7 as `entry_price`, 'SuperTrend' as `signal_type`, 'SELL' as `signal_side`, csd.`is_Margin_Trade`, csd.`last_update_DateTime` as `update_datetime` 
                    FROM `ant_cryptotradingbot`.`crypto_symbols_data` as csd 
                    INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_macd_st_data` as csmsd on csd.symbol_name = csmsd.symbol_name 
                    INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_ema_data` as csema on csd.symbol_name = csema.symbol_name 
                    WHERE csd.middle_BBand_price > csd.current_askPrice and csmsd.`2hrs_ST_prv` = True and csmsd.`2hrs_ST_current` = False 
                    and csmsd.sum_dem_macd_prv > 0 and csmsd.sum_dem_macd_prv > csmsd.sum_dem_macd_current and csd.MACD_macd < 0 and (csd.last_RSI < 90 or csd.`2hrs_ST` = False) and csd.is_Active = True and csd.is_Margin_Trade = True 
                    
                    union all
                    SELECT csd.`symbol_name`, `current_askPrice`, csema.ema_7 as `entry_price`, concat('Pattern - ', lps.`PatternName`) as `signal_type`, 'BUY' as `signal_side`, csd.`is_Margin_Trade`, csd.`last_update_DateTime` as `update_datetime` 
                    FROM `ant_cryptotradingbot`.`crypto_symbols_data` as csd 
                    INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_macd_st_data` as csmsd on csd.symbol_name = csmsd.symbol_name 
                    INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_ema_data` as csema on csd.symbol_name = csema.symbol_name 
                    INNER JOIN `ant_cryptotradingbot`.`live_patterns_signal` as lps on csd.symbol_name = lps.symbol_name 
                    WHERE (csd.MACD_macd > 0 or (csd.MACD_macd < 0 and csd.MACD_dif < csd.MACD_dem and csd.MACD_dem < 0)) and csmsd.sum_dem_macd_prv < csmsd.sum_dem_macd_current and csd.`2hrs_ST` = True 
                    and csema.ema_200 < csema.ema_99 and csema.ema_99 < csema.ema_25 and csema.ema_25 < csema.ema_7 and csema.ema_7 < csd.current_askPrice and csd.is_Active = True
                    and lps.`PatternName` in ('Inverted Hammer','Hammer','Piercing Pattern','Morning Star','Morning Doji Star','Three Advancing White Soldiers','Engulfing Pattern') and lps.SignalType = 'bullish' and csd.is_Margin_Trade = True 
                    
                    union all
                    SELECT csd.`symbol_name`, `current_askPrice`, csema.ema_7 as `entry_price`, 'EMA' as `signal_type`, 'BUY' as `signal_side`, csd.`is_Margin_Trade`, csd.`last_update_DateTime` as `update_datetime` 
                    FROM `ant_cryptotradingbot`.`crypto_symbols_data` as csd 
                    INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_ema_data` as csema on csd.symbol_name = csema.symbol_name 
                    INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_macd_st_data` as csmsd on csd.symbol_name = csmsd.symbol_name 
                    WHERE ((`SIGNAL_7_25` = 'BUY' and csema.ema_200 > csema.ema_25 and csema.ema_25 < csema.ema_7 and csema.ema_7 < csd.current_askPrice) 
                    or (`SIGNAL_7_99` = 'BUY' and csema.ema_200 > csema.ema_99 and csema.ema_99 < csema.ema_7 and csema.ema_7 < csd.current_askPrice)
                    or (`SIGNAL_7_200` = 'BUY' and csema.ema_200 < csema.ema_7 and csema.ema_200 > csema.ema_99 and csema.ema_200 > csema.ema_25 and csema.ema_7 < csd.current_askPrice))
                    and csmsd.sum_dem_macd_prv < csmsd.sum_dem_macd_current and csd.MACD_macd > 0 and csd.is_Active = True and csd.is_Margin_Trade = True 
                    union all
                    SELECT csd.`symbol_name`, `current_askPrice`, csema.ema_7 as `entry_price`, 'EMA' as `signal_type`, 'SELL' as `signal_side`, csd.`is_Margin_Trade`, csd.`last_update_DateTime` as `update_datetime` 
                    FROM `ant_cryptotradingbot`.`crypto_symbols_data` as csd 
                    INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_ema_data` as csema on csd.symbol_name = csema.symbol_name 
                    INNER JOIN `ant_cryptotradingbot`.`crypto_symbols_macd_st_data` as csmsd on csd.symbol_name = csmsd.symbol_name 
                    WHERE ((`SIGNAL_7_25` = 'SELL' and csema.ema_200 < csema.ema_25 and csema.ema_25 > csema.ema_7 and csema.ema_7 > csd.current_askPrice) 
                    or (`SIGNAL_7_99` = 'SELL' and csema.ema_200 < csema.ema_99 and csema.ema_99 > csema.ema_7 and csema.ema_7 > csd.current_askPrice) 
                    or (`SIGNAL_7_200` = 'SELL' and csema.ema_200 > csema.ema_7 and csema.ema_200 < csema.ema_99 and csema.ema_200 < csema.ema_25 and csema.ema_7 > csd.current_askPrice))
                    and csmsd.sum_dem_macd_prv < csmsd.sum_dem_macd_current and csd.MACD_macd < 0 and csd.is_Active = True and csd.is_Margin_Trade = True
                    