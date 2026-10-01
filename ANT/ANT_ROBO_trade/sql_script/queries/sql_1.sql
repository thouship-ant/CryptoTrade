select * from `ant_cryptotradingbot`.`order_report` order by order_seq_id desc;
-- delete from `ant_cryptotradingbot`.`order_report` where s_no > 63 and s_no < 103
-- update `ant_cryptotradingbot`.`order_report` set order_seq_id = (order_seq_id - 80) where order_seq_id > 82; 

(select distinct first_value(buy_amount) over (order by order_seq_id asc) as invest_amount, first_value(sell_amount) over (order by order_seq_id desc) as final_amount from `ant_cryptotradingbot`.`order_report` where username = 'Admin' and sell_amount is not null)
union all
(select distinct first_value(buy_amount) over (order by order_seq_id asc) as invest_amount, first_value(sell_amount) over (order by order_seq_id desc) as final_amount from `ant_cryptotradingbot`.`order_report` where username = 'Admin' and sell_amount is not null and update_date >= '2022-07-01')
union all
(select distinct first_value(buy_amount) over (order by order_seq_id asc) as invest_amount, first_value(sell_amount) over (order by order_seq_id desc) as final_amount from `ant_cryptotradingbot`.`order_report` where username = 'Admin' and sell_amount is not null and update_date >= '2022-07-02');


SELECT orp.symbol_name, cbor.current_price, cbor.profit_percent as current_percent, orp.order_quantity, orp.buy_price, orp.buy_amount, ifnull(orp.sell_price, 0) as sell_price, ifnull(orp.sell_amount, 0) as sell_amount, ifnull(cbor.target_price, 0) as target_price, ifnull(cbor.stoploss_price, 0) as stoploss_price, orp.order_date 
from `ant_cryptotradingbot`.`order_report` as orp
left join `ant_cryptotradingbot`.`current_buy_order_report` as cbor on cbor.symbol_name = orp.symbol_name
where orp.username = 'Admin'
order by orp.order_seq_id desc limit 1;


-- INSERT `ant_cryptotradingbot`.`crypto_symbols_name` (symbol_name, symbol_full_name) VALUES ('BTC', 'Bitcoin');

SELECT * from `ant_cryptotradingbot`.`crypto_symbols_name`
;

call order_reports('thouship', '2022-07-27', '2022-07-27 23:59:59')


select distinct auw.`initial_investment` as invest_amount, auw.`binance_exchange_usdt` as final_amount from `ant_cryptotradingbot`.`ant_user_wallet` as auw left join `ant_cryptotradingbot`.`order_report` as ort on auw.username = ort.username where auw.username = '{}' and ort.username is null


(select distinct auw.`initial_investment` as invest_amount, (auw.`binance_exchange_usdt`+(select sum(buy_amount) from `ant_cryptotradingbot`.`order_report` where username = 'najik' and sell_price is null)) as final_amount from `ant_cryptotradingbot`.`order_report` as ort inner join `ant_cryptotradingbot`.`ant_user_wallet` as auw on auw.username = ort.username where ort.username = 'najik' and ort.sell_price is null)
                union all
                (select distinct auw.`initial_investment` as invest_amount, auw.`binance_exchange_usdt` as final_amount from `ant_cryptotradingbot`.`order_report` as ort inner join `ant_cryptotradingbot`.`ant_user_wallet` as auw on auw.username = ort.username where ort.username = 'najik' and ort.sell_price is not null
                and (select count(buy_amount) from `ant_cryptotradingbot`.`order_report` where username = 'najik' and sell_price is null) = 0)
                union all
                (select distinct auw.`initial_investment` as invest_amount, auw.`binance_exchange_usdt` as final_amount from `ant_cryptotradingbot`.`ant_user_wallet` as auw left join `ant_cryptotradingbot`.`order_report` as ort on auw.username = ort.username where auw.username = 'najik' and ort.username is null)