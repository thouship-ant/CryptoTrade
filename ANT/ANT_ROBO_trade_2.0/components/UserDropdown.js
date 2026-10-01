'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  User,
  Wallet,
  TrendingUp,
  Zap,
  LogOut,
  ChevronDown,
  Shield,
  Sun,
  Moon,
  Lock
} from 'lucide-react';
import Link from 'next/link';
import { getApiBaseUrl } from '@/lib/apiConfig';
import { useTheme } from '@/components/ThemeProvider';

export default function UserDropdown({ userName, userId }) {
  const router = useRouter();
  const { theme, toggleTheme } = useTheme();
  const [userStats, setUserStats] = useState(null);
  const [loading, setLoading] = useState(true);
  // Power Activation only makes sense once a bot plan has been purchased -
  // matches the same gate on app/bot-plans/page.js's Activate Power card.
  const [hasPurchasedBot, setHasPurchasedBot] = useState(false);

  useEffect(() => {
    if (userId) {
      fetchUserStats();
    }
  }, [userId]);

  const fetchUserStats = async () => {
    try {
      const [walletRes, configRes, purchasesRes] = await Promise.all([
        fetch(`${getApiBaseUrl()}/api/wallet/${userId}`),
        fetch(`${getApiBaseUrl()}/api/config/${userId}`),
        fetch(`${getApiBaseUrl()}/api/bot-plans/purchases/${userId}`)
      ]);

      const walletData = await walletRes.json();
      const configData = await configRes.json();
      const purchasesData = await purchasesRes.json();
      setHasPurchasedBot((purchasesData.purchases || []).length > 0);

      const investmentAmount = configData.live_current_investment || 0;

      setUserStats({
        walletBalance: walletData.wallet?.ant_wallet_balance || 0,
        investmentAmount,
        currentPlan: configData.current_plan || 'No Plan',
        energyPower: configData.energy_power || 0
      });
    } catch (error) {
      console.error('Error fetching user stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.clear();
    router.push('/');
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="gap-2">
          <div className="h-8 w-8 rounded-full bg-amber-100 flex items-center justify-center">
            <User className="h-4 w-4 text-amber-600" />
          </div>
          <span className="hidden md:inline">{userName}</span>
          <ChevronDown className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80 themed-bg-pattern">
        <DropdownMenuLabel>
          <div className="flex items-center gap-3">
            <div className="h-12 w-12 rounded-full bg-gradient-to-br from-amber-400 to-amber-600 flex items-center justify-center">
              <User className="h-6 w-6 text-white" />
            </div>
            <div>
              <div className="font-semibold">{userName}</div>
              <Badge variant="outline" className="mt-1">
                <Shield className="h-3 w-3 mr-1" />
                {userStats?.currentPlan || 'No Plan'}
              </Badge>
            </div>
          </div>
        </DropdownMenuLabel>
        
        <DropdownMenuSeparator />
        
        {loading ? (
          <div className="p-4 text-center text-sm text-muted-foreground">
            Loading stats...
          </div>
        ) : (
          <div className="p-2 space-y-2">
            {/* Wallet Balance */}
            <Link href="/wallet">
              <div className="flex items-center justify-between p-3 rounded-lg hover:bg-accent transition-colors cursor-pointer">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-lg bg-green-100 flex items-center justify-center">
                    <Wallet className="h-5 w-5 text-green-600" />
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">Earnings Wallet</div>
                    <div className="font-semibold text-green-600">
                      ${parseFloat(userStats?.walletBalance || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </div>
                  </div>
                </div>
              </div>
            </Link>

            {/* Power Balance (energy_power) - Activate Power only makes sense once a
                bot plan is purchased, so this links there only when unlocked;
                otherwise it's a plain, non-clickable balance display. */}
            {hasPurchasedBot ? (
              <Link href="/bot-plans/activate">
                <div className="flex items-center justify-between p-3 rounded-lg hover:bg-accent transition-colors cursor-pointer">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-lg bg-yellow-100 flex items-center justify-center">
                      <Zap className="h-5 w-5 text-yellow-600" />
                    </div>
                    <div>
                      <div className="text-xs text-muted-foreground">Power Balance</div>
                      <div className="font-semibold text-yellow-600">
                        {parseFloat(userStats?.energyPower || 0).toLocaleString()}
                      </div>
                    </div>
                  </div>
                </div>
              </Link>
            ) : (
              <div className="flex items-center justify-between p-3 rounded-lg">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-lg bg-muted flex items-center justify-center">
                    <Zap className="h-5 w-5 text-muted-foreground" />
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">Power Balance</div>
                    <div className="font-semibold text-muted-foreground">
                      {parseFloat(userStats?.energyPower || 0).toLocaleString()}
                    </div>
                  </div>
                </div>
                <Lock className="h-3.5 w-3.5 text-muted-foreground" title="Purchase a bot plan to unlock" />
              </div>
            )}

            {/* Investment Amount */}
            <Link href="/settings">
              <div className="flex items-center justify-between p-3 rounded-lg hover:bg-accent transition-colors cursor-pointer">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-lg bg-amber-100 flex items-center justify-center">
                    <TrendingUp className="h-5 w-5 text-amber-600" />
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">Trading Capital</div>
                    <div className="font-semibold text-amber-600">
                      ${parseFloat(userStats?.investmentAmount || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </div>
                  </div>
                </div>
              </div>
            </Link>
          </div>
        )}
        
        <DropdownMenuSeparator />

        {/* Not a DropdownMenuItem on purpose - Radix closes the menu on item click,
            which would be annoying to re-open every time you flip the theme. */}
        <div className="flex items-center justify-between px-2 py-1.5">
          <div className="flex items-center gap-2 text-sm">
            {theme === 'dark' ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
            <span>Theme</span>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={theme === 'dark'}
            aria-label="Toggle dark mode"
            onClick={(e) => { e.stopPropagation(); toggleTheme(); }}
            className={`relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors ${
              theme === 'dark' ? 'bg-primary' : 'bg-muted'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
                theme === 'dark' ? 'translate-x-4' : 'translate-x-0.5'
              }`}
            />
          </button>
        </div>

        <DropdownMenuSeparator />

        <DropdownMenuItem onClick={handleLogout} className="cursor-pointer">
          <LogOut className="mr-2 h-4 w-4" />
          <span>Logout</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
