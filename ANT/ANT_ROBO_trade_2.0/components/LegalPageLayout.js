'use client';

import Link from 'next/link';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowLeft } from 'lucide-react';

// Shared shell for the login footer's policy pages (Terms, Privacy, Refunds,
// Contact Us) - deliberately standalone, not wrapped in the authenticated
// Navigation shell other pages use (see app/faq/page.js), since these must be
// reachable from the login page before anyone has signed in. Mirrors
// Inventory_stock/inventory-enterprice_2.0's LegalPageLayout/LegalSection
// pattern (same footer-links-to-policy-pages structure, referenced there as
// antstockpulse.pro), adapted to this app's web/Tailwind/shadcn conventions
// instead of that app's React Native one.
export function LegalPageLayout({ title, children }) {
  return (
    <div className="min-h-screen bg-background px-4 py-8">
      <div className="mx-auto max-w-2xl">
        <Link href="/" className="mb-6 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" /> Back to login
        </Link>
        <Card>
          <CardHeader>
            <CardTitle className="text-2xl">{title}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6 text-sm leading-6 text-foreground">
            {children}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export function LegalSection({ heading, children }) {
  return (
    <section>
      {heading && <h2 className="mb-1.5 text-base font-semibold text-foreground">{heading}</h2>}
      <p className="text-muted-foreground">{children}</p>
    </section>
  );
}
