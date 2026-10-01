
-- INSERT `ant_cryptotradingbot`.`daily_profit_report` (`date`, `username`, `start_amount`, `end_amount`, `profit_amount`, `profit_percent`, `update_date`) VALUES ('2022-07-19', 'thouship', 505.23, 507.55, 2.32, 0.66, '2022-07-19 23:59:59');

-- delete from `ant_cryptotradingbot`.`daily_profit_report` where username='thouship';
-- truncate table `ant_cryptotradingbot`.`daily_profit_report`;
select * from `ant_cryptotradingbot`.`daily_profit_report` where username='Admin';
select sum(profit_amount) from `ant_cryptotradingbot`.`daily_profit_report` where `username` = 'Admin';

set @tradedate='2022-06-21';
select sum(profit_amount) from `ant_cryptotradingbot`.`order_report` where `username` = 'thouship';-- and update_date >= @tradedate and update_date <= concat(@tradedate, ' 23:59:59');
select sum(profit_amount) from `ant_cryptotradingbot`.`daily_profit_report` where `username` = 'thouship';-- and `date` = @tradedate;

select * from `ant_cryptotradingbot`.`daily_profit_report` where `username` = 'najik' order by `date` desc;
select * from `ant_cryptotradingbot`.`daily_profit_report` where `username` = 'thouship' order by `date` desc;
select * from `ant_cryptotradingbot`.`daily_profit_report` where `username` = 'Admin' order by `date` desc;

select sum(orp.profit_amount), sum(orp.commission_price) from 
                                (select cast(update_date as date) as `date`, profit_amount, commission_price from `ant_cryptotradingbot`.`order_report` where `username` = 'Admin') as orp
                                where orp.`date`='2022-07-23' group by orp.`date`

-- ALTER TABLE `ant_cryptotradingbot`.`daily_profit_report` ALTER `profit_amount` SET DEFAULT (0);
-- ALTER TABLE `ant_cryptotradingbot`.`daily_profit_report` ALTER `profit_percent` SET DEFAULT (0);

-- update `ant_cryptotradingbot`.`daily_profit_report` set end_amount=612.2748+0.92, start_amount=612.27 where `username` = 'thouship' and `date` = '2022-08-01';
-- update `ant_cryptotradingbot`.`daily_profit_report` set end_amount=482.1100, start_amount=481.5400 where `username` = 'Admin' and `date` = '2022-07-26';

select orp.`date`, sum(orp.profit_amount), sum(orp.profit_percent), sum(orp.commission_price) from 
(select cast(update_date as date) as `date`, profit_amount, profit_percent, commission_price from `ant_cryptotradingbot`.`order_report` where `username` = 'thouship') as orp
group by orp.`date`;
select `date`,profit_amount,profit_percent,commission_price from `ant_cryptotradingbot`.`daily_profit_report` where `username` = 'thouship' order by `date` asc;


set @username='thouship';
-- select distinct cast(`update_date` as Date) as 'date' from `ant_cryptotradingbot`.`order_report` where username = @username;
set @tradedate='2022-07-17';
select distinct @startamount := first_value(buy_amount) over (order by order_seq_id asc) as invest_amount, @endamount := (first_value(buy_amount) over (order by order_seq_id asc) + sum(profit_amount) - sum(commission_price)) as final_amount from `ant_cryptotradingbot`.`order_report` where username = @username and sell_amount is not null and update_date >= @tradedate and update_date <= concat(@tradedate, ' 23:59:59');
set @profitamount = @endamount - @startamount;
set @profitpercent = (@endamount - @startamount) / (@startamount / 100);
select @startamount, @endamount,  @profitamount , @profitpercent;
-- INSERT `ant_cryptotradingbot`.`daily_profit_report` (`date`, `username`, `start_amount`, `end_amount`, `profit_amount`, `profit_percent`, `update_date`) VALUES (@tradedate, @username, @startamount, @endamount, @profitamount, @profitpercent, concat(@tradedate, ' 23:59:59'));


SELECT csn.symbol_name as symbol, replace(csn.symbol_full_name, '_', '') as symbol_full_name, csd.`profit_amount`, cast(csd.`update_date` as Date) as `Date` from `ant_cryptotradingbot`.`order_report` as csd
                inner join `ant_cryptotradingbot`.`crypto_symbols_name` as csn on csn.symbol_name = replace(csd.symbol_name, 'USDT', '')
                where csd.`username` = 'thouship' order by csd.`update_date` desc limit 8;
