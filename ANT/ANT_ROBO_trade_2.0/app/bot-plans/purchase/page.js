'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { TrendingUp, ArrowLeft, History, Clock, Zap } from 'lucide-react';
import Navigation from '@/components/Navigation';
import Link from 'next/link';
import TablePagination from '@/components/TablePagination';
import { getApiBaseUrl } from '@/lib/apiConfig';
import { useAlert } from '@/components/AlertProvider';

const PURCHASE_HISTORY_PAGE_SIZE = 5;

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

export default function BotPurchasePage() {
  const router = useRouter();
  const alert = useAlert();
  const [loading, setLoading] = useState(true);
  const [plans, setPlans] = useState([]);
  const [purchases, setPurchases] = useState([]);
  const [purchaseHistoryPage, setPurchaseHistoryPage] = useState(1);
  const [activationBalance, setActivationBalance] = useState(0);
  const [userId, setUserId] = useState('');
  const [userName, setUserName] = useState('');
  const [purchasing, setPurchasing] = useState(null);

  useEffect(() => {
    const storedUserId = localStorage.getItem('user_id');
    const storedUserName = localStorage.getItem('full_name');

    if (!storedUserId) {
      router.push('/');
      return;
    }

    setUserId(storedUserId);
    setUserName(storedUserName);
    fetchPlans();
    fetchWalletBalance(storedUserId);
    fetchPurchaseHistory(storedUserId);
  }, [router]);

  const fetchPlans = async () => {
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/bot-plans`);
      const data = await response.json();
      setPlans(data.plans || []);
    } catch (error) {
      console.error('Error fetching plans:', error);
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
      const response = await fetch(`${getApiBaseUrl()}/api/bot-plans/purchases/${uid}`);
      const data = await response.json();
      setPurchases(data.purchases || []);
      setPurchaseHistoryPage(1);
    } catch (error) {
      console.error('Error fetching bot purchase history:', error);
    }
  };

  // An expired yearly plan can be bought again, so only unexpired purchases block a purchase.
  const activePurchases = purchases.filter((p) => !p.is_expired);
  const purchasedBotNames = new Set(activePurchases.map((p) => p.bot_name));
  // Bot plans bill yearly - keyed by bot_name so each plan card can show when
  // the current user's own purchase of it expires (purchased_date + 1 year,
  // computed server-side in expiry_date).
  const purchaseByBotName = new Map(activePurchases.map((p) => [p.bot_name, p]));

  // Matches formatPurchaseDate's "2026 Apr 12 8:10 PM" style but date-only,
  // since an expiry is naturally read as a day, not a specific time.
  const formatExpiryDate = (value) => {
    const parsed = new Date(value);
    if (isNaN(parsed.getTime())) return null;
    return `${parsed.getFullYear()} ${MONTH_NAMES[parsed.getMonth()]} ${parsed.getDate()}`;
  };

  const handlePurchase = async (bot) => {
    setPurchasing(bot.bot_name);

    try {
      const response = await fetch(`${getApiBaseUrl()}/api/bot-plans/purchase/${userId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bot_name: bot.bot_name })
      });

      const data = await response.json();

      if (response.ok) {
        alert.success(`✅ Successfully purchased ${data.plan}!\n\nNext, connect your Binance API keys in Settings to start trading.`);
        fetchPurchaseHistory(userId);
        router.push('/settings');
      } else {
        alert.error('❌ ' + (data.detail || 'Purchase failed'));
      }
    } catch (error) {
      console.error(error)
      alert.error('❌ Error processing purchase');
    } finally {
      setPurchasing(null);
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
    <div className="min-h-screen bg-background">
      <Navigation userName={userName} />

      <div className="container mx-auto px-4 py-8">
        <div className="mb-6">
          <Link href="/bot-plans">
            <Button variant="ghost" size="sm" className="gap-2 mb-4">
              <ArrowLeft className="h-4 w-4" />
              Back to Bot Plans
            </Button>
          </Link>
          <h1 className="text-4xl font-bold mb-2">Purchase Trading Bot</h1>
          <p className="text-muted-foreground text-lg">
            Paid in USDT from your activation balance. Each plan is valid for one year.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {plans.map((bot, index) => {
            const originalPrice = parseFloat(bot.bot_price) || 0;
            const price = bot.discount_price !== null && bot.discount_price !== undefined
              ? parseFloat(bot.discount_price)
              : originalPrice;
            const hasDiscount = price < originalPrice;
            const discountPercent = hasDiscount ? Math.round(((originalPrice - price) / originalPrice) * 100) : 0;
            const isComingSoon = (bot.current_status || '').trim().toUpperCase() === 'COMING SOON';
            const alreadyPurchased = purchasedBotNames.has(bot.bot_name);
            const insufficientBalance = activationBalance < price;
            const existingPurchase = purchaseByBotName.get(bot.bot_name);
            const expiryLabel = existingPurchase?.expiry_date ? formatExpiryDate(existingPurchase.expiry_date) : null;

            return (
              <Card key={bot.bot_name || index} className="relative flex flex-col">
                {isComingSoon ? (
                  <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                    <Badge className="bg-orange-500 text-white px-4 py-1">
                      <Clock className="h-3 w-3 mr-1 inline" />
                      Coming Soon
                    </Badge>
                  </div>
                ) : (
                  <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                    <Badge className="bg-green-500 text-white px-4 py-1">
                      <Zap className="h-3 w-3 mr-1 inline" />
                      Yearly
                    </Badge>
                  </div>
                )}

                <CardHeader className="text-center pb-6 pt-8">
                  <div className="mb-4">
                    <div className="h-16 w-16 mx-auto rounded-full bg-amber-100 flex items-center justify-center">
                      <TrendingUp className="h-8 w-8 text-amber-600" />
                    </div>
                  </div>
                  <CardTitle className="text-2xl mb-2">{bot.bot_name}</CardTitle>
                  <div className="flex items-center justify-center gap-2 flex-wrap">
                    {hasDiscount && (
                      <span className="text-lg text-muted-foreground/70 line-through">${originalPrice.toLocaleString()}</span>
                    )}
                    <span className="text-4xl font-bold text-amber-600">${price.toLocaleString()}</span>
                    {hasDiscount && discountPercent > 0 && (
                      <Badge variant="destructive">-{discountPercent}%</Badge>
                    )}
                  </div>
                </CardHeader>

                <CardContent className="flex-1">
                  <CardDescription className="text-sm text-muted-foreground leading-relaxed">
                    {bot.bot_description || ''}
                  </CardDescription>
                </CardContent>

                <CardFooter>
                  <Button
                    className="w-full h-auto py-2.5"
                    size="lg"
                    onClick={() => handlePurchase(bot)}
                    disabled={isComingSoon || alreadyPurchased || insufficientBalance || purchasing === bot.bot_name}
                  >
                    {isComingSoon ? (
                      'Coming Soon'
                    ) : alreadyPurchased ? (
                      <span className="flex flex-col items-center leading-tight">
                        <span>Already Purchased</span>
                        {expiryLabel && (
                          <span className="text-xs font-normal opacity-80">Expires {expiryLabel}</span>
                        )}
                      </span>
                    ) : insufficientBalance ? (
                      'Insufficient Balance'
                    ) : purchasing === bot.bot_name ? (
                      'Processing...'
                    ) : (
                      'Purchase Bot'
                    )}
                  </Button>
                </CardFooter>
              </Card>
            );
          })}
        </div>

        <div className="mt-12 grid md:grid-cols-2 gap-6 items-start">
          {/* How Bot Trading Works */}
          <Card className="bg-gradient-to-r from-amber-50 to-amber-50 dark:from-amber-950/30 dark:to-amber-950/30">
            <CardContent className="p-8">
              <h3 className="text-2xl font-bold mb-4 text-foreground">How Bot Trading Works</h3>
              <div className="grid gap-6 text-left">
                <div>
                  <div className="h-10 w-10 rounded-full bg-amber-500 text-white flex items-center justify-center font-bold mb-3">
                    1
                  </div>
                  <h4 className="font-semibold mb-2 text-foreground">Purchase Your Bot</h4>
                  <p className="text-sm text-muted-foreground">
                    Pick spot or futures trading to match your capital and risk appetite
                  </p>
                </div>
                <div>
                  <div className="h-10 w-10 rounded-full bg-amber-500 text-white flex items-center justify-center font-bold mb-3">
                    2
                  </div>
                  <h4 className="font-semibold mb-2 text-foreground">Bot Activation</h4>
                  <p className="text-sm text-muted-foreground">
                    Connect a trade-only Binance API key; the bot then analyzes the market and trades 24/7
                  </p>
                </div>
                <div>
                  <div className="h-10 w-10 rounded-full bg-green-500 text-white flex items-center justify-center font-bold mb-3">
                    3
                  </div>
                  <h4 className="font-semibold mb-2 text-foreground">Track Performance</h4>
                  <p className="text-sm text-muted-foreground">
                    Follow every position, coin-wise P&L and daily results. Crypto is volatile - profit is never guaranteed
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
              <CardDescription>Bots you've purchased so far</CardDescription>
            </CardHeader>
            <CardContent>
              {purchases.length === 0 ? (
                <div className="text-center py-6 text-muted-foreground text-sm">
                  No bot purchases yet
                </div>
              ) : (
                <>
                  <div className="space-y-3">
                    {purchases
                      .slice((purchaseHistoryPage - 1) * PURCHASE_HISTORY_PAGE_SIZE, purchaseHistoryPage * PURCHASE_HISTORY_PAGE_SIZE)
                      .map((purchase, index) => {
                        const purchaseDate = getPurchaseDate(purchase);
                        const price = purchase.discount_price !== null && purchase.discount_price !== undefined
                          ? parseFloat(purchase.discount_price)
                          : parseFloat(purchase.bot_price) || 0;
                        return (
                          <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                            <div className="font-medium">{purchase.bot_name}@{price.toLocaleString()}</div>
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
