'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Activity, FileText, BarChart3, Wallet, ShoppingCart, Users, Settings, ShieldCheck } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import UserDropdown from './UserDropdown';
import MobileSidebar from './MobileSidebar';
import { getApiBaseUrl } from '@/lib/apiConfig';

export default function Navigation({ userName }) {
  const [userId, setUserId] = useState('');
  const [role, setRole] = useState('');
  const pathname = usePathname();

  useEffect(() => {
    const storedUserId = localStorage.getItem('user_id');
    if (!storedUserId) {
      return;
    }
    setUserId(storedUserId);

    fetch(`${getApiBaseUrl()}/api/config/${storedUserId}`)
      .then((res) => res.json())
      .then((data) => {
        const fetchedRole = (data?.role || '').toLowerCase();
        setRole(fetchedRole);
        localStorage.setItem('role', fetchedRole);
      })
      .catch(() => {});
  }, []);

  return (
    <nav className="bg-background border-b sticky top-0 z-50 themed-bg-pattern">
      <div className="container mx-auto px-4 py-3">
        <div className="relative flex items-center justify-between">
          <div className="flex items-center gap-4">
            <MobileSidebar />
            <Link href="/dashboard" className="hidden md:block">
              <img src="/assets/images/app_name_light.png" alt="ANT Crypto Robo Trade" height={50} width={200} className="dark:hidden"/>
              <img src="/assets/images/app_name_dark.png" alt="ANT Crypto Robo Trade" height={50} width={200} className="hidden dark:block"/>
            </Link>
            <div className="hidden md:flex gap-4">
              <Link href="/dashboard">
                <Button variant="ghost" size="sm" className={`gap-2 ${pathname === '/dashboard' ? 'bg-accent text-primary' : ''}`}>
                  <Activity className="h-4 w-4" />
                  Dashboard
                </Button>
              </Link>
              <Link href="/orders">
                <Button variant="ghost" size="sm" className={`gap-2 ${pathname === '/orders' ? 'bg-accent text-primary' : ''}`}>
                  <FileText className="h-4 w-4" />
                  Orders
                </Button>
              </Link>
              <Link href="/reports">
                <Button variant="ghost" size="sm" className={`gap-2 ${pathname === '/reports' ? 'bg-accent text-primary' : ''}`}>
                  <BarChart3 className="h-4 w-4" />
                  Reports
                </Button>
              </Link>
              {/* The Demo role (a paper-trading utility account, not a
                  real trading user) has no wallet/bot-plan/settings to manage. */}
              {role !== 'demo' && (
                <Link href="/wallet">
                  <Button variant="ghost" size="sm" className={`gap-2 ${pathname === '/wallet' ? 'bg-accent text-primary' : ''}`}>
                    <Wallet className="h-4 w-4" />
                    Wallet
                  </Button>
                </Link>
              )}
              {role !== 'demo' && (
                <Link href="/bot-plans">
                  <Button variant="ghost" size="sm" className={`gap-2 ${pathname === '/bot-plans' ? 'bg-accent text-primary' : ''}`}>
                    <ShoppingCart className="h-4 w-4" />
                    Bot Plans
                  </Button>
                </Link>
              )}
              <Link href="/referral">
                <Button variant="ghost" size="sm" className={`gap-2 ${pathname === '/referral' ? 'bg-accent text-primary' : ''}`}>
                  <Users className="h-4 w-4" />
                  Referral
                  <Badge variant="secondary" className="text-xs bg-amber-100 text-amber-800 mb-5 w-8 h-5 flex items-center justify-center">
                    <span className="text-xs">New</span>
                  </Badge>
                </Button>
              </Link>
              {role !== 'demo' && (
                <Link href="/settings">
                  <Button variant="ghost" size="sm" className={`gap-2 ${pathname === '/settings' ? 'bg-accent text-primary' : ''}`}>
                    <Settings className="h-4 w-4" />
                    Settings
                  </Button>
                </Link>
              )}
              {role === 'admin' && (
                <Link href="/admin">
                  <Button variant="ghost" size="sm" className={`gap-2 ${pathname === '/admin' ? 'bg-accent text-primary' : ''}`}>
                    <ShieldCheck className="h-4 w-4" />
                    Admin
                  </Button>
                </Link>
              )}
            </div>
          </div>

          <Link
            href="/dashboard"
            className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 md:hidden"
          >
            <img src="/assets/images/app_name_light.png" alt="ANT Crypto Robo Trade" height={50} width={200} className="dark:hidden" />
            <img src="/assets/images/app_name_dark.png" alt="ANT Crypto Robo Trade" height={50} width={200} className="hidden dark:block" />
          </Link>

          <div className="flex items-center gap-4">
            <UserDropdown userName={userName} userId={userId} />
          </div>
        </div>
      </div>
    </nav>
  );
}
