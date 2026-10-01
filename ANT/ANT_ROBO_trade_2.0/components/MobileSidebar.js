'use client';

import { useState, useEffect } from 'react';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Menu, Activity, FileText, BarChart3, Wallet, ShoppingCart, Settings, HelpCircle, Users, ShieldCheck } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { getApiBaseUrl } from '@/lib/apiConfig';

export default function MobileSidebar() {
  const [open, setOpen] = useState(false);
  const [role, setRole] = useState('');
  const pathname = usePathname();

  useEffect(() => {
    const storedUserId = localStorage.getItem('user_id');
    if (!storedUserId) {
      return;
    }

    fetch(`${getApiBaseUrl()}/api/config/${storedUserId}`)
      .then((res) => res.json())
      .then((data) => {
        const fetchedRole = (data?.role || '').toLowerCase();
        setRole(fetchedRole);
        localStorage.setItem('role', fetchedRole);
      })
      .catch(() => {});
  }, []);

  // The Demo role (a paper-trading/backtest utility account, not a real
  // trading user) has no wallet/bot-plan/settings to manage - those pages are
  // hidden from its nav same as Admin is only ever the reserved account.
  const menuItems = [
    { href: '/dashboard', icon: Activity, label: 'Dashboard' },
    { href: '/orders', icon: FileText, label: 'Orders' },
    { href: '/reports', icon: BarChart3, label: 'Reports' },
    ...(role !== 'demo' ? [{ href: '/wallet', icon: Wallet, label: 'Wallet' }] : []),
    ...(role !== 'demo' ? [{ href: '/bot-plans', icon: ShoppingCart, label: 'Bot Plans' }] : []),
    { href: '/referral', icon: Users, label: 'Referral', badge: 'New' },
    { href: '/faq', icon: HelpCircle, label: 'FAQ' },
    ...(role !== 'demo' ? [{ href: '/settings', icon: Settings, label: 'Settings' }] : []),
    ...(role === 'admin' ? [{ href: '/admin', icon: ShieldCheck, label: 'Admin' }] : []),
  ];

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button variant="ghost" size="icon" className="md:hidden">
          <Menu className="h-6 w-6" />
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="w-[280px] sm:w-[320px] themed-bg-pattern">
        <SheetHeader>
          <SheetTitle className="text-left text-xl font-bold text-primary">
            <img src="/assets/images/app_name_light.png" alt="ANT Crypto Robo Trade" height={50} width={150} className="dark:hidden"/>
            <img src="/assets/images/app_name_dark.png" alt="ANT Crypto Robo Trade" height={50} width={150} className="hidden dark:block"/>
          </SheetTitle>
        </SheetHeader>
        <div className="mt-6 flex flex-col gap-2 z-1000">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setOpen(false)}
              >
                <div
                  className={`flex items-center justify-between gap-3 px-4 py-3 rounded-lg transition-colors ${
                    isActive
                      ? 'bg-accent text-primary'
                      : 'hover:bg-accent text-foreground'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Icon className={`h-5 w-5 ${
                      isActive ? 'text-primary' : 'text-muted-foreground'
                    }`} />
                    <span className={`font-medium ${
                      isActive ? 'text-primary' : 'text-foreground'
                    }`}>
                      {item.label}
                    </span>
                  </div>
                  {item.badge && (
                    <Badge variant="secondary" className="text-xs bg-amber-100 text-amber-800 mb-5 w-8 h-5 flex items-center justify-center">
                      <span className="text-xs">New</span>
                    </Badge>
                  )}
                </div>
              </Link>
            );
          })}
        </div>

        {/* Footer */}
        <div className="absolute bottom-6 left-6 right-6">
          <div className="p-4 bg-accent rounded-lg">
            <p className="text-xs text-muted-foreground text-center">
              ANT © 2026. All rights reserved.
            </p>
            <p className="text-xs text-muted-foreground text-center mt-1">
              Version 2.0.0
            </p>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
