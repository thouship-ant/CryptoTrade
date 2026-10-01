'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import Navigation from '@/components/Navigation';
import CoinIcon from '@/components/CoinIcon';
import TablePagination from '@/components/TablePagination';
import PeriodFilter, { periodQuery, periodReady } from '@/components/PeriodFilter';
import { getApiBaseUrl, safeJson, formatUsd, formatPrice, formatQty, formatDateTime } from '@/lib/apiConfig';

const DailyProfitChart = dynamic(() => import('@/components/DailyProfitChart'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-72">
      <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary"></div>
    </div>
  ),
});

const DEFAULT_PAGE_SIZE = 10;

const CHART_PERIODS = [
  { value: '1d', label: '1D' },
  { value: '1w', label: '1W' },
  { value: '1m', label: '1M' },
  { value: '3m', label: '3M' },
  { value: '6m', label: '6M' },
  { value: '1y', label: '1Y' },
];

const pnlClass = (v) => (Number(v) >= 0 ? 'text-green-600' : 'text-red-600');
const signed = (v) => `${Number(v) >= 0 ? '+' : '-'}$${formatUsd(Math.abs(Number(v) || 0))}`;

function Spinner() {
  return (
    <div className="flex justify-center py-8">
      <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary"></div>
    </div>
  );
}

function StatTile({ label, value, className = '' }) {
  return (
    <div className="rounded-lg border p-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className={`text-lg font-bold whitespace-nowrap ${className}`}>{value}</div>
    </div>
  );
}

export default function ReportsPage() {
  const router = useRouter();
  const [userId, setUserId] = useState('');
  const [userName, setUserName] = useState('');
  const [activeTab, setActiveTab] = useState('trades');

  // Trade history
  const [period, setPeriod] = useState('current_month');
  const [customFrom, setCustomFrom] = useState('');
  const [customTo, setCustomTo] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [trades, setTrades] = useState([]);
  const [tradesLoading, setTradesLoading] = useState(true);
  const [tradesError, setTradesError] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);
  const [totalPages, setTotalPages] = useState(1);
  const [totalTrades, setTotalTrades] = useState(0);
  const [summary, setSummary] = useState(null);
  const [selectedTrade, setSelectedTrade] = useState(null);

  // Coin-wise P/L
  const [symbolPnl, setSymbolPnl] = useState([]);
  const [symbolLoading, setSymbolLoading] = useState(false);
  const [symbolPage, setSymbolPage] = useState(1);
  const [symbolPageSize, setSymbolPageSize] = useState(DEFAULT_PAGE_SIZE);

  // Daily profit chart
  const [chartPeriod, setChartPeriod] = useState('1m');
  const [chartData, setChartData] = useState([]);
  const [chartGranularity, setChartGranularity] = useState('day');
  const [chartLoading, setChartLoading] = useState(false);
  const [chartLoaded, setChartLoaded] = useState(false);

  useEffect(() => {
    const storedUserId = localStorage.getItem('user_id');
    if (!storedUserId) {
      router.push('/');
      return;
    }
    setUserId(storedUserId);
    setUserName(localStorage.getItem('full_name') || '');
  }, [router]);

  const fetchTrades = useCallback(async () => {
    if (!userId || !periodReady(period, customFrom, customTo)) return;
    setTradesLoading(true);
    setTradesError('');
    try {
      const query = periodQuery(period, customFrom, customTo);
      const [tradesRes, summaryRes] = await Promise.all([
        fetch(`${getApiBaseUrl()}/api/trades/${userId}?${query}&page=${page}&limit=${pageSize}&status=${statusFilter}`),
        fetch(`${getApiBaseUrl()}/api/trades/${userId}/pnl-summary?${query}`),
      ]);
      if (!tradesRes.ok) throw new Error('trades');
      const data = await safeJson(tradesRes);
      setTrades(data.trades || []);
      setTotalPages(data.total_pages || 1);
      setTotalTrades(data.total || 0);
      setSummary(summaryRes.ok ? await safeJson(summaryRes) : null);
    } catch (error) {
      console.error('Error fetching trades:', error);
      setTradesError('Could not load trade history. Please try again.');
    } finally {
      setTradesLoading(false);
    }
  }, [userId, period, customFrom, customTo, page, pageSize, statusFilter]);

  useEffect(() => { fetchTrades(); }, [fetchTrades]);

  useEffect(() => {
    if (!userId || activeTab !== 'pnl') return;
    (async () => {
      setSymbolLoading(true);
      try {
        const response = await fetch(`${getApiBaseUrl()}/api/symbol-pnl/${userId}`);
        const data = await safeJson(response);
        setSymbolPnl(data.symbol_pnl || []);
      } catch (error) {
        console.error('Error fetching symbol P&L:', error);
      } finally {
        setSymbolLoading(false);
      }
    })();
  }, [userId, activeTab]);

  useEffect(() => {
    if (!userId || activeTab !== 'chart') return;
    (async () => {
      setChartLoading(true);
      try {
        const response = await fetch(`${getApiBaseUrl()}/api/reports/daily-profit/${userId}?period=${chartPeriod}`);
        const data = await safeJson(response);
        setChartData(data.data || []);
        setChartGranularity(data.granularity || 'day');
      } catch (error) {
        console.error('Error fetching daily profit:', error);
      } finally {
        setChartLoading(false);
        setChartLoaded(true);
      }
    })();
  }, [userId, activeTab, chartPeriod]);

  const resetPage = () => setPage(1);
  const symbolRows = symbolPnl.slice((symbolPage - 1) * symbolPageSize, symbolPage * symbolPageSize);

  return (
    <div className="min-h-screen bg-background">
      <Navigation userName={userName} />

      <div className="container mx-auto px-4 py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-bold">Trading Reports</h1>
          <p className="text-muted-foreground mt-1">Performance of your bot, trade by trade and coin by coin</p>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid h-auto w-full grid-cols-1 gap-1 sm:grid-cols-3 mb-6">
            <TabsTrigger value="trades">Trade History</TabsTrigger>
            <TabsTrigger value="pnl">Cumulative P/L by Coin</TabsTrigger>
            <TabsTrigger value="chart">Daily Profit Chart</TabsTrigger>
          </TabsList>

          {/* Trade History */}
          <TabsContent value="trades">
            <Card>
              <CardHeader className="gap-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <CardTitle>Trade History</CardTitle>
                    <CardDescription>{totalTrades} trade{totalTrades === 1 ? '' : 's'} found</CardDescription>
                  </div>
                  <div className="flex items-center gap-2 w-full sm:w-auto flex-wrap">
                    <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v); resetPage(); }}>
                      <SelectTrigger className="flex-1 min-w-0 sm:flex-none sm:w-[120px] text-xs sm:text-sm">
                        <SelectValue placeholder="Status" />
                      </SelectTrigger>
                      <SelectContent className="bg-popover">
                        <SelectItem value="all">All</SelectItem>
                        <SelectItem value="open">Open</SelectItem>
                        <SelectItem value="closed">Closed</SelectItem>
                      </SelectContent>
                    </Select>
                    <PeriodFilter
                      period={period} onPeriodChange={(v) => { setPeriod(v); resetPage(); }}
                      from={customFrom} to={customTo}
                      onFromChange={(v) => { setCustomFrom(v); resetPage(); }}
                      onToChange={(v) => { setCustomTo(v); resetPage(); }}
                    />
                  </div>
                </div>
                {summary && (
                  <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                    <StatTile label="Net P/L (closed)" value={signed(summary.net_pnl)} className={pnlClass(summary.net_pnl)} />
                    <StatTile label="Win rate" value={summary.win_rate == null ? '-' : `${summary.win_rate}% (${summary.winning_trades}/${summary.closed_trades})`} />
                    <StatTile label="Max profit" value={summary.max_profit == null ? '-' : signed(summary.max_profit)} className="text-green-600" />
                    <StatTile label="Max loss" value={summary.max_loss == null ? '-' : signed(summary.max_loss)} className="text-red-600" />
                  </div>
                )}
              </CardHeader>
              <CardContent>
                {!periodReady(period, customFrom, customTo) ? (
                  <div className="text-center py-8 text-muted-foreground">Pick both a from and to date to see trades for that range</div>
                ) : tradesLoading ? (
                  <Spinner />
                ) : tradesError ? (
                  <div className="text-center py-8 text-red-600">{tradesError}</div>
                ) : trades.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">No trades found for this period</div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b">
                          <th className="text-left p-3 font-medium">Pair</th>
                          <th className="text-left p-3 font-medium">Side</th>
                          <th className="text-right p-3 font-medium">Qty</th>
                          <th className="text-right p-3 font-medium">Entry</th>
                          <th className="text-right p-3 font-medium">Exit / Current</th>
                          <th className="text-right p-3 font-medium">P&amp;L</th>
                          <th className="text-center p-3 font-medium">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {trades.map((t) => (
                          <tr key={t.signal_id} className="border-b hover:bg-accent transition-colors cursor-pointer" onClick={() => setSelectedTrade(t)}>
                            <td className="p-3">
                              <div className="flex items-center gap-3">
                                <CoinIcon symbol={t.symbol_name} size={28} />
                                <div>
                                  <div className="font-medium">{t.symbol_name}</div>
                                  <div className="text-xs text-muted-foreground whitespace-nowrap">{formatDateTime(t.created_DateTime)}</div>
                                </div>
                              </div>
                            </td>
                            <td className="p-3"><Badge variant={t.side === 'LONG' ? 'default' : 'secondary'}>{t.side}</Badge></td>
                            <td className="p-3 text-right">{formatQty(t.quantity)}</td>
                            <td className="p-3 text-right">${formatPrice(t.entry_price)}</td>
                            <td className="p-3 text-right">${formatPrice(t.exit_price ?? t.current_price ?? t.entry_price)}</td>
                            <td className={`p-3 text-right font-semibold whitespace-nowrap ${pnlClass(t.PandL)}`}>
                              {signed(t.PandL)}
                              <div className="text-xs font-normal">{Number(t.PandL_percent || 0).toFixed(2)}%</div>
                            </td>
                            <td className="p-3 text-center">
                              <Badge variant={t.is_Active ? 'outline' : 'secondary'}>{t.is_Active ? 'Open' : 'Closed'}</Badge>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
                {!tradesLoading && (
                  <div className="mt-6">
                    <TablePagination
                      page={page} totalPages={totalPages} onPageChange={setPage}
                      pageSize={pageSize} onPageSizeChange={(size) => { setPageSize(size); setPage(1); }}
                    />
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Cumulative P/L by Coin */}
          <TabsContent value="pnl">
            <Card>
              <CardHeader>
                <CardTitle>Cumulative P/L by Coin</CardTitle>
                <CardDescription>All-time realized P&amp;L of closed trades, per pair</CardDescription>
              </CardHeader>
              <CardContent>
                {symbolLoading ? (
                  <Spinner />
                ) : symbolPnl.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">No closed trades yet</div>
                ) : (
                  <>
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead>
                          <tr className="border-b">
                            <th className="text-left p-3 font-medium">Pair</th>
                            <th className="text-right p-3 font-medium">Trades</th>
                            <th className="text-right p-3 font-medium">Win rate</th>
                            <th className="text-right p-3 font-medium">Total P&amp;L</th>
                          </tr>
                        </thead>
                        <tbody>
                          {symbolRows.map((s) => (
                            <tr key={s.symbol_name} className="border-b">
                              <td className="p-3">
                                <div className="flex items-center gap-3">
                                  <CoinIcon symbol={s.symbol_name} size={28} />
                                  <span className="font-medium">{s.symbol_name}</span>
                                </div>
                              </td>
                              <td className="p-3 text-right">{s.total_trades}</td>
                              <td className="p-3 text-right">{s.total_trades ? Math.round((Number(s.winning_trades) / s.total_trades) * 100) : 0}%</td>
                              <td className={`p-3 text-right font-semibold ${pnlClass(s.total_pnl)}`}>{signed(s.total_pnl)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <div className="mt-6">
                      <TablePagination
                        page={symbolPage} totalPages={Math.ceil(symbolPnl.length / symbolPageSize)} onPageChange={setSymbolPage}
                        pageSize={symbolPageSize} onPageSizeChange={(size) => { setSymbolPageSize(size); setSymbolPage(1); }}
                      />
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Daily Profit Chart */}
          <TabsContent value="chart">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between flex-wrap gap-2">
                <div>
                  <CardTitle>Daily Profit</CardTitle>
                  <CardDescription>
                    {chartGranularity === 'hour' ? 'Hour-by-hour P&L for today' : 'Day-by-day P&L over the selected period'}
                  </CardDescription>
                </div>
                <div className="flex gap-1">
                  {CHART_PERIODS.map((p) => (
                    <Button key={p.value} size="sm" variant={chartPeriod === p.value ? 'default' : 'outline'} onClick={() => setChartPeriod(p.value)}>
                      {p.label}
                    </Button>
                  ))}
                </div>
              </CardHeader>
              <CardContent>
                {chartLoading || !chartLoaded ? (
                  <div className="flex items-center justify-center h-72">
                    <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary"></div>
                  </div>
                ) : (
                  <DailyProfitChart data={chartData} granularity={chartGranularity} />
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      {/* Trade Detail */}
      <Dialog open={!!selectedTrade} onOpenChange={() => setSelectedTrade(null)}>
        <DialogContent className="max-w-xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {selectedTrade && <CoinIcon symbol={selectedTrade.symbol_name} size={24} />}
              {selectedTrade?.symbol_name}
              <Badge variant={selectedTrade?.side === 'LONG' ? 'default' : 'secondary'}>{selectedTrade?.side}</Badge>
            </DialogTitle>
            <DialogDescription>{selectedTrade?.is_Active ? 'Open position' : 'Closed trade'}</DialogDescription>
          </DialogHeader>
          {selectedTrade && (
            <div className="grid grid-cols-2 gap-4 text-sm">
              <Field label="Quantity" value={formatQty(selectedTrade.quantity)} />
              <Field label="Leverage" value={`${selectedTrade.leverage}x`} />
              <Field label="Entry price" value={`$${formatPrice(selectedTrade.entry_price)}`} />
              <Field label={selectedTrade.is_Active ? 'Current price' : 'Exit price'} value={`$${formatPrice(selectedTrade.exit_price ?? selectedTrade.current_price ?? selectedTrade.entry_price)}`} />
              <Field label="Target" value={selectedTrade.target_price ? `$${formatPrice(selectedTrade.target_price)}` : '-'} />
              <Field label="Stoploss" value={selectedTrade.stoploss_price ? `$${formatPrice(selectedTrade.stoploss_price)}` : '-'} />
              <Field label="Commission" value={`$${formatUsd(selectedTrade.commission, 4)}`} />
              <div>
                <div className="text-muted-foreground">{selectedTrade.is_Active ? 'Unrealized' : 'Realized'} P&amp;L</div>
                <div className={`font-semibold ${pnlClass(selectedTrade.PandL)}`}>
                  {signed(selectedTrade.PandL)} ({Number(selectedTrade.PandL_percent || 0).toFixed(2)}%)
                </div>
              </div>
              <Field label="Opened" value={formatDateTime(selectedTrade.created_DateTime)} />
              <Field label="Closed" value={selectedTrade.is_Active ? '-' : formatDateTime(selectedTrade.last_update_DateTime)} />
              <div className="col-span-2">
                <div className="text-muted-foreground">Entry signal</div>
                <div className="mt-1 rounded-lg bg-muted p-3">{selectedTrade.buy_reason || selectedTrade.signal_type || '-'}</div>
              </div>
              {!selectedTrade.is_Active && (
                <div className="col-span-2">
                  <div className="text-muted-foreground">Exit reason</div>
                  <div className="mt-1 rounded-lg bg-muted p-3">{selectedTrade.sell_reason || '-'}</div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

function Field({ label, value }) {
  return (
    <div>
      <div className="text-muted-foreground">{label}</div>
      <div className="font-medium break-words">{value}</div>
    </div>
  );
}
