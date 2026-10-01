'use client';

import { LegalPageLayout, LegalSection } from '@/components/LegalPageLayout';
import { Mail } from 'lucide-react';

// Set NEXT_PUBLIC_SUPPORT_EMAIL at build time for your deployment.
const SUPPORT_EMAIL = process.env.NEXT_PUBLIC_SUPPORT_EMAIL || 'support@antcryptotrade.example';

export default function ContactUsPage() {
  return (
    <LegalPageLayout title="Contact Us">
      <LegalSection>
        Have a question about your plan, wallet, Binance connection, or the platform itself?
        Reach out and we will get back to you as soon as we can.
      </LegalSection>

      <a
        href={`mailto:${SUPPORT_EMAIL}`}
        className="flex items-center gap-3 rounded-md border border-border bg-card p-4 hover:bg-accent/50"
      >
        <Mail className="h-5 w-5 text-primary" />
        <div>
          <div className="text-xs font-semibold uppercase text-muted-foreground">Email us at</div>
          <div className="text-base font-bold text-foreground">{SUPPORT_EMAIL}</div>
        </div>
      </a>

      <LegalSection heading="Deposit or withdrawal queries">
        Please include the transaction hash (TxID) and the amount - it lets us find a USDT
        transfer on-chain in seconds. Never send us your Binance API secret or any password.
      </LegalSection>

      <LegalSection heading="Support hours">
        We typically respond within 1-2 business days.
      </LegalSection>
    </LegalPageLayout>
  );
}
