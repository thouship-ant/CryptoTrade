'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ShoppingCart, Zap, Lock } from 'lucide-react';
import Navigation from '@/components/Navigation';
import Link from 'next/link';
import { getApiBaseUrl } from '@/lib/apiConfig';

export default function BotPlansPage() {
  const router = useRouter();
  const [userName, setUserName] = useState('');
  const [hasPurchasedBot, setHasPurchasedBot] = useState(false);
  const [purchasesLoading, setPurchasesLoading] = useState(true);
  const [botPlans, setBotPlans] = useState([]);
  const [powerPlans, setPowerPlans] = useState([]);

  useEffect(() => {
    const storedUserId = localStorage.getItem('user_id');
    const storedUserName = localStorage.getItem('full_name');

    if (!storedUserId) {
      router.push('/');
      return;
    }

    setUserName(storedUserName);

    // The Demo role (a paper-trading/backtest utility account, not a real
    // trading user) has no bot plans to buy or activate - checked fresh from
    // the server rather than trusting Navigation's own cached localStorage
    // role, which may not have populated yet on a cold page load.
    fetch(`${getApiBaseUrl()}/api/config/${storedUserId}`)
      .then((res) => res.json())
      .then((data) => {
        if ((data.role || '').toLowerCase() === 'demo') {
          router.push('/dashboard');
        }
      })
      .catch(() => {});

    Promise.all([
      fetch(`${getApiBaseUrl()}/api/bot-plans`).then((r) => r.json()),
      fetch(`${getApiBaseUrl()}/api/power-plans`).then((r) => r.json()),
    ])
      .then(([bots, powers]) => {
        setBotPlans(bots.plans || []);
        setPowerPlans(powers.plans || []);
      })
      .catch((error) => console.error('Error fetching plans:', error));

    // Power Activation is only useful once there's a bot running to boost -
    // gate it behind having purchased at least one bot plan.
    fetch(`${getApiBaseUrl()}/api/bot-plans/purchases/${storedUserId}`)
      .then((res) => res.json())
      .then((data) => setHasPurchasedBot((data.purchases || []).length > 0))
      .catch((error) => console.error('Error fetching bot purchases:', error))
      .finally(() => setPurchasesLoading(false));
  }, [router]);

  const priceOf = (plan, listKey, discountKey) => Number(plan[discountKey] ?? plan[listKey]);
  const rangeLabel = (plans, listKey, discountKey) => {
    if (!plans.length) return '-';
    const prices = plans.map((p) => priceOf(p, listKey, discountKey));
    const lo = Math.min(...prices);
    const hi = Math.max(...prices);
    return lo === hi ? `$${lo.toLocaleString()}` : `$${lo.toLocaleString()} - $${hi.toLocaleString()}`;
  };
  const botRange = rangeLabel(botPlans, 'bot_price', 'discount_price');
  const powerRange = rangeLabel(powerPlans, 'power_price', 'discount_price');

  return (
    <div className="min-h-screen bg-background">
      <Navigation userName={userName} />

      <div className="container mx-auto px-4 py-8">
        <div className="mb-8 text-center">
          <h1 className="text-4xl font-bold mb-2">Bot Trading Plans</h1>
          <p className="text-muted-foreground text-lg">
            Choose between purchasing bots or activating powers
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          {/* Bot Purchase */}
          <Link href="/bot-plans/purchase">
            <Card className="hover:shadow-xl transition-all cursor-pointer border-2 hover:border-amber-500">
              <CardHeader className="text-center pb-8 pt-8">
                <div className="mb-4">
                  <div className="h-20 w-20 mx-auto rounded-full bg-gradient-to-br from-amber-400 to-amber-600 flex items-center justify-center">
                    <ShoppingCart className="h-10 w-10 text-white" />
                  </div>
                </div>
                <CardTitle className="text-2xl">Purchase Bot</CardTitle>
                <CardDescription className="text-base mt-2">
                  Buy automated Binance trading bots - spot or futures
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-center">
                <div className="p-4 bg-amber-50 rounded-lg">
                  <div className="text-sm font-medium text-amber-900">Available Plans</div>
                  <div className="text-2xl font-bold text-amber-600 mt-1">{botRange} <span className="text-sm font-normal">USDT</span></div>
                  <div className="text-xs text-amber-700 mt-1">{botPlans.length} Different Plans</div>
                </div>
                <Button size="lg" className="w-full gap-2 btn bg-primary hover:bg-primary/90 text-white">
                  View Bot Plans
                </Button>
              </CardContent>
            </Card>
          </Link>

          {/* Power Activation - only unlocked once at least one bot plan is purchased,
              since there's nothing yet for a power boost to apply to otherwise. */}
          {!purchasesLoading && hasPurchasedBot ? (
            <Link href="/bot-plans/activate">
              <Card className="hover:shadow-xl transition-all cursor-pointer border-2 hover:border-yellow-500">
                <CardHeader className="text-center pb-8 pt-8">
                  <div className="mb-4">
                    <div className="h-20 w-20 mx-auto rounded-full bg-gradient-to-br from-yellow-500 to-yellow-600 flex items-center justify-center">
                      <Zap className="h-10 w-10 text-white" />
                    </div>
                  </div>
                  <CardTitle className="text-2xl">Activate Power</CardTitle>
                  <CardDescription className="text-base mt-2">
                    Activate power to boost your trading capabilities and energy
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3 text-center">
                  <div className="p-4 bg-yellow-50 rounded-lg">
                    <div className="text-sm font-medium text-yellow-900">Available Packages</div>
                    <div className="text-2xl font-bold text-yellow-600 mt-1">{powerRange} <span className="text-sm font-normal">USDT</span></div>
                    <div className="text-xs text-yellow-700 mt-1">{powerPlans.length} Different Packages</div>
                  </div>
                  <Button size="lg" className="w-full bg-yellow-600 hover:bg-yellow-700">
                    View Power Packages
                  </Button>
                </CardContent>
              </Card>
            </Link>
          ) : (
            <Card className="opacity-60 border-2 border-dashed">
              <CardHeader className="text-center pb-8 pt-8">
                <div className="mb-4">
                  <div className="h-20 w-20 mx-auto rounded-full bg-muted flex items-center justify-center">
                    <Lock className="h-8 w-8 text-muted-foreground" />
                  </div>
                </div>
                <CardTitle className="text-2xl text-muted-foreground">Activate Power</CardTitle>
                <CardDescription className="text-base mt-2">
                  Purchase a bot plan first to unlock power activation
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-center">
                <div className="p-4 bg-muted rounded-lg">
                  <div className="text-sm font-medium text-muted-foreground">Available Packages</div>
                  <div className="text-2xl font-bold text-muted-foreground mt-1">{powerRange} <span className="text-sm font-normal">USDT</span></div>
                  <div className="text-xs text-muted-foreground mt-1">{powerPlans.length} Different Packages</div>
                </div>
                <Button size="lg" className="w-full" variant="outline" disabled>
                  Locked — Purchase a Bot First
                </Button>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Info Section */}
        <div className="mt-12 max-w-4xl mx-auto">
          <Card>
            <CardHeader>
              <CardTitle>What&apos;s the Difference?</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-2 gap-6">
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <ShoppingCart className="h-5 w-5 text-amber-600" />
                    <h3 className="font-semibold">Bot Purchase</h3>
                  </div>
                  <ul className="space-y-2 text-sm text-muted-foreground ml-7">
                    <li>• Buy complete trading bot packages</li>
                    <li>• Includes AI-powered trading algorithms</li>
                    <li>• Trades on your own Binance account</li>
                    <li>• Long and short strategies</li>
                    <li>• 365 days validity</li>
                    <li>• 24/7 automated trading</li>
                  </ul>
                </div>
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <Zap className="h-5 w-5 text-yellow-600" />
                    <h3 className="font-semibold">Power Activation</h3>
                  </div>
                  <ul className="space-y-2 text-sm text-muted-foreground ml-7">
                    <li>• Activate trading points/energy</li>
                    <li>• Boost your trading capacity</li>
                    <li>• Unlock advanced features</li>
                    <li>• Increase order limits</li>
                    <li>• Enhance profit potential</li>
                    <li>• Pay from your USDT activation balance</li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
