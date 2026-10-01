'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Wallet, Plus, ArrowUpRight, ArrowLeftRight, Copy, Check, TrendingUp, Download, Upload, AlertTriangle } from 'lucide-react';
import Navigation from '@/components/Navigation';
import TransactionList from '@/components/TransactionList';
import TablePagination from '@/components/TablePagination';
import { useAlert } from '@/components/AlertProvider';
import { getApiBaseUrl, safeJson, formatUsd } from '@/lib/apiConfig';

const HISTORY_PAGE_SIZE = 5;
const TX_HASH_RE = /^0x[0-9a-fA-F]{64}$/;
const ADDRESS_RE = /^0x[0-9a-fA-F]{40}$/;

const TYPE_FILTERS = [
  { value: 'all', label: 'All transactions' },
  { value: 'deposit', label: 'Deposits' },
  { value: 'withdrawal', label: 'Withdrawals' },
  { value: 'transfer', label: 'Transfers' },
  { value: 'referal_income', label: 'Referral income' },
  { value: 'bot_purchase', label: 'Bot purchases' },
  { value: 'points_activation', label: 'Power purchases' },
];

function CopyButton({ text, label = 'Copy' }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard blocked - the address is still selectable on screen */
    }
  };
  return (
    <Button type="button" variant="outline" size="sm" onClick={copy} className="gap-1.5 shrink-0">
      {copied ? <Check className="h-4 w-4 text-green-600" /> : <Copy className="h-4 w-4" />}
      {copied ? 'Copied' : label}
    </Button>
  );
}

export default function WalletPage() {
  const router = useRouter();
  const alert = useAlert();
  const [userId, setUserId] = useState('');
  const [userName, setUserName] = useState('');
  const [loading, setLoading] = useState(true);
  const [wallet, setWallet] = useState(null);
  const [limits, setLimits] = useState({ min_withdrawal: 10, withdrawal_fee: 1, min_deposit: 10 });
  const [savedAddress, setSavedAddress] = useState('');
  const [depositInfo, setDepositInfo] = useState(null);

  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyPage, setHistoryPage] = useState(1);
  const [historyPages, setHistoryPages] = useState(1);
  const [typeFilter, setTypeFilter] = useState('all');

  const [dialog, setDialog] = useState(null); // 'deposit' | 'withdraw' | 'transfer'
  const [submitting, setSubmitting] = useState(false);
  const [depositForm, setDepositForm] = useState({ amount: '', tx_hash: '' });
  const [withdrawForm, setWithdrawForm] = useState({ amount: '', usdt_address: '' });
  const [transferAmount, setTransferAmount] = useState('');

  const loadWallet = useCallback(async (uid) => {
    try {
      const [walletRes, infoRes] = await Promise.all([
        fetch(`${getApiBaseUrl()}/api/wallet/${uid}`),
        fetch(`${getApiBaseUrl()}/api/wallet/deposit-info`),
      ]);
      if (walletRes.ok) {
        const data = await safeJson(walletRes);
        setWallet(data.wallet);
        setLimits(data.limits || limits);
        setSavedAddress(data.usdt_address || '');
        setWithdrawForm((f) => ({ ...f, usdt_address: f.usdt_address || data.usdt_address || '' }));
      }
      if (infoRes.ok) setDepositInfo(await safeJson(infoRes));
    } catch (error) {
      console.error('Error loading wallet:', error);
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadHistory = useCallback(async (uid, page, type) => {
    setHistoryLoading(true);
    try {
      const typeParam = type !== 'all' ? `&transaction_type=${type}` : '';
      const response = await fetch(`${getApiBaseUrl()}/api/wallet/${uid}/transactions?page=${page}&limit=${HISTORY_PAGE_SIZE}${typeParam}`);
      const data = await safeJson(response);
      setHistory(data.transactions || []);
      setHistoryPages(data.total_pages || 1);
    } catch (error) {
      console.error('Error loading transactions:', error);
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    const storedUserId = localStorage.getItem('user_id');
    if (!storedUserId) {
      router.push('/');
      return;
    }
    setUserId(storedUserId);
    setUserName(localStorage.getItem('full_name') || '');
    loadWallet(storedUserId);
  }, [router, loadWallet]);

  useEffect(() => {
    if (userId) loadHistory(userId, historyPage, typeFilter);
  }, [userId, historyPage, typeFilter, loadHistory]);

  const refreshAll = () => {
    loadWallet(userId);
    loadHistory(userId, historyPage, typeFilter);
  };

  const post = async (path, body, successMessage) => {
    setSubmitting(true);
    try {
      const response = await fetch(`${getApiBaseUrl()}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await safeJson(response);
      if (!response.ok) {
        alert.error((typeof data.detail === 'string' && data.detail) || 'Request failed');
        return false;
      }
      alert.success(successMessage(data));
      setDialog(null);
      refreshAll();
      return true;
    } catch {
      alert.error('Server error. Please try again.');
      return false;
    } finally {
      setSubmitting(false);
    }
  };

  const submitDeposit = (e) => {
    e.preventDefault();
    const amount = parseFloat(depositForm.amount);
    if (!amount || amount < limits.min_deposit) return alert.warning(`Minimum deposit is ${limits.min_deposit} USDT`);
    if (!TX_HASH_RE.test(depositForm.tx_hash.trim())) return alert.warning('Enter the full transaction hash (0x + 64 characters)');
    post(`/api/wallet/deposit-request/${userId}`, { amount, tx_hash: depositForm.tx_hash.trim() },
      () => 'Deposit submitted - it will be credited once an admin verifies the transfer').then((ok) => {
      if (ok) setDepositForm({ amount: '', tx_hash: '' });
    });
  };

  const submitWithdraw = (e) => {
    e.preventDefault();
    const amount = parseFloat(withdrawForm.amount);
    if (!amount || amount < limits.min_withdrawal) return alert.warning(`Minimum withdrawal is ${limits.min_withdrawal} USDT`);
    if (amount > earnings) return alert.warning('Amount exceeds your earnings balance');
    if (!ADDRESS_RE.test(withdrawForm.usdt_address.trim())) return alert.warning('Enter a valid BEP20 (BSC) address starting with 0x');
    post(`/api/wallet/withdraw/${userId}`, { amount, usdt_address: withdrawForm.usdt_address.trim() },
      (d) => `Withdrawal requested - you will receive ${formatUsd(d.you_receive)} USDT once processed`).then((ok) => {
      if (ok) setWithdrawForm((f) => ({ ...f, amount: '' }));
    });
  };

  const submitTransfer = (e) => {
    e.preventDefault();
    const amount = parseFloat(transferAmount);
    if (!amount || amount <= 0) return alert.warning('Enter a valid amount');
    if (amount > earnings) return alert.warning('Amount exceeds your earnings balance');
    post(`/api/wallet/transfer/${userId}`, { amount }, () => 'Transferred to activation balance').then((ok) => {
      if (ok) setTransferAmount('');
    });
  };

  const earnings = parseFloat(wallet?.ant_wallet_balance || 0);
  const activation = parseFloat(wallet?.activation_balance || 0);
  const withdrawAmount = parseFloat(withdrawForm.amount) || 0;

  if (loading) {
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
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-3xl font-bold">Wallet</h1>
            <p className="text-muted-foreground mt-1">USDT on the BEP20 (BSC) network. Your trading funds stay on Binance - this wallet pays for plans and holds referral earnings.</p>
          </div>
          <div className="flex gap-2 w-full sm:w-auto flex-wrap">
            <Button className="gap-2 flex-1 sm:flex-none" onClick={() => setDialog('deposit')}>
              <Plus className="h-4 w-4" /> Add Funds
            </Button>
            <Button variant="outline" className="gap-2 flex-1 sm:flex-none" onClick={() => setDialog('transfer')} disabled={earnings <= 0}>
              <ArrowLeftRight className="h-4 w-4" /> Transfer
            </Button>
            <Button variant="outline" className="gap-2 flex-1 sm:flex-none" onClick={() => setDialog('withdraw')} disabled={earnings < limits.min_withdrawal}>
              <ArrowUpRight className="h-4 w-4" /> Withdraw
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Activation Balance</CardTitle>
              <Wallet className="h-4 w-4 text-amber-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">${formatUsd(activation)}</div>
              <p className="text-xs text-muted-foreground mt-1">Spend on bot &amp; power plans</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Earnings Wallet</CardTitle>
              <TrendingUp className="h-4 w-4 text-green-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">${formatUsd(earnings)}</div>
              <p className="text-xs text-muted-foreground mt-1">Withdrawable referral income</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Deposited</CardTitle>
              <Download className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">${formatUsd(wallet?.total_deposit)}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Withdrawn</CardTitle>
              <Upload className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">${formatUsd(wallet?.total_withdrawal)}</div>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-3">
            <div>
              <CardTitle>Transaction History</CardTitle>
              <CardDescription>Deposits, withdrawals, transfers and purchases</CardDescription>
            </div>
            <Select value={typeFilter} onValueChange={(v) => { setTypeFilter(v); setHistoryPage(1); }}>
              <SelectTrigger className="w-full sm:w-[190px] text-xs sm:text-sm">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-popover">
                {TYPE_FILTERS.map((f) => <SelectItem key={f.value} value={f.value}>{f.label}</SelectItem>)}
              </SelectContent>
            </Select>
          </CardHeader>
          <CardContent>
            <TransactionList transactions={history} loading={historyLoading} />
            <div className="mt-6">
              <TablePagination page={historyPage} totalPages={historyPages} onPageChange={setHistoryPage} />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Add Funds */}
      <Dialog open={dialog === 'deposit'} onOpenChange={(o) => !o && setDialog(null)}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Add Funds (USDT)</DialogTitle>
            <DialogDescription>Send USDT, then submit the transaction hash so an admin can verify and credit it.</DialogDescription>
          </DialogHeader>
          {!depositInfo?.usdt_address ? (
            <div className="rounded-lg border bg-muted p-4 text-sm text-muted-foreground">Deposits are currently unavailable. Please try again later.</div>
          ) : (
            <form onSubmit={submitDeposit} className="space-y-4">
              <div className="rounded-lg border p-3 space-y-3">
                <div className="flex items-center gap-2">
                  <Badge variant="outline">{depositInfo.network}</Badge>
                  <span className="text-xs text-muted-foreground">USDT only</span>
                </div>
                {depositInfo.qr_image && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={depositInfo.qr_image} alt="Deposit address QR code" className="mx-auto h-40 w-40 rounded-lg bg-white p-2 object-contain" />
                )}
                <div className="flex items-center gap-2">
                  <code className="flex-1 break-all rounded bg-muted px-2 py-1.5 text-xs">{depositInfo.usdt_address}</code>
                  <CopyButton text={depositInfo.usdt_address} />
                </div>
                {depositInfo.note && <p className="text-xs text-muted-foreground">{depositInfo.note}</p>}
              </div>
              <div className="flex gap-2 rounded-lg border border-amber-300 bg-amber-50 p-3 text-xs text-amber-900 dark:border-amber-700/50 dark:bg-amber-950/30 dark:text-amber-200">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                <span>Send only USDT on {depositInfo.network}. Funds sent on another network or in another coin cannot be recovered.</span>
              </div>
              <div className="space-y-2">
                <Label htmlFor="dep_amount">Amount sent (USDT)</Label>
                <Input id="dep_amount" type="number" inputMode="decimal" min={limits.min_deposit} step="0.01" autoComplete="off"
                  placeholder={`Min ${limits.min_deposit}`} value={depositForm.amount}
                  onChange={(e) => setDepositForm({ ...depositForm, amount: e.target.value })} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="dep_hash">Transaction hash (TxID)</Label>
                <Input id="dep_hash" autoComplete="off" placeholder="0x..." value={depositForm.tx_hash}
                  onChange={(e) => setDepositForm({ ...depositForm, tx_hash: e.target.value })} />
              </div>
              <Button type="submit" className="w-full" disabled={submitting}>{submitting ? 'Submitting...' : 'Submit for verification'}</Button>
            </form>
          )}
        </DialogContent>
      </Dialog>

      {/* Withdraw */}
      <Dialog open={dialog === 'withdraw'} onOpenChange={(o) => !o && setDialog(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Withdraw Earnings</DialogTitle>
            <DialogDescription>Available: ${formatUsd(earnings)} USDT. Withdrawals are sent on-chain by an admin.</DialogDescription>
          </DialogHeader>
          <form onSubmit={submitWithdraw} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="wd_amount">Amount (USDT)</Label>
              <Input id="wd_amount" type="number" inputMode="decimal" min={limits.min_withdrawal} max={earnings} step="0.01" autoComplete="off"
                placeholder={`Min ${limits.min_withdrawal}`} value={withdrawForm.amount}
                onChange={(e) => setWithdrawForm({ ...withdrawForm, amount: e.target.value })} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="wd_addr">Your BEP20 (BSC) address</Label>
              <Input id="wd_addr" autoComplete="off" placeholder="0x..." value={withdrawForm.usdt_address}
                onChange={(e) => setWithdrawForm({ ...withdrawForm, usdt_address: e.target.value })} />
              {savedAddress && savedAddress !== withdrawForm.usdt_address && (
                <button type="button" className="text-xs text-primary hover:underline" onClick={() => setWithdrawForm({ ...withdrawForm, usdt_address: savedAddress })}>
                  Use saved address
                </button>
              )}
            </div>
            <div className="rounded-lg bg-muted p-3 text-sm space-y-1">
              <div className="flex justify-between"><span className="text-muted-foreground">Network fee</span><span>{limits.withdrawal_fee} USDT</span></div>
              <div className="flex justify-between font-medium"><span>You receive</span><span>{withdrawAmount > limits.withdrawal_fee ? formatUsd(withdrawAmount - limits.withdrawal_fee) : '0.00'} USDT</span></div>
            </div>
            <Button type="submit" className="w-full" disabled={submitting}>{submitting ? 'Submitting...' : 'Request withdrawal'}</Button>
          </form>
        </DialogContent>
      </Dialog>

      {/* Transfer */}
      <Dialog open={dialog === 'transfer'} onOpenChange={(o) => !o && setDialog(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Transfer to Activation Balance</DialogTitle>
            <DialogDescription>Move earnings (${formatUsd(earnings)}) into your activation balance to buy plans. This is instant.</DialogDescription>
          </DialogHeader>
          <form onSubmit={submitTransfer} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="tr_amount">Amount (USDT)</Label>
              <div className="flex gap-2">
                <Input id="tr_amount" type="number" inputMode="decimal" min="0.01" max={earnings} step="0.01" autoComplete="off"
                  placeholder="0.00" value={transferAmount} onChange={(e) => setTransferAmount(e.target.value)} />
                <Button type="button" variant="outline" onClick={() => setTransferAmount(String(earnings))}>Max</Button>
              </div>
            </div>
            <Button type="submit" className="w-full" disabled={submitting}>{submitting ? 'Transferring...' : 'Transfer'}</Button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
