'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Zap, Check, ArrowLeft, History } from 'lucide-react';
import Navigation from '@/components/Navigation';
import Link from 'next/link';
import TablePagination from '@/components/TablePagination';
import { getApiBaseUrl } from '@/lib/apiConfig';
import { useAlert } from '@/components/AlertProvider';

const PURCHASE_HISTORY_PAGE_SIZE = 5;

const COLOR_CYCLE = ['green', 'blue', 'purple', 'orange', 'pink', 'yellow'];
const COLOR_CLASSES = {
  green: 'from-green-500 to-green-600',
  blue: 'from-amber-400 to-amber-600',
  purple: 'from-amber-400 to-amber-600',
  orange: 'from-orange-500 to-orange-600',
  pink: 'from-pink-500 to-pink-600',
  yellow: 'from-yellow-500 to-yellow-600'
};

const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

// Formats like "2026 Apr 12 8:10 PM"
const formatPurchaseDate = (date) => {
  const year = date.getFullYear();
  const month = MONTH_NAMES[date.getMonth()];
  const day = date.getDate();
  const minutes = String(date.getMinutes()).padStart(2, '0');
  const hours = date.getHours() % 12 || 12;
  const ampm = date.getHours() >= 12 ? 'PM' : 'AM';
  return `${year} ${month} ${day} ${hours}:${minutes} ${ampm}`;
};

// Best-effort lookup of a date-like field on a purchase row, since the exact column name isn't guaranteed
const getPurchaseDate = (purchase) => {
  const knownKeys = ['created_date', 'purchase_date', 'created_at', 'purchased_at', 'transaction_date'];
  for (const key of knownKeys) {
    if (purchase[key]) {
      const parsed = new Date(purchase[key]);
      if (!isNaN(parsed.getTime())) return formatPurchaseDate(parsed);
    }
  }
  // Fallback: scan every field for a date/time-like key with a parseable value
  for (const [key, value] of Object.entries(purchase)) {
    if (/date|time/i.test(key) && value) {
      const parsed = new Date(value);
      if (!isNaN(parsed.getTime())) return formatPurchaseDate(parsed);
    }
  }
  return null;
};

export default function PowerActivationPage() {
  const router = useRouter();
  const alert = useAlert();
  const [loading, setLoading] = useState(true);
  const [plans, setPlans] = useState([]);
  const [purchases, setPurchases] = useState([]);
  const [purchaseHistoryPage, setPurchaseHistoryPage] = useState(1);
  const [activationBalance, setActivationBalance] = useState(0);
  const [userId, setUserId] = useState('');
  const [userName, setUserName] = useState('');
  const [activating, setActivating] = useState(null);

  useEffect(() => {
    const storedUserId = localStorage.getItem('user_id');
    const storedUserName = localStorage.getItem('full_name');

    if (!storedUserId) {
      router.push('/');
      return;
    }

    setUserId(storedUserId);
    setUserName(storedUserName);
    checkBotPurchaseGate(storedUserId);
    fetchPlans();
    fetchWalletBalance(storedUserId);
    fetchPurchaseHistory(storedUserId);
  }, [router]);

  // Defense in depth against direct navigation - the entry points into this page
  // (app/bot-plans/page.js's card, UserDropdown's Power Balance tile) already hide
  // themselves until a bot plan is purchased, but someone could still type this
  // URL directly.
  const checkBotPurchaseGate = async (uid) => {
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/bot-plans/purchases/${uid}`);
      const data = await response.json();
      if ((data.purchases || []).length === 0) {
        alert.warning('Purchase a bot plan first to unlock Power Activation');
        router.push('/bot-plans');
      }
    } catch (error) {
      console.error('Error checking bot purchase status:', error);
    }
  };

  const fetchPlans = async () => {
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/power-plans`);
      const data = await response.json();
      setPlans(data.plans || []);
    } catch (error) {
      console.error('Error fetching power plans:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchWalletBalance = async (uid) => {
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/wallet/${uid}`);
      const data = await response.json();
      setActivationBalance(parseFloat(data.wallet?.activation_balance || 0));
    } catch (error) {
      console.error('Error fetching wallet balance:', error);
    }
  };

  const fetchPurchaseHistory = async (uid) => {
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/power-plans/purchases/${uid}`);
      const data = await response.json();
      setPurchases(data.purchases || []);
      setPurchaseHistoryPage(1);
    } catch (error) {
      console.error('Error fetching power purchase history:', error);
    }
  };

  const handleActivate = async (pkg) => {
    setActivating(pkg.power_name);

    try {
      const originalPrice = parseFloat(pkg.power_price) || 0;
      const price = pkg.discount_price !== null && pkg.discount_price !== undefined
        ? parseFloat(pkg.discount_price)
        : originalPrice;

      if (activationBalance < price) {
        alert.error(`❌ Insufficient activation balance!\n\nRequired: $${price.toLocaleString()}\nAvailable: $${activationBalance.toLocaleString()}\n\nPlease add money to your wallet first.`);
        setActivating(null);
        router.push('/wallet');
        return;
      }

      // Activate power directly from activation balance in the DB (no Cashfree)
      const response = await fetch(`${getApiBaseUrl()}/api/wallet/activate-points/${userId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ power_name: pkg.power_name })
      });

      const data = await response.json();

      if (response.ok) {
        const powerValue = parseFloat(pkg.power_value) || 0;
        alert.success(`✅ Power Activated Successfully!\n\n${powerValue.toLocaleString()} power have been activated.\n\nYour bot needs at least 500 power to keep opening new trades.`);
        fetchPurchaseHistory(userId);
        router.push('/dashboard');
      } else {
        alert.error('❌ ' + (data.detail || 'Activation failed. Please try again.'));
      }
    } catch (error) {
      console.error(error)
      alert.error('❌ Error processing activation');
    } finally {
      setActivating(null);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-amber-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-accent/30">
      <Navigation userName={userName} />

      <div className="container mx-auto px-4 py-8">
        <div className="mb-6">
          <Link href="/bot-plans">
            <Button variant="ghost" size="sm" className="gap-2 mb-4">
              <ArrowLeft className="h-4 w-4" />
              Back to Bot Plans
            </Button>
          </Link>
          <div className="flex items-center gap-3 mb-2">
            <Zap className="h-10 w-10 text-yellow-500" />
            <h1 className="text-4xl font-bold">Activate Trading Power</h1>
          </div>
          <p className="text-muted-foreground text-lg">
            Boost your trading capacity with energy power
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {plans.map((pkg, index) => {
            const color = COLOR_CYCLE[index % COLOR_CYCLE.length];
            const originalPrice = parseFloat(pkg.power_price) || 0;
            const price = pkg.discount_price !== null && pkg.discount_price !== undefined
              ? parseFloat(pkg.discount_price)
              : originalPrice;
            const hasDiscount = price < originalPrice;
            const popular = index === 2;
            const insufficientBalance = activationBalance < price;

            return (
              <Card key={pkg.power_name} className={`relative ${
                popular ? 'border-amber-500 border-2 shadow-xl' : 'hover:shadow-lg'
              } transition-all`}>
                {popular && (
                  <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                    <Badge className="bg-amber-500 text-white px-4 py-1">
                      <Zap className="h-3 w-3 mr-1 inline" />
                      Most Popular
                    </Badge>
                  </div>
                )}

                <CardHeader className="text-center pb-6 pt-8">
                  <div className="mb-4">
                    <div className={`h-16 w-16 mx-auto rounded-full bg-gradient-to-br ${COLOR_CLASSES[color]} flex items-center justify-center`}>
                      <Zap className="h-8 w-8 text-white" />
                    </div>
                  </div>
                  <CardTitle className="text-xl mb-2">{pkg.power_name}</CardTitle>
                  <div className="flex items-center justify-center gap-2 flex-wrap">
                    {hasDiscount && (
                      <span className="text-base text-muted-foreground/70 line-through">${originalPrice.toLocaleString()}</span>
                    )}
                    <span className="text-3xl font-bold bg-gradient-to-r from-yellow-600 to-orange-600 bg-clip-text text-transparent">
                      ${price.toLocaleString()}
                    </span>
                  </div>
                  <div className="text-sm text-muted-foreground mt-1">
                    {pkg.power_value_name || (parseFloat(pkg.power_value) || 0).toLocaleString()} Power
                  </div>
                </CardHeader>

                <CardContent className="space-y-3">
                  <div className="flex items-center justify-between p-3 bg-yellow-50 dark:bg-yellow-950/40 rounded-lg">
                    <div className="flex items-center gap-2">
                      <Zap className="h-4 w-4 text-yellow-600 dark:text-yellow-400" />
                      <span className="text-sm font-medium text-yellow-900 dark:text-yellow-100">Power added</span>
                    </div>
                    <Badge variant="secondary">+{(parseFloat(pkg.power_value) || 0).toLocaleString()}</Badge>
                  </div>

                  <div className="pt-2 space-y-2">
                    <div className="flex items-start gap-2">
                      <Check className="h-4 w-4 text-green-600 mt-0.5" />
                      <span className="text-xs text-muted-foreground">Instant activation</span>
                    </div>
                    <div className="flex items-start gap-2">
                      <Check className="h-4 w-4 text-green-600 mt-0.5" />
                      <span className="text-xs text-muted-foreground">Keeps your bot above the minimum power to trade</span>
                    </div>
                    <div className="flex items-start gap-2">
                      <Check className="h-4 w-4 text-green-600 mt-0.5" />
                      <span className="text-xs text-muted-foreground">Paid from your USDT activation balance</span>
                    </div>
                  </div>
                </CardContent>

                <CardFooter>
                  <Button
                    className={`w-full gap-2 border-0 text-white bg-gradient-to-br ${COLOR_CLASSES[color]} hover:opacity-90`}
                    size="lg"
                    onClick={() => handleActivate(pkg)}
                    disabled={insufficientBalance || activating === pkg.power_name}
                  >
                    {activating === pkg.power_name ? (
                      'Activating...'
                    ) : insufficientBalance ? (
                      'Insufficient Balance'
                    ) : (
                      <>
                        <Zap className="h-4 w-4" />
                        Activate Power
                      </>
                    )}
                  </Button>
                </CardFooter>
              </Card>
            );
          })}
        </div>

        <div className="mt-12 grid md:grid-cols-2 gap-6 items-start">
          {/* Info Section */}
          <Card className="bg-gradient-to-r from-yellow-50 to-orange-50 dark:from-yellow-950/30 dark:to-orange-950/30">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-6 w-6 text-yellow-600 dark:text-yellow-400" />
                What is Power?
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-6">
                <div className="space-y-2">
                  <div className="h-10 w-10 rounded-lg bg-yellow-100 dark:bg-yellow-900/50 flex items-center justify-center"><Zap className="h-6 w-6 text-yellow-600 dark:text-yellow-400" /></div>
                  <h3 className="font-semibold text-foreground">Fuel for your bot</h3>
                  <p className="text-sm text-muted-foreground">
                    Power is consumed as your bot trades. The bot stops opening new trades when it falls below the minimum, and resumes once you top it up.
                  </p>
                </div>
                <div className="space-y-2">
                  <div className="h-10 w-10 rounded-lg bg-amber-100 dark:bg-amber-900/50 flex items-center justify-center"><Check className="h-6 w-6 text-amber-600 dark:text-amber-400" /></div>
                  <h3 className="font-semibold text-foreground">No performance promise</h3>
                  <p className="text-sm text-muted-foreground">
                    Power keeps the bot running; it does not improve or guarantee returns. Crypto trading carries a risk of loss.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Purchase History */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <History className="h-5 w-5" />
                Purchase History
              </CardTitle>
              <CardDescription>Power packages you've activated so far</CardDescription>
            </CardHeader>
            <CardContent>
              {purchases.length === 0 ? (
                <div className="text-center py-6 text-muted-foreground text-sm">
                  No power purchases yet
                </div>
              ) : (
                <>
                  <div className="space-y-3">
                    {purchases
                      .slice((purchaseHistoryPage - 1) * PURCHASE_HISTORY_PAGE_SIZE, purchaseHistoryPage * PURCHASE_HISTORY_PAGE_SIZE)
                      .map((purchase, index) => {
                        const purchaseDate = getPurchaseDate(purchase);
                        const powerValue = parseFloat(purchase.energy_power) || 0;
                        const label = purchase.power_name || 'Power';
                        return (
                          <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                            <div className="font-medium">{label}@{powerValue.toLocaleString()}</div>
                            {purchaseDate && (
                              <div className="text-sm text-muted-foreground">{purchaseDate}</div>
                            )}
                          </div>
                        );
                      })}
                  </div>
                  <div className="mt-4">
                    <TablePagination
                      page={purchaseHistoryPage}
                      totalPages={Math.ceil(purchases.length / PURCHASE_HISTORY_PAGE_SIZE)}
                      onPageChange={setPurchaseHistoryPage}
                    />
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
