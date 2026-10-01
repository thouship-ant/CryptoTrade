'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import Navigation from '@/components/Navigation';
import CoinIcon from '@/components/CoinIcon';
import TablePagination from '@/components/TablePagination';
import PeriodFilter, { periodQuery, periodReady } from '@/components/PeriodFilter';
import { getApiBaseUrl, safeJson, formatUsd, formatPrice, formatQty, formatDateTime } from '@/lib/apiConfig';

const DEFAULT_PAGE_SIZE = 10;

export default function OrdersPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [orders, setOrders] = useState([]);
  const [summary, setSummary] = useState(null);
  const [userName, setUserName] = useState('');
  const [period, setPeriod] = useState('today');
  const [customFrom, setCustomFrom] = useState('');
  const [customTo, setCustomTo] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);

  const fetchOrders = useCallback(async (uid) => {
    setLoading(true);
    setError('');
    try {
      const query = periodQuery(period, customFrom, customTo);
      const [ordersRes, summaryRes] = await Promise.all([
        fetch(`${getApiBaseUrl()}/api/order-reports/${uid}?${query}`),
        fetch(`${getApiBaseUrl()}/api/trades/${uid}/pnl-summary?${query}`),
      ]);
      if (!ordersRes.ok) throw new Error('Could not load orders');
      const ordersData = await safeJson(ordersRes);
      setOrders(ordersData.orders || []);
      setSummary(summaryRes.ok ? await safeJson(summaryRes) : null);
      setPage(1);
    } catch (err) {
      console.error('Error fetching orders:', err);
      setError('Could not load orders. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [period, customFrom, customTo]);

  useEffect(() => {
    const storedUserId = localStorage.getItem('user_id');
    if (!storedUserId) {
      router.push('/');
      return;
    }
    setUserName(localStorage.getItem('full_name') || '');
    // Wait for both ends of a custom range rather than querying a half-picked one.
    if (periodReady(period, customFrom, customTo)) fetchOrders(storedUserId);
  }, [router, period, customFrom, customTo, fetchOrders]);

  const filtered = typeFilter === 'all' ? orders : orders.filter((o) => o.type === typeFilter);
  const totalValue = filtered.reduce((sum, o) => sum + (parseFloat(o.order_value) || 0), 0);
  const pnl = summary?.net_pnl ?? 0;

  return (
    <div className="min-h-screen bg-background">
      <Navigation userName={userName} />

      <div className="container mx-auto px-4 py-8">
        <div className="mb-6 flex items-center justify-between flex-wrap gap-3">
          <div>
            <h1 className="text-3xl font-bold">Order Reports</h1>
            <p className="text-muted-foreground mt-1">Every Binance order your bot placed</p>
          </div>
          <div className="flex items-center gap-2 w-full sm:w-auto flex-wrap">
            <Select value={typeFilter} onValueChange={(v) => { setTypeFilter(v); setPage(1); }}>
              <SelectTrigger className="flex-1 min-w-0 sm:flex-none sm:w-[120px] text-xs sm:text-sm">
                <SelectValue placeholder="Side" />
              </SelectTrigger>
              <SelectContent className="bg-popover">
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="Buy">Buy</SelectItem>
                <SelectItem value="Sell">Sell</SelectItem>
              </SelectContent>
            </Select>
            <PeriodFilter
              period={period} onPeriodChange={setPeriod}
              from={customFrom} to={customTo} onFromChange={setCustomFrom} onToChange={setCustomTo}
            />
          </div>
        </div>

        <Card>
          <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-4">
            <div>
              <CardTitle>Orders</CardTitle>
              <CardDescription>{filtered.length} order{filtered.length === 1 ? '' : 's'} found</CardDescription>
            </div>
            <div className="flex flex-wrap gap-x-6 gap-y-2">
              <div className="text-right">
                <div className="text-xs text-muted-foreground">Realized P/L (closed trades)</div>
                <div className={`text-lg font-bold whitespace-nowrap ${pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {pnl >= 0 ? '+' : '-'}${formatUsd(Math.abs(pnl))}
                </div>
              </div>
              <div className="text-right">
                <div className="text-xs text-muted-foreground">No. of Orders</div>
                <div className="text-lg font-bold">{filtered.length}</div>
              </div>
              <div className="text-right">
                <div className="text-xs text-muted-foreground">Total Value Traded</div>
                <div className="text-lg font-bold whitespace-nowrap">${formatUsd(totalValue)}</div>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {!periodReady(period, customFrom, customTo) ? (
              <div className="text-center py-8 text-muted-foreground">Pick both a from and to date to see orders for that range</div>
            ) : loading ? (
              <div className="flex justify-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary"></div>
              </div>
            ) : error ? (
              <div className="text-center py-8 text-red-600">{error}</div>
            ) : filtered.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">No orders found for this period</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left p-4 font-medium">Date</th>
                      <th className="text-left p-4 font-medium">Pair</th>
                      <th className="text-left p-4 font-medium">Side</th>
                      <th className="text-right p-4 font-medium">Quantity</th>
                      <th className="text-right p-4 font-medium">Price</th>
                      <th className="text-right p-4 font-medium">Value</th>
                      <th className="text-center p-4 font-medium">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.slice((page - 1) * pageSize, page * pageSize).map((order, index) => (
                      <tr key={index} className="border-b hover:bg-accent transition-colors">
                        <td className="p-4 text-sm whitespace-nowrap">{formatDateTime(order.date)}</td>
                        <td className="p-4">
                          <div className="flex items-center gap-3">
                            <CoinIcon symbol={order.symbol} size={32} />
                            <div>
                              <div className="font-medium">{order.symbol}</div>
                              <div className="text-xs text-muted-foreground">{order.position_side === 'SHORT' ? 'Short position' : 'Long position'}</div>
                            </div>
                          </div>
                        </td>
                        <td className="p-4">
                          <Badge variant={order.type === 'Buy' ? 'default' : 'secondary'}>{order.type}</Badge>
                        </td>
                        <td className="p-4 text-right">{formatQty(order.quantity)}</td>
                        <td className="p-4 text-right">${formatPrice(order.avg_price)}</td>
                        <td className="p-4 text-right font-medium">${formatUsd(order.order_value)}</td>
                        <td className="p-4 text-center">
                          <Badge variant="outline">{order.status}</Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {!loading && (
              <div className="mt-6">
                <TablePagination
                  page={page}
                  totalPages={Math.max(1, Math.ceil(filtered.length / pageSize))}
                  onPageChange={setPage}
                  pageSize={pageSize}
                  onPageSizeChange={(size) => { setPageSize(size); setPage(1); }}
                />
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
