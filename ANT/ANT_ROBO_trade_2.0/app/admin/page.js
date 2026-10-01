'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Mail, Search, Check, X } from 'lucide-react';
import Navigation from '@/components/Navigation';
import TablePagination from '@/components/TablePagination';
import PeriodFilter, { periodQuery, periodReady } from '@/components/PeriodFilter';
import { useAlert } from '@/components/AlertProvider';
import { getApiBaseUrl, safeJson, formatUsd, formatDateTime } from '@/lib/apiConfig';

const pnlClass = (v) => (Number(v) >= 0 ? 'text-green-600' : 'text-red-600');
const signed = (v) => `${Number(v) >= 0 ? '+' : '-'}$${formatUsd(Math.abs(Number(v) || 0))}`;
const shortHash = (h) => (h ? `${h.slice(0, 10)}...${h.slice(-6)}` : '-');

function Spinner() {
  return (
    <div className="flex justify-center py-8">
      <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary"></div>
    </div>
  );
}

function StatusBadge({ status }) {
  const variant = status === 'pending' ? 'secondary' : status === 'approved' || status === 'completed' ? 'default' : 'destructive';
  return <Badge variant={variant}>{status}</Badge>;
}

export default function AdminPage() {
  const router = useRouter();
  const alert = useAlert();
  const [adminId, setAdminId] = useState('');
  const [userName, setUserName] = useState('');
  const [allowed, setAllowed] = useState(false);
  const [tab, setTab] = useState('users');

  useEffect(() => {
    const storedUserId = localStorage.getItem('user_id');
    if (!storedUserId) {
      router.push('/');
      return;
    }
    setUserName(localStorage.getItem('full_name') || '');
    // The role comes from the server, never from localStorage (which the user controls).
    fetch(`${getApiBaseUrl()}/api/config/${storedUserId}`)
      .then(safeJson)
      .then((data) => {
        if ((data.role || '').toLowerCase() === 'admin') {
          setAdminId(storedUserId);
          setAllowed(true);
        } else {
          router.push('/dashboard');
        }
      })
      .catch(() => router.push('/dashboard'));
  }, [router]);

  if (!allowed) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <Navigation userName={userName} />
      <div className="container mx-auto px-4 py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-bold">Admin</h1>
          <p className="text-muted-foreground mt-1">Users, deposits, withdrawals and platform settings</p>
        </div>

        <Tabs value={tab} onValueChange={setTab}>
          <TabsList className="grid h-auto w-full grid-cols-2 gap-1 sm:grid-cols-3 lg:grid-cols-6 mb-6">
            <TabsTrigger value="users">Users</TabsTrigger>
            <TabsTrigger value="pnl">P&amp;L Report</TabsTrigger>
            <TabsTrigger value="deposits">Deposits</TabsTrigger>
            <TabsTrigger value="withdrawals">Withdrawals</TabsTrigger>
            <TabsTrigger value="signals">Signal P&amp;L</TabsTrigger>
            <TabsTrigger value="settings">Deposit Address</TabsTrigger>
          </TabsList>

          <TabsContent value="users"><UsersTab adminId={adminId} mode="users" alert={alert} /></TabsContent>
          <TabsContent value="pnl"><UsersTab adminId={adminId} mode="pnl" alert={alert} /></TabsContent>
          <TabsContent value="deposits"><RequestsTab adminId={adminId} kind="deposits" alert={alert} /></TabsContent>
          <TabsContent value="withdrawals"><RequestsTab adminId={adminId} kind="withdrawals" alert={alert} /></TabsContent>
          <TabsContent value="signals"><SignalsTab adminId={adminId} /></TabsContent>
          <TabsContent value="settings"><DepositSettingsTab adminId={adminId} alert={alert} /></TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- Users / P&L Report
function UsersTab({ adminId, mode, alert }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [emailTarget, setEmailTarget] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/admin/dashboard/${adminId}?page=${page}&limit=${pageSize}&search=${encodeURIComponent(search)}`);
      const data = await safeJson(response);
      if (!response.ok) throw new Error(data.detail || 'load failed');
      setUsers(data.users || []);
      setTotalPages(data.total_pages || 1);
      setTotal(data.total || 0);
    } catch (error) {
      alert.error(String(error.message || 'Could not load users'));
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [adminId, page, pageSize, search]);

  useEffect(() => { load(); }, [load]);

  return (
    <Card>
      <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-3">
        <div>
          <CardTitle>{mode === 'users' ? 'Users' : 'P&L Report'}</CardTitle>
          <CardDescription>{total} registered user{total === 1 ? '' : 's'}</CardDescription>
        </div>
        <form className="flex gap-2 w-full sm:w-auto" onSubmit={(e) => { e.preventDefault(); setPage(1); setSearch(searchInput.trim()); }}>
          <Input value={searchInput} onChange={(e) => setSearchInput(e.target.value)} placeholder="Search name, username, email" className="sm:w-64" />
          <Button type="submit" variant="outline" size="icon" aria-label="Search"><Search className="h-4 w-4" /></Button>
        </form>
      </CardHeader>
      <CardContent>
        {loading ? <Spinner /> : users.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">No users found</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left p-3 font-medium">User</th>
                  {mode === 'users' ? (
                    <>
                      <th className="text-left p-3 font-medium">Plan</th>
                      <th className="text-right p-3 font-medium">Power</th>
                      <th className="text-right p-3 font-medium">Earnings</th>
                      <th className="text-right p-3 font-medium">Activation</th>
                      <th className="text-center p-3 font-medium">Binance</th>
                      <th className="text-center p-3 font-medium">Bot</th>
                      <th className="text-left p-3 font-medium">Joined</th>
                      <th className="p-3"></th>
                    </>
                  ) : (
                    <>
                      <th className="text-right p-3 font-medium">Open</th>
                      <th className="text-right p-3 font-medium">Today</th>
                      <th className="text-right p-3 font-medium">Month</th>
                      <th className="text-right p-3 font-medium">Overall</th>
                      <th className="text-right p-3 font-medium">Power bought</th>
                      <th className="text-right p-3 font-medium">P/L per power</th>
                    </>
                  )}
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.user_id} className="border-b hover:bg-accent/50">
                    <td className="p-3">
                      <div className="font-medium flex items-center gap-2">
                        {u.full_name}
                        {u.role?.toLowerCase() === 'admin' && <Badge variant="outline">admin</Badge>}
                        {!u.is_verified && <Badge variant="secondary">unverified</Badge>}
                      </div>
                      <div className="text-xs text-muted-foreground">@{u.username} &middot; {u.email_id}</div>
                    </td>
                    {mode === 'users' ? (
                      <>
                        <td className="p-3">{u.current_plan || <span className="text-muted-foreground">None</span>}</td>
                        <td className="p-3 text-right">{Number(u.energy_power).toLocaleString()}</td>
                        <td className="p-3 text-right">${formatUsd(u.wallet_balance)}</td>
                        <td className="p-3 text-right">${formatUsd(u.activation_balance)}</td>
                        <td className="p-3 text-center">{u.has_api_keys ? <Check className="h-4 w-4 text-green-600 inline" /> : <X className="h-4 w-4 text-muted-foreground inline" />}</td>
                        <td className="p-3 text-center"><Badge variant={u.is_trading_active && u.has_api_keys ? 'default' : 'secondary'}>{u.is_trading_active && u.has_api_keys ? 'on' : 'off'}</Badge></td>
                        <td className="p-3 whitespace-nowrap text-muted-foreground">{u.created_date ? new Date(u.created_date).toLocaleDateString() : '-'}</td>
                        <td className="p-3">
                          <Button size="icon" variant="ghost" aria-label={`Email ${u.username}`} onClick={() => setEmailTarget(u)}><Mail className="h-4 w-4" /></Button>
                        </td>
                      </>
                    ) : (
                      <>
                        <td className="p-3 text-right">{u.open_positions}</td>
                        <td className={`p-3 text-right font-medium ${pnlClass(u.today_pnl)}`}>{signed(u.today_pnl)}</td>
                        <td className={`p-3 text-right font-medium ${pnlClass(u.month_pnl)}`}>{signed(u.month_pnl)}</td>
                        <td className={`p-3 text-right font-semibold ${pnlClass(u.overall_pnl)}`}>{signed(u.overall_pnl)}</td>
                        <td className="p-3 text-right">{Number(u.total_power_purchased).toLocaleString()}</td>
                        <td className="p-3 text-right">{u.profit_per_power_percent == null ? '-' : `${u.profit_per_power_percent}%`}</td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="mt-6">
          <TablePagination page={page} totalPages={totalPages} onPageChange={setPage} pageSize={pageSize} onPageSizeChange={(s) => { setPageSize(s); setPage(1); }} />
        </div>
      </CardContent>

      <EmailDialog adminId={adminId} target={emailTarget} onClose={() => setEmailTarget(null)} alert={alert} />
    </Card>
  );
}

function EmailDialog({ adminId, target, onClose, alert }) {
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [sendAt, setSendAt] = useState('');
  const [sending, setSending] = useState(false);

  useEffect(() => {
    if (target) { setSubject(''); setBody(''); setSendAt(''); }
  }, [target]);

  const send = async (e) => {
    e.preventDefault();
    if (!subject.trim() || !body.trim()) return alert.warning('Enter a subject and a message');
    setSending(true);
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/admin/send-email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          admin_user_id: adminId, target_user_id: target.user_id, subject: subject.trim(), body: body.trim(),
          send_at: sendAt ? new Date(sendAt).toISOString().slice(0, 19) : null,
        }),
      });
      const data = await safeJson(response);
      if (!response.ok) return alert.error((typeof data.detail === 'string' && data.detail) || 'Failed to send');
      if (data.sent === false) alert.warning('Email could not be sent - check SMTP settings');
      else alert.success(data.message || 'Done');
      onClose();
    } catch {
      alert.error('Server error. Please try again.');
    } finally {
      setSending(false);
    }
  };

  return (
    <Dialog open={!!target} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Email {target?.full_name}</DialogTitle>
          <DialogDescription>{target?.email_id}</DialogDescription>
        </DialogHeader>
        <form onSubmit={send} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="em_subject">Subject</Label>
            <Input id="em_subject" value={subject} onChange={(e) => setSubject(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="em_body">Message</Label>
            <Textarea id="em_body" rows={6} value={body} onChange={(e) => setBody(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="em_at">Send later (optional)</Label>
            <Input id="em_at" type="datetime-local" value={sendAt} onChange={(e) => setSendAt(e.target.value)} />
          </div>
          <Button type="submit" className="w-full" disabled={sending}>{sending ? 'Sending...' : sendAt ? 'Schedule email' : 'Send now'}</Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------- Deposits / Withdrawals
function RequestsTab({ adminId, kind, alert }) {
  const isDeposits = kind === 'deposits';
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(5);
  const [totalPages, setTotalPages] = useState(1);
  const [status, setStatus] = useState('pending');
  const [period, setPeriod] = useState('all');
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [action, setAction] = useState(null); // { row, action }
  const [note, setNote] = useState('');
  const [txHash, setTxHash] = useState('');
  const [processing, setProcessing] = useState(false);

  const load = useCallback(async () => {
    if (period !== 'all' && !periodReady(period, from, to)) return;
    setLoading(true);
    try {
      const range = period === 'all' ? 'period=all' : periodQuery(period, from, to);
      const statusParam = status !== 'all' ? `&status=${status}` : '';
      const response = await fetch(`${getApiBaseUrl()}/api/admin/${kind}/${adminId}?${range}${statusParam}&page=${page}&limit=${pageSize}`);
      const data = await safeJson(response);
      if (!response.ok) throw new Error(data.detail || 'load failed');
      setRows(data[kind] || []);
      setTotalPages(data.total_pages || 1);
    } catch (error) {
      alert.error(String(error.message || 'Could not load requests'));
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [adminId, kind, page, pageSize, status, period, from, to]);

  useEffect(() => { load(); }, [load]);

  const submit = async () => {
    const { row, action: act } = action;
    setProcessing(true);
    try {
      const body = { admin_user_id: adminId, action: act, admin_note: note.trim() || null };
      if (!isDeposits && act === 'complete') body.tx_hash = txHash.trim() || null;
      const response = await fetch(`${getApiBaseUrl()}/api/admin/${kind}/${row.id}/process`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
      });
      const data = await safeJson(response);
      if (!response.ok) return alert.error((typeof data.detail === 'string' && data.detail) || 'Failed');
      alert.success(data.message);
      setAction(null);
      load();
    } catch {
      alert.error('Server error. Please try again.');
    } finally {
      setProcessing(false);
    }
  };

  const yes = isDeposits ? 'approve' : 'complete';
  return (
    <Card>
      <CardHeader className="gap-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle>{isDeposits ? 'USDT Deposit Claims' : 'Withdrawal Requests'}</CardTitle>
            <CardDescription>
              {isDeposits ? 'Match each transaction hash on BscScan (amount, token, destination) before approving.' : 'Send the USDT on-chain, then mark the request completed.'}
            </CardDescription>
          </div>
          <div className="flex items-center gap-2 w-full sm:w-auto flex-wrap">
            <Select value={status} onValueChange={(v) => { setStatus(v); setPage(1); }}>
              <SelectTrigger className="flex-1 sm:flex-none sm:w-[130px] text-xs sm:text-sm"><SelectValue /></SelectTrigger>
              <SelectContent className="bg-popover">
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value={isDeposits ? 'approved' : 'completed'}>{isDeposits ? 'Approved' : 'Completed'}</SelectItem>
                <SelectItem value="rejected">Rejected</SelectItem>
              </SelectContent>
            </Select>
            <Select value={period === 'all' ? 'all' : '__range'} onValueChange={(v) => { if (v === 'all') setPeriod('all'); else setPeriod('current_month'); setPage(1); }}>
              <SelectTrigger className="flex-1 sm:flex-none sm:w-[130px] text-xs sm:text-sm"><SelectValue /></SelectTrigger>
              <SelectContent className="bg-popover">
                <SelectItem value="all">All time</SelectItem>
                <SelectItem value="__range">Date range</SelectItem>
              </SelectContent>
            </Select>
            {period !== 'all' && (
              <PeriodFilter period={period} onPeriodChange={(v) => { setPeriod(v); setPage(1); }} from={from} to={to} onFromChange={setFrom} onToChange={setTo} />
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? <Spinner /> : rows.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">Nothing here</div>
        ) : (
          <div className="space-y-3">
            {rows.map((r) => (
              <div key={r.id} className="rounded-lg border p-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0 space-y-1 text-sm">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-semibold">{r.full_name || r.user_id}</span>
                    <span className="text-muted-foreground">@{r.username}</span>
                    <StatusBadge status={r.status} />
                  </div>
                  <div className="text-lg font-bold">
                    ${formatUsd(r.amount)} <span className="text-xs font-normal text-muted-foreground">USDT{!isDeposits && ` (fee $${formatUsd(r.fee)}, send $${formatUsd(r.amount - r.fee)})`}</span>
                  </div>
                  {isDeposits ? (
                    <div className="text-xs text-muted-foreground break-all">
                      Tx: <a className="text-primary hover:underline" href={`https://bscscan.com/tx/${r.tx_hash}`} target="_blank" rel="noopener noreferrer">{r.tx_hash}</a>
                    </div>
                  ) : (
                    <>
                      <div className="text-xs text-muted-foreground break-all">To: <code>{r.usdt_address}</code></div>
                      {r.tx_hash && <div className="text-xs text-muted-foreground break-all">Paid tx: <a className="text-primary hover:underline" href={`https://bscscan.com/tx/${r.tx_hash}`} target="_blank" rel="noopener noreferrer">{shortHash(r.tx_hash)}</a></div>}
                    </>
                  )}
                  <div className="text-xs text-muted-foreground">Requested {formatDateTime(r.requested_at)}{r.processed_at && ` · processed ${formatDateTime(r.processed_at)}`}</div>
                  {r.admin_note && <div className="text-xs italic text-muted-foreground">Note: {r.admin_note}</div>}
                </div>
                {r.status === 'pending' && (
                  <div className="flex gap-2 shrink-0">
                    <Button size="sm" onClick={() => { setAction({ row: r, action: yes }); setNote(''); setTxHash(''); }}>{isDeposits ? 'Approve' : 'Complete'}</Button>
                    <Button size="sm" variant="outline" onClick={() => { setAction({ row: r, action: 'reject' }); setNote(''); setTxHash(''); }}>Reject</Button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
        <div className="mt-6">
          <TablePagination page={page} totalPages={totalPages} onPageChange={setPage} pageSize={pageSize} onPageSizeChange={(s) => { setPageSize(s); setPage(1); }} />
        </div>
      </CardContent>

      <Dialog open={!!action} onOpenChange={(o) => !o && setAction(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="capitalize">{action?.action} {isDeposits ? 'deposit' : 'withdrawal'}</DialogTitle>
            <DialogDescription>
              {action && (isDeposits
                ? (action.action === 'approve' ? `Credits $${formatUsd(action.row.amount)} to the user's activation balance.` : 'No funds are credited.')
                : (action.action === 'complete' ? 'Confirms you have sent the USDT on-chain.' : `Refunds $${formatUsd(action.row.amount)} to the user's earnings wallet.`))}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {!isDeposits && action?.action === 'complete' && (
              <div className="space-y-2">
                <Label htmlFor="act_hash">Payout transaction hash (optional)</Label>
                <Input id="act_hash" placeholder="0x..." value={txHash} onChange={(e) => setTxHash(e.target.value)} />
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="act_note">Note to user (optional)</Label>
              <Input id="act_note" value={note} onChange={(e) => setNote(e.target.value)} />
            </div>
            <Button className="w-full" variant={action?.action === 'reject' ? 'destructive' : 'default'} disabled={processing} onClick={submit}>
              {processing ? 'Working...' : 'Confirm'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </Card>
  );
}

// ---------------------------------------------------------------- Signal-wise P&L
function SignalsTab({ adminId }) {
  const [period, setPeriod] = useState('current_month');
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!periodReady(period, from, to)) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const response = await fetch(`${getApiBaseUrl()}/api/admin/signal-pnl/${adminId}?${periodQuery(period, from, to)}`);
        const data = await safeJson(response);
        if (!cancelled) setRows(data.signal_pnl || []);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [adminId, period, from, to]);

  return (
    <Card>
      <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-3">
        <div>
          <CardTitle>Signal-wise P&amp;L</CardTitle>
          <CardDescription>Closed trades across all users, grouped by the entry signal</CardDescription>
        </div>
        <div className="flex items-center gap-2 w-full sm:w-auto flex-wrap">
          <PeriodFilter period={period} onPeriodChange={setPeriod} from={from} to={to} onFromChange={setFrom} onToChange={setTo} />
        </div>
      </CardHeader>
      <CardContent>
        {loading ? <Spinner /> : rows.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">No closed trades in this period</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left p-3 font-medium">Signal</th>
                  <th className="text-right p-3 font-medium">Trades</th>
                  <th className="text-right p-3 font-medium">Win rate</th>
                  <th className="text-right p-3 font-medium">P&amp;L</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.buy_reason} className="border-b">
                    <td className="p-3">{r.buy_reason}</td>
                    <td className="p-3 text-right">{r.total_trades}</td>
                    <td className="p-3 text-right">{r.total_trades ? Math.round((Number(r.winning_trades) / r.total_trades) * 100) : 0}%</td>
                    <td className={`p-3 text-right font-semibold ${pnlClass(r.total_pnl)}`}>{signed(r.total_pnl)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------- Deposit address settings
function DepositSettingsTab({ adminId, alert }) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ usdt_address: '', network: 'BEP20 (BSC)', note: '', is_enabled: true });
  const [qrImage, setQrImage] = useState(null);
  const [newQr, setNewQr] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const response = await fetch(`${getApiBaseUrl()}/api/admin/deposit-settings/${adminId}`);
        const data = await safeJson(response);
        if (response.ok) {
          setForm({ usdt_address: data.usdt_address || '', network: data.network || 'BEP20 (BSC)', note: data.note || '', is_enabled: !!data.is_enabled });
          setQrImage(data.qr_image || null);
        }
      } finally {
        setLoading(false);
      }
    })();
  }, [adminId]);

  const onFile = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) return alert.warning('Choose an image file');
    if (file.size > 1_000_000) return alert.warning('Image is too large (max 1 MB)');
    const reader = new FileReader();
    reader.onload = () => setNewQr(reader.result);
    reader.readAsDataURL(file);
  };

  const save = async (e) => {
    e.preventDefault();
    if (!/^0x[0-9a-fA-F]{40}$/.test(form.usdt_address.trim())) return alert.warning('Enter a valid BEP20 (BSC) address');
    setSaving(true);
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/admin/deposit-settings`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ admin_user_id: adminId, ...form, usdt_address: form.usdt_address.trim(), qr_image: newQr || undefined }),
      });
      const data = await safeJson(response);
      if (!response.ok) return alert.error((typeof data.detail === 'string' && data.detail) || 'Failed to save');
      alert.success('Deposit settings saved');
      if (newQr) { setQrImage(newQr); setNewQr(null); }
    } catch {
      alert.error('Server error. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <Spinner />;
  const preview = newQr || qrImage;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Deposit Address</CardTitle>
        <CardDescription>The USDT address users send funds to. Double-check it: every deposit goes here.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={save} className="space-y-5 max-w-xl">
          <div className="flex items-center justify-between rounded-lg border p-3">
            <div>
              <div className="font-medium">Accept deposits</div>
              <div className="text-xs text-muted-foreground">Turn off to hide the Add Funds option for everyone</div>
            </div>
            <Switch checked={form.is_enabled} onCheckedChange={(v) => setForm({ ...form, is_enabled: v })} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="ds_addr">USDT address</Label>
            <Input id="ds_addr" placeholder="0x..." autoComplete="off" spellCheck={false} value={form.usdt_address} onChange={(e) => setForm({ ...form, usdt_address: e.target.value })} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="ds_net">Network</Label>
            <Input id="ds_net" value={form.network} onChange={(e) => setForm({ ...form, network: e.target.value })} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="ds_note">Note shown to users (optional)</Label>
            <Input id="ds_note" value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="ds_qr">QR code image (optional)</Label>
            <Input id="ds_qr" type="file" accept="image/*" onChange={onFile} />
            {preview && (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={preview} alt="Deposit QR preview" className="h-36 w-36 rounded-lg bg-white p-2 object-contain" />
            )}
          </div>
          <Button type="submit" disabled={saving}>{saving ? 'Saving...' : 'Save'}</Button>
        </form>
      </CardContent>
    </Card>
  );
}
