USE [ant_cryptotradingbot]
GO

IF  EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[crypto_symbols_data]') AND type in (N'U'))
DROP TABLE [dbo].[crypto_symbols_data]
GO

SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[crypto_symbols_data](
	[symbol_id] [bigint] IDENTITY(1,1) NOT NULL,
	[symbol_name] [nvarchar](20) NULL,
	[current_askPrice] [decimal](10,8) NULL,
	[current_bidPrice] [decimal](10,8) NULL,
	[24hrs_change] [decimal](5,2) NULL,
	[upper_BBand_price] [decimal](10,8) NULL,
	[middle_BBand_price] [decimal](10,8) NULL,
	[lower_BBand_price] [decimal](10,8) NULL,
	[MACD_dif] [decimal](10,8) NULL,
	[MACD_dem] [decimal](10,8) NULL,
	[MACD_macd] [decimal](10,8) NULL,
	[last_RSI] [decimal](5,2) NULL,
	[15mins_ST] [bit] NOT NULL default 0,
	[30mins_ST] [bit] NOT NULL default 0,
	[2hrs_ST] [bit] NOT NULL default 0,
	[1d_ST] [bit] NOT NULL default 0,
	[last_update_DateTime] [datetime] NOT NULL default GETDATE(),
	[is_MACD_Trade] [bit] NOT NULL default 1,
	[is_ST_Trade] [bit] NOT NULL default 0,
	[is_Active] [bit] NOT NULL default 1,
	CONSTRAINT PK_crypto_symbols_data PRIMARY KEY (symbol_id)
);
GO


IF  EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[crypto_symbols_macd_st_data]') AND type in (N'U'))
DROP TABLE [dbo].[crypto_symbols_macd_st_data]
GO

SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[crypto_symbols_macd_st_data](
	[symbol_name] [nvarchar](20) NOT NULL,
	[sum_dem_macd_prv] [decimal](8,8) NULL,
	[sum_dem_macd_current] [decimal](8,8) NULL,
	[2hrs_ST_prv] [bit] NOT NULL default 0,
	[2hrs_ST_current] [bit] NOT NULL default 0,
	[last_update_DateTime] [datetime] NOT NULL default GETDATE(),
	[is_Active] [bit] NOT NULL default 1,
	CONSTRAINT PK_crypto_symbols_macd_st_data PRIMARY KEY (symbol_name)
);
GO


IF  EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[order_report]') AND type in (N'U'))
DROP TABLE [dbo].[order_report]
GO

SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[order_report](
	[s_no] [bigint] IDENTITY(1,1) NOT NULL,
	[order_seq_id] [bigint] NOT NULL,
	[symbol_name] [nvarchar](20) NOT NULL,
	[signal_type] [nvarchar](20) NULL,
	[order_quantity] [decimal](8,2) NULL,
	[buy_price] [decimal](12,8) NULL,
	[buy_amount] [decimal](12,4) NULL,
	[sell_price] [decimal](12,8) NULL,
	[sell_amount] [decimal](12,4) NULL,
	[profit_amount] [decimal](8,2) NULL,
	[profit_percent] [decimal](8,2) NULL,
	[username] [nvarchar](50) NOT NULL,
	[order_date] [datetime] NOT NULL,
	[update_date] [datetime] NULL,
	CONSTRAINT PK_order_report PRIMARY KEY ([s_no])
);
GO


IF  EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[current_buy_order_report]') AND type in (N'U'))
DROP TABLE [dbo].[current_buy_order_report]
GO

SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[current_buy_order_report](
	[order_seq_id] [bigint] NOT NULL,
	[symbol_name] [nvarchar](20) NOT NULL,
	[signal_type] [nvarchar](20) NULL,
	[order_quantity] [decimal](8,2) NULL,
	[buy_price] [decimal](12,8) NULL,
	[current_price] [decimal](12,8) NULL,
	[profit_percent] [decimal](8,2) NULL,
	[target_price] [decimal](12,8) NULL,
	[username] [nvarchar](50) NOT NULL,
	[order_date] [datetime] NOT NULL
);
GO

IF  EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[bnb_report]') AND type in (N'U'))
DROP TABLE [dbo].[bnb_report]
GO

SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[bnb_report](
	[s_no] [bigint] IDENTITY(1,1) NOT NULL,
	[symbol_name] [nvarchar](20) NOT NULL,
	[order_quantity] [decimal](8,2) NULL,
	[buy_price] [decimal](12,8) NULL,
	[buy_amount] [decimal](12,4) NULL,
	[username] [nvarchar](50) NOT NULL,
	[order_date] [datetime] NOT NULL,
	CONSTRAINT PK_bnb_report PRIMARY KEY ([s_no])
);
GO
