'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { KeyRound, ShieldCheck, SlidersHorizontal, UserRound, Power, CheckCircle2, Eye, EyeOff } from 'lucide-react';
import Navigation from '@/components/Navigation';
import { useAlert } from '@/components/AlertProvider';
import { getApiBaseUrl, safeJson, formatUsd } from '@/lib/apiConfig';
import { validateMobileNumber } from '@/lib/mobileValidation';

const ADDRESS_RE = /^0x[0-9a-fA-F]{40}$/;

// Form values are kept as strings while editing (so "0." and "" stay typeable) and only
// parsed on save.
function toForm(c) {
  return {
    total_investment_amount: String(c.total_investment_amount ?? ''),
    single_trade_amount: String(c.single_trade_amount ?? ''),
    max_trade: String(c.max_trade ?? ''),
    leverage: String(c.leverage ?? 1),
    stoploss_percent: String(c.stoploss_percent ?? ''),
    target_percent: String(c.target_percent ?? ''),
    trade_long: !!c.trade_long,
    trade_short: !!c.trade_short,
    usdt_address: c.usdt_address || '',
    mobile_number: c.whatsapp_number || '',
  };
}

function Section({ icon: Icon, title, description, children, action }) {
  return (
    <Card className="mb-6">
      <CardHeader className="flex flex-row items-start justify-between gap-3">
        <div>
          <CardTitle className="flex items-center gap-2"><Icon className="h-5 w-5 text-primary" /> {title}</CardTitle>
          {description && <CardDescription className="mt-1.5">{description}</CardDescription>}
        </div>
        {action}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

function Field({ id, label, hint, children }) {
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      {children}
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}

export default function SettingsPage() {
  const router = useRouter();
  const alert = useAlert();
  const [userId, setUserId] = useState('');
  const [userName, setUserName] = useState('');
  const [loading, setLoading] = useState(true);
  const [config, setConfig] = useState(null);
  const [form, setForm] = useState(null);

  const [keys, setKeys] = useState({ api_key: '', api_secret: '' });
  const [showSecret, setShowSecret] = useState(false);
  const [savingKeys, setSavingKeys] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [verifyResult, setVerifyResult] = useState(null);

  const [saving, setSaving] = useState(false);
  const [togglingBot, setTogglingBot] = useState(false);

  const loadConfig = useCallback(async (uid) => {
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/config/${uid}`);
      if (!response.ok) throw new Error('config');
      const data = await safeJson(response);
      setConfig(data);
      setForm(toForm(data));
    } catch (error) {
      console.error('Error loading settings:', error);
      alert.error('Could not load your settings. Please refresh.');
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const storedUserId = localStorage.getItem('user_id');
    if (!storedUserId) {
      router.push('/');
      return;
    }
    setUserId(storedUserId);
    setUserName(localStorage.getItem('full_name') || '');
    loadConfig(storedUserId);
  }, [router, loadConfig]);

  const put = async (path, body) => {
    const response = await fetch(`${getApiBaseUrl()}${path}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await safeJson(response);
    return { ok: response.ok, data };
  };

  const saveKeys = async (e) => {
    e.preventDefault();
    if (!keys.api_key.trim() || !keys.api_secret.trim()) {
      alert.warning('Enter both the API key and the API secret');
      return;
    }
    setSavingKeys(true);
    try {
      const { ok, data } = await put(`/api/config/${userId}`, { api_key: keys.api_key, api_secret: keys.api_secret });
      if (!ok) {
        alert.error((typeof data.detail === 'string' && data.detail) || 'Failed to save API keys');
        return;
      }
      setKeys({ api_key: '', api_secret: '' });
      setVerifyResult(null);
      alert.success('API keys saved. Now verify the connection.');
      await loadConfig(userId);
    } catch {
      alert.error('Server error. Please try again.');
    } finally {
      setSavingKeys(false);
    }
  };

  const verifyKeys = async () => {
    setVerifying(true);
    setVerifyResult(null);
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/binance/verify/${userId}`, { method: 'POST' });
      const data = await safeJson(response);
      if (!response.ok) {
        alert.error((typeof data.detail === 'string' && data.detail) || 'Could not verify the keys');
        return;
      }
      setVerifyResult(data);
      alert.success('Binance account connected');
      await loadConfig(userId);
    } catch {
      alert.error('Server error. Please try again.');
    } finally {
      setVerifying(false);
    }
  };

  const num = (value) => (value === '' || value == null ? NaN : Number(value));

  const saveSettings = async (e) => {
    e.preventDefault();
    const mobile = validateMobileNumber(form.mobile_number);
    if (mobile.error) return alert.warning(mobile.error);
    const address = form.usdt_address.trim();
    if (address && !ADDRESS_RE.test(address)) return alert.warning('Withdrawal address must be a valid BEP20 (BSC) address starting with 0x');

    const payload = {
      total_investment_amount: num(form.total_investment_amount),
      single_trade_amount: num(form.single_trade_amount),
      max_trade: num(form.max_trade),
      leverage: num(form.leverage),
      stoploss_percent: num(form.stoploss_percent),
      target_percent: num(form.target_percent),
    };
    for (const [key, value] of Object.entries(payload)) {
      if (Number.isNaN(value)) return alert.warning('Please fill in every trading setting with a number');
      if (key !== 'total_investment_amount' && value <= 0) return alert.warning('Trading settings must be greater than zero');
    }
    if (!form.trade_long && !form.trade_short) return alert.warning('Enable at least one of Long or Short trading');
    if (payload.single_trade_amount > payload.total_investment_amount && payload.total_investment_amount > 0) {
      return alert.warning('Single trade amount cannot be larger than your trading capital');
    }

    setSaving(true);
    try {
      const { ok, data } = await put(`/api/config/${userId}`, {
        ...payload,
        max_trade: Math.round(payload.max_trade),
        leverage: Math.round(payload.leverage),
        trade_long: form.trade_long,
        trade_short: form.trade_short,
        usdt_address: address,
        mobile_number: form.mobile_number,
      });
      if (!ok) {
        alert.error((typeof data.detail === 'string' && data.detail) || 'Failed to save settings');
        return;
      }
      alert.success('Settings saved');
      await loadConfig(userId);
    } catch {
      alert.error('Server error. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const toggleBot = async (next) => {
    setTogglingBot(true);
    try {
      const { ok, data } = await put(`/api/config/${userId}/trading-status`, { is_trading_active: next });
      if (!ok) {
        alert.error((typeof data.detail === 'string' && data.detail) || 'Could not change bot status');
        return;
      }
      alert.success(data.message || (next ? 'Trading started' : 'Trading stopped'));
      setConfig((c) => ({ ...c, is_trading_active: next }));
    } catch {
      alert.error('Server error. Please try again.');
    } finally {
      setTogglingBot(false);
    }
  };

  const setField = (name) => (e) => setForm((f) => ({ ...f, [name]: e.target.value }));

  if (loading || !form) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
      </div>
    );
  }

  const hasKeys = config.has_api_key && config.has_api_secret;
  const lowPower = config.energy_power < config.min_trading_power;
  const stoplossAmount = (num(form.single_trade_amount) * num(form.stoploss_percent)) / 100;
  const targetAmount = (num(form.single_trade_amount) * num(form.target_percent)) / 100;

  return (
    <div className="min-h-screen bg-background">
      <Navigation userName={userName} />

      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <div className="mb-6">
          <h1 className="text-3xl font-bold">Settings</h1>
          <p className="text-muted-foreground mt-1">Connect Binance and tune how the bot trades for you</p>
        </div>

        {/* Bot status */}
        <Card className="mb-6">
          <CardContent className="flex flex-wrap items-center justify-between gap-4 pt-6">
            <div className="flex items-center gap-3">
              <div className={`h-11 w-11 rounded-lg flex items-center justify-center ${config.is_trading_active ? 'bg-green-100 dark:bg-green-950/40' : 'bg-muted'}`}>
                <Power className={`h-5 w-5 ${config.is_trading_active ? 'text-green-600' : 'text-muted-foreground'}`} />
              </div>
              <div>
                <div className="font-semibold flex items-center gap-2">
                  Trading bot
                  <Badge variant={config.is_trading_active ? 'default' : 'secondary'}>{config.is_trading_active ? 'Running' : 'Paused'}</Badge>
                </div>
                <p className="text-sm text-muted-foreground">
                  Pausing stops new entries; open positions are still managed to exit.
                  {lowPower && ` Power is below ${config.min_trading_power} - top it up to start.`}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-sm text-muted-foreground">Plan: <strong className="text-foreground">{config.current_plan || 'None'}</strong></span>
              <Switch
                checked={config.is_trading_active}
                onCheckedChange={toggleBot}
                disabled={togglingBot}
                aria-label="Start or stop the trading bot"
              />
            </div>
          </CardContent>
        </Card>

        {/* Binance connection */}
        <Section
          icon={KeyRound}
          title="Binance Connection"
          description="The bot trades on your own Binance account through an API key. Your funds never leave Binance."
          action={hasKeys ? (
            <Badge variant="outline" className="gap-1 shrink-0"><CheckCircle2 className="h-3.5 w-3.5 text-green-600" /> Keys saved</Badge>
          ) : <Badge variant="secondary" className="shrink-0">Not connected</Badge>}
        >
          <div className="mb-4 flex gap-3 rounded-lg border bg-muted/50 p-3 text-sm">
            <ShieldCheck className="h-5 w-5 shrink-0 text-primary mt-0.5" />
            <ul className="list-disc space-y-1 pl-4 text-muted-foreground">
              <li>On Binance, create an API key (API Management) and enable <strong>Spot &amp; Margin Trading</strong> (and <strong>Futures</strong> if you trade short/leverage).</li>
              <li>Leave <strong>Enable Withdrawals</strong> switched <strong>off</strong>. Keys that can withdraw are rejected.</li>
              <li>Optionally restrict the key to our server IP for extra safety.</li>
            </ul>
          </div>

          {hasKeys && (
            <div className="mb-4 flex flex-wrap items-center gap-x-6 gap-y-2 rounded-lg border p-3 text-sm">
              <div><span className="text-muted-foreground">Current key:</span> <code>{config.api_key_masked}</code></div>
              {config.show_spot_balance && (
                <div><span className="text-muted-foreground">Spot USDT:</span> <strong>${formatUsd(config.binance_spot_usdt ?? 0)}</strong></div>
              )}
              {config.show_futures_balance && (
                <div><span className="text-muted-foreground">Futures USDT:</span> <strong>${formatUsd(config.binance_futures_usdt ?? 0)}</strong></div>
              )}
              <div className="text-xs text-muted-foreground">Last synced</div>
              <Button type="button" size="sm" variant="outline" className="ml-auto" onClick={verifyKeys} disabled={verifying}>
                {verifying ? 'Verifying...' : 'Verify & sync balance'}
              </Button>
            </div>
          )}
          {verifyResult && (
            <div className="mb-4 flex items-center gap-2 rounded-lg border border-green-300 bg-green-50 p-3 text-sm text-green-900 dark:border-green-800 dark:bg-green-950/30 dark:text-green-200">
              <CheckCircle2 className="h-4 w-4 shrink-0" />
              Connected.
              {verifyResult.spot_usdt != null && ` Spot $${formatUsd(verifyResult.spot_usdt)}`}
              {verifyResult.futures_usdt != null && ` Futures $${formatUsd(verifyResult.futures_usdt)}`}
              {` (total $${formatUsd(verifyResult.usdt_total)}, $${formatUsd(verifyResult.usdt_free)} free)`}
              {verifyResult.futures_enabled ? ' - futures enabled.' : ' - futures not enabled on this key.'}
            </div>
          )}

          <form onSubmit={saveKeys} className="grid gap-4 sm:grid-cols-2">
            <Field id="api_key" label={hasKeys ? 'Replace API key' : 'API key'}>
              <Input id="api_key" autoComplete="off" spellCheck={false} placeholder="Paste your Binance API key"
                value={keys.api_key} onChange={(e) => setKeys({ ...keys, api_key: e.target.value })} />
            </Field>
            <Field id="api_secret" label={hasKeys ? 'Replace API secret' : 'API secret'} hint="Stored on the server and never shown again.">
              <div className="relative">
                <Input id="api_secret" type={showSecret ? 'text' : 'password'} autoComplete="new-password" spellCheck={false}
                  placeholder="Paste your Binance API secret" className="pr-10"
                  value={keys.api_secret} onChange={(e) => setKeys({ ...keys, api_secret: e.target.value })} />
                <button type="button" aria-label={showSecret ? 'Hide secret' : 'Show secret'}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  onClick={() => setShowSecret((s) => !s)}>
                  {showSecret ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </Field>
            <div className="sm:col-span-2 flex gap-2">
              <Button type="submit" disabled={savingKeys}>{savingKeys ? 'Saving...' : 'Save API keys'}</Button>
              {hasKeys && <Button type="button" variant="outline" onClick={verifyKeys} disabled={verifying}>{verifying ? 'Verifying...' : 'Verify connection'}</Button>}
            </div>
          </form>
        </Section>

        <form onSubmit={saveSettings}>
          {/* Trading configuration */}
          <Section icon={SlidersHorizontal} title="Trading Configuration" description="Sizing and risk controls the bot applies to every trade">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field id="total_investment_amount" label="Trading capital (USDT)" hint={`Live on Binance incl. open margin: $${formatUsd(config.live_current_investment)}`}>
                <Input id="total_investment_amount" type="number" inputMode="decimal" min="0" step="0.01" value={form.total_investment_amount} onChange={setField('total_investment_amount')} />
              </Field>
              <Field id="single_trade_amount" label="Amount per trade (USDT)" hint="Margin committed to each new position">
                <Input id="single_trade_amount" type="number" inputMode="decimal" min="0" step="0.01" value={form.single_trade_amount} onChange={setField('single_trade_amount')} />
              </Field>
              <Field id="max_trade" label="Max open trades" hint="Hard cap on simultaneous positions (1-50)">
                <Input id="max_trade" type="number" inputMode="numeric" min="1" max="50" step="1" value={form.max_trade} onChange={setField('max_trade')} />
              </Field>
              <Field id="leverage" label="Leverage (x)" hint="1x = spot-style, no leverage (1-20x). Higher leverage amplifies losses too.">
                <Input id="leverage" type="number" inputMode="numeric" min="1" max="20" step="1" value={form.leverage} onChange={setField('leverage')} />
              </Field>
              <Field id="stoploss_percent" label="Stoploss (%)" hint={Number.isFinite(stoplossAmount) ? `Max loss per trade about $${formatUsd(stoplossAmount)}` : undefined}>
                <Input id="stoploss_percent" type="number" inputMode="decimal" min="0" step="0.1" value={form.stoploss_percent} onChange={setField('stoploss_percent')} />
              </Field>
              <Field id="target_percent" label="Target profit (%)" hint={Number.isFinite(targetAmount) ? `Take profit at about $${formatUsd(targetAmount)} per trade` : undefined}>
                <Input id="target_percent" type="number" inputMode="decimal" min="0" step="0.1" value={form.target_percent} onChange={setField('target_percent')} />
              </Field>
            </div>
            <div className="mt-6 grid gap-3 sm:grid-cols-2">
              <label className="flex items-center justify-between gap-3 rounded-lg border p-3">
                <div>
                  <div className="font-medium">Long trades</div>
                  <div className="text-xs text-muted-foreground">Buy and hold for a rise</div>
                </div>
                <Switch checked={form.trade_long} onCheckedChange={(v) => setForm((f) => ({ ...f, trade_long: v }))} />
              </label>
              <label className="flex items-center justify-between gap-3 rounded-lg border p-3">
                <div>
                  <div className="font-medium">Short trades</div>
                  <div className="text-xs text-muted-foreground">Profit from a fall (needs Futures)</div>
                </div>
                <Switch checked={form.trade_short} onCheckedChange={(v) => setForm((f) => ({ ...f, trade_short: v }))} />
              </label>
            </div>
          </Section>

          {/* Account */}
          <Section icon={UserRound} title="Account" description="Contact and payout details">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field id="mobile_number" label="Mobile / WhatsApp number">
                <Input id="mobile_number" autoComplete="tel" value={form.mobile_number} onChange={setField('mobile_number')} />
              </Field>
              <Field id="usdt_address" label="Withdrawal address (USDT, BEP20)" hint="Pre-fills the Withdraw form">
                <Input id="usdt_address" autoComplete="off" spellCheck={false} placeholder="0x..." value={form.usdt_address} onChange={setField('usdt_address')} />
              </Field>
              <Field id="referal_code" label="Your referral code">
                <Input id="referal_code" readOnly value={config.referal_code} />
              </Field>
              <Field id="energy_power" label="Power balance">
                <Input id="energy_power" readOnly value={Number(config.energy_power).toLocaleString()} />
              </Field>
            </div>
          </Section>

          <div className="sticky bottom-4 flex justify-end">
            <Button type="submit" size="lg" className="shadow-lg" disabled={saving}>{saving ? 'Saving...' : 'Save settings'}</Button>
          </div>
        </form>
      </div>
    </div>
  );
}
