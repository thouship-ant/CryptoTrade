'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { TrendingUp, Wallet, Activity, BarChart3, Flame, KeyRound, Power } from 'lucide-react';
import Navigation from '@/components/Navigation';
import CoinIcon from '@/components/CoinIcon';
import TablePagination from '@/components/TablePagination';
import { getApiBaseUrl, safeJson, formatUsd, formatPrice, formatQty, formatDateTime } from '@/lib/apiConfig';

const CandlestickChart = dynamic(() => import('@/components/CandlestickChart'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-72">
      <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary"></div>
    </div>
  ),
});

const DEFAULT_PAGE_SIZE = 5;
const LIVE_REFRESH_MS = 60 * 1000;

const POSITION_TABS = [
  { value: 'ALL', label: 'All' },
  { value: 'LONG', label: 'Long' },
  { value: 'SHORT', label: 'Short' },
];

function pnlClass(value) {
  return Number(value) >= 0 ? 'text-green-600' : 'text-red-600';
}

function signed(value, digits = 2) {
  const n = Number(value) || 0;
  return `${n >= 0 ? '+' : '-'}$${formatUsd(Math.abs(n), digits)}`;
}

function PercentBadge({ value }) {
  const n = Number(value) || 0;
  return <Badge variant={n >= 0 ? 'default' : 'destructive'}>{n >= 0 ? '+' : ''}{n.toFixed(2)}%</Badge>;
}

export default function DashboardPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState(null);
  const [config, setConfig] = useState(null);
  const [movers, setMovers] = useState([]);
  const [userName, setUserName] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);
  const [tab, setTab] = useState('ALL');
  const [selected, setSelected] = useState(null);
  const [candles, setCandles] = useState([]);
  const [candlesLoading, setCandlesLoading] = useState(false);

  const fetchLive = useCallback(async (uid) => {
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/dashboard/${uid}/live`);
      if (!response.ok) return;
      const data = await safeJson(response);
      setDashboard((prev) => (prev ? { ...prev, ...data } : prev));
    } catch (error) {
      console.error('Error refreshing live dashboard data:', error);
    }
  }, []);

  useEffect(() => {
    const storedUserId = localStorage.getItem('user_id');
    if (!storedUserId) {
      router.push('/');
      return;
    }
    setUserName(localStorage.getItem('full_name') || '');

    const load = async (path, apply) => {
      try {
        const response = await fetch(`${getApiBaseUrl()}${path}`);
        if (response.ok) apply(await safeJson(response));
      } catch (error) {
        console.error(`Error loading ${path}:`, error);
      }
    };

    (async () => {
      await Promise.all([
        load(`/api/dashboard/${storedUserId}`, setDashboard),
        load(`/api/config/${storedUserId}`, setConfig),
        load('/api/market/top-movers?limit=8', (d) => setMovers(d.coins || [])),
      ]);
      setLoading(false);
    })();

    const intervalId = setInterval(() => fetchLive(storedUserId), LIVE_REFRESH_MS);
    return () => clearInterval(intervalId);
  }, [router, fetchLive]);

  // Candles for the position-detail chart: from a little before entry until now.
  useEffect(() => {
    if (!selected) return;
    let cancelled = false;
    (async () => {
      setCandlesLoading(true);
      try {
        const from = new Date(selected.created_DateTime).toISOString();
        const response = await fetch(
          `${getApiBaseUrl()}/api/market/candles/${encodeURIComponent(selected.symbol_name)}?from_datetime=${encodeURIComponent(from)}`
        );
        const data = await safeJson(response);
        if (!cancelled) setCandles(data.candles || []);
      } catch (error) {
        console.error('Error fetching candles:', error);
        if (!cancelled) setCandles([]);
      } finally {
        if (!cancelled) setCandlesLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [selected]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
      </div>
    );
  }

  const openOrders = dashboard?.open_orders || [];
  const tabCounts = POSITION_TABS.reduce((acc, t) => {
    acc[t.value] = t.value === 'ALL' ? openOrders.length : openOrders.filter((o) => o.side === t.value).length;
    return acc;
  }, {});
  const filtered = openOrders.filter((o) => tab === 'ALL' || o.side === tab);
  // The live refresh doesn't reset the page (browsing isn't yanked back mid-session) - clamp
  // in case the list shrank underneath it.
  const totalPages = Math.ceil(filtered.length / pageSize);
  const currentPage = Math.min(page, totalPages || 1);

  const keysMissing = config && !config.has_api_key;
  const paused = config && config.has_api_key && !config.is_trading_active;

  return (
    <div className="min-h-screen bg-background">
      <Navigation userName={userName} />

      <div className="container mx-auto px-4 py-8">
        {keysMissing && (
          <Link href="/settings" className="mb-6 flex items-center gap-3 rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900 hover:bg-amber-100 dark:border-amber-700/50 dark:bg-amber-950/30 dark:text-amber-200">
            <KeyRound className="h-5 w-5 shrink-0" />
            <span>Connect your Binance API keys in <strong>Settings</strong> to start automated trading.</span>
          </Link>
        )}
        {paused && (
          <Link href="/settings" className="mb-6 flex items-center gap-3 rounded-lg border bg-muted p-4 text-sm hover:bg-accent">
            <Power className="h-5 w-5 shrink-0 text-muted-foreground" />
            <span>The bot is <strong>paused</strong>. Open positions are still managed; no new trades will be opened. Start it from <strong>Settings</strong>.</span>
          </Link>
        )}

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Trading Capital</CardTitle>
              <Wallet className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">${formatUsd(dashboard?.total_investment)}</div>
              <p className="text-xs text-muted-foreground mt-1">
                Binance USDT + open margin &middot; Earnings: ${formatUsd(dashboard?.wallet_balance)}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total P/L</CardTitle>
              <TrendingUp className="h-4 w-4 text-green-500" />
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold ${pnlClass(dashboard?.total_profit)}`}>{signed(dashboard?.total_profit)}</div>
              <div className="mt-1"><PercentBadge value={dashboard?.total_profit_percent} /></div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Today&apos;s P/L</CardTitle>
              <Activity className="h-4 w-4 text-amber-500" />
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold ${pnlClass(dashboard?.today_profit)}`}>{signed(dashboard?.today_profit)}</div>
              <div className="mt-1"><PercentBadge value={dashboard?.today_profit_percent} /></div>
              <div className="text-xs text-muted-foreground mt-2 flex items-center gap-2 flex-wrap">
                <span>Realized <span className={`font-semibold ${pnlClass(dashboard?.today_realized_profit)}`}>{signed(dashboard?.today_realized_profit)}</span></span>
                <span>Unrealized <span className={`font-semibold ${pnlClass(dashboard?.today_unrealized_profit)}`}>{signed(dashboard?.today_unrealized_profit)}</span></span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Month&apos;s P/L</CardTitle>
              <BarChart3 className="h-4 w-4 text-amber-500" />
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold ${pnlClass(dashboard?.month_profit)}`}>{signed(dashboard?.month_profit)}</div>
              <div className="mt-1"><PercentBadge value={dashboard?.month_profit_percent} /></div>
            </CardContent>
          </Card>
        </div>

        {/* Open Positions */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Open Positions</CardTitle>
            <CardDescription>{tabCounts[tab]} active position{tabCounts[tab] === 1 ? '' : 's'} &middot; refreshes every minute</CardDescription>
          </CardHeader>
          {/* Folder-style tabs - the active tab's own bottom border is erased and pulled
              down onto the shared rule below (-mb-px) so it merges into the content. */}
          <div className="px-6">
            <div className="flex items-end gap-1 border-b border-border">
              {POSITION_TABS.map((t) => (
                <button
                  key={t.value}
                  type="button"
                  onClick={() => { setTab(t.value); setPage(1); }}
                  className={`relative -mb-px rounded-t-lg border px-3 py-1.5 text-sm font-medium transition-colors ${
                    tab === t.value
                      ? 'z-10 border-border border-b-transparent bg-card text-foreground'
                      : 'border-transparent text-muted-foreground hover:bg-muted/50 hover:text-foreground'
                  }`}
                >
                  {t.label}
                  <span className="ml-1.5 text-xs text-muted-foreground">({tabCounts[t.value]})</span>
                </button>
              ))}
            </div>
          </div>
          <CardContent>
            <div className="space-y-4">
              {filtered.length === 0 && (
                <div className="text-center py-8 text-muted-foreground">
                  No {tab === 'ALL' ? '' : `${tab.toLowerCase()} `}open positions
                </div>
              )}
              {filtered.slice((currentPage - 1) * pageSize, currentPage * pageSize).map((order) => (
                <div
                  key={order.signal_id}
                  className="flex flex-col sm:flex-row sm:items-center gap-3 p-4 border rounded-lg hover:bg-accent transition-colors cursor-pointer"
                  onClick={() => setSelected(order)}
                >
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <CoinIcon symbol={order.symbol_name} size={40} />
                    <div className="min-w-0">
                      <div className="font-medium truncate">{order.symbol_name}</div>
                      <div className="text-sm text-muted-foreground truncate">
                        {order.leverage > 1 ? `${order.leverage}x leverage` : 'Spot'}
                      </div>
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-2 sm:flex sm:flex-[2] sm:items-center sm:gap-0">
                    <div className="flex items-center sm:flex-1">
                      <Badge variant={order.side === 'LONG' ? 'default' : 'secondary'}>{order.side}</Badge>
                    </div>
                    <div className="sm:flex-1 text-right">
                      <div className="font-medium whitespace-nowrap">${formatPrice(order.entry_price)}</div>
                      <div className="text-sm text-muted-foreground whitespace-nowrap">Qty: {formatQty(order.quantity)}</div>
                    </div>
                    <div className="sm:flex-1 text-right">
                      <div className="font-medium whitespace-nowrap">${formatPrice(order.current_price ?? order.entry_price)}</div>
                      <div className={`text-sm font-bold whitespace-nowrap ${pnlClass(order.PandL)}`}>
                        {signed(order.PandL)} <span className="font-normal">({Number(order.PandL_percent || 0).toFixed(2)}%)</span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-6">
              <TablePagination
                page={currentPage}
                totalPages={totalPages}
                onPageChange={setPage}
                pageSize={pageSize}
                onPageSizeChange={(size) => { setPageSize(size); setPage(1); }}
              />
            </div>
          </CardContent>
        </Card>

        {/* Position detail */}
        <Dialog open={!!selected} onOpenChange={() => setSelected(null)}>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                {selected && <CoinIcon symbol={selected.symbol_name} size={24} />}
                {selected?.symbol_name} <Badge variant={selected?.side === 'LONG' ? 'default' : 'secondary'}>{selected?.side}</Badge>
              </DialogTitle>
              <DialogDescription>Details of this open position</DialogDescription>
            </DialogHeader>
            {selected && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <Detail label="Quantity" value={formatQty(selected.quantity)} />
                  <Detail label="Leverage" value={`${selected.leverage}x`} />
                  <Detail label="Entry Price" value={`$${formatPrice(selected.entry_price)}`} sub={`$${formatUsd(selected.entry_price * selected.quantity)} notional`} />
                  <Detail label="Current Price" value={`$${formatPrice(selected.current_price ?? selected.entry_price)}`} />
                  <Detail label="Target" value={selected.target_price ? `$${formatPrice(selected.target_price)}` : '-'} />
                  <Detail label="Stoploss" value={selected.stoploss_price ? `$${formatPrice(selected.stoploss_price)}` : '-'} />
                  <Detail label="Margin" value={`$${formatUsd(selected.margin)}`} />
                  <div>
                    <div className="text-muted-foreground">Unrealized P&amp;L</div>
                    <div className={`font-semibold ${pnlClass(selected.PandL)}`}>
                      {signed(selected.PandL)} ({Number(selected.PandL_percent || 0).toFixed(2)}%)
                    </div>
                  </div>
                  <Detail label="Opened" value={formatDateTime(selected.created_DateTime)} />
                  <Detail label="Signal" value={selected.buy_reason || selected.signal_type || '-'} />
                </div>
                <div>
                  <div className="text-sm text-muted-foreground mb-2">15m chart &mdash; {selected.symbol_name} (entry to now)</div>
                  {candlesLoading ? (
                    <div className="flex items-center justify-center h-72">
                      <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary"></div>
                    </div>
                  ) : (
                    <CandlestickChart candles={candles} entryPrice={Number(selected.entry_price)} />
                  )}
                </div>
              </div>
            )}
          </DialogContent>
        </Dialog>

        <div className="grid gap-8 lg:grid-cols-2">
          {/* Recent P/L */}
          <Card>
            <CardHeader>
              <CardTitle>Recent Performance</CardTitle>
              <CardDescription>Last 7 days profit/loss</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {(dashboard?.recent_profits || []).length === 0 && (
                  <div className="text-center py-8 text-muted-foreground">No completed trading days yet</div>
                )}
                {(dashboard?.recent_profits || []).map((report, index) => (
                  <div key={index} className="flex items-center justify-between p-4 border rounded-lg">
                    <div>
                      <div className="font-medium">{new Date(report.date).toLocaleDateString()}</div>
                      <div className="text-sm text-muted-foreground">Start: ${formatUsd(parseFloat(report.start_amount))}</div>
                    </div>
                    <div className="text-right">
                      <div className={`font-bold ${pnlClass(report.profit_amount)}`}>{signed(parseFloat(report.profit_amount))}</div>
                      <PercentBadge value={parseFloat(report.profit_percent)} />
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Market movers */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><Flame className="h-5 w-5 text-amber-500" /> Top Movers (24h)</CardTitle>
              <CardDescription>Biggest USDT-pair gainers on Binance</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {movers.length === 0 && <div className="text-center py-8 text-muted-foreground">Market data unavailable right now</div>}
                {movers.map((coin) => (
                  <div key={coin.symbol_name} className="flex items-center justify-between gap-3 p-3 border rounded-lg">
                    <div className="flex items-center gap-3 min-w-0">
                      <CoinIcon symbol={coin.symbol_name} size={32} />
                      <div className="font-medium truncate">{coin.symbol_name.replace(/USDT$/, '')}<span className="text-muted-foreground">/USDT</span></div>
                    </div>
                    <div className="text-right">
                      <div className="font-medium">${formatPrice(coin.price)}</div>
                      <div className={`text-sm font-semibold ${pnlClass(coin.change_percent)}`}>
                        {Number(coin.change_percent) >= 0 ? '+' : ''}{Number(coin.change_percent).toFixed(2)}%
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

function Detail({ label, value, sub }) {
  return (
    <div>
      <div className="text-muted-foreground">{label}</div>
      <div className="font-medium break-words">{value}</div>
      {sub && <div className="text-xs text-muted-foreground">{sub}</div>}
    </div>
  );
}
