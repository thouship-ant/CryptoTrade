'use client';

import { LegalPageLayout, LegalSection } from '@/components/LegalPageLayout';

export default function PrivacyPage() {
  return (
    <LegalPageLayout title="Privacy Policy">
      <LegalSection>
        This Privacy Policy explains what information ANT Crypto Robo Trade collects, how we use
        it, and the choices you have. It applies to your use of the web app.
      </LegalSection>

      <LegalSection heading="1. Information We Collect">
        Account details (name, username, mobile number, email), the Binance API key and secret you
        provide so the bot can trade for you, your trading activity and P&L generated through the
        platform, and wallet records (USDT deposit and withdrawal requests, transaction hashes and
        withdrawal addresses). We never ask for your Binance login password.
      </LegalSection>

      <LegalSection heading="2. How We Use It">
        To place and manage trades on your Binance account, show you your own
        dashboard/reports/orders, verify and process wallet deposits and withdrawals, calculate
        referral commissions, and send you account and security emails (such as one-time codes).
      </LegalSection>

      <LegalSection heading="3. Exchange Credentials">
        Your Binance API secret is encrypted before it is stored and is never shown back to anyone,
        including you. We ask that your key has withdrawals disabled, and we reject keys that can
        withdraw. You can replace your key at any time from Settings, and you should revoke it on
        Binance if you stop using the platform; doing so stops the bot from placing further orders.
      </LegalSection>

      <LegalSection heading="4. Payment Data">
        Deposits and withdrawals are on-chain USDT transfers. Blockchain transactions are public by
        design: the addresses and amounts involved can be seen by anyone, and we cannot remove them.
      </LegalSection>

      <LegalSection heading="5. Data Sharing">
        We do not sell your personal data. It is shared only with Binance (to place your own orders
        through the API key you provided) and our email provider (to deliver one-time codes and
        notices) - never with unrelated third parties, except where the law requires it. Coin logos
        on some pages are loaded from a public CDN, which sees your IP address like any website.
      </LegalSection>

      <LegalSection heading="6. Data Retention">
        We retain account and trading history for as long as your account is active, and as
        needed to meet recordkeeping obligations for financial transactions after that.
      </LegalSection>

      <LegalSection heading="7. Your Choices">
        You can update your account details and replace your exchange key from Settings at any
        time. To request account deletion, contact us from the Contact Us page.
      </LegalSection>

      <LegalSection heading="8. Security">
        Exchange secrets are encrypted at rest, passwords are stored as salted hashes, and all
        traffic uses HTTPS. No online service can guarantee absolute security, but we take
        reasonable measures to protect your data.
      </LegalSection>

      <LegalSection heading="9. Changes to This Policy">
        We may update this Privacy Policy from time to time. Continued use of the platform after
        an update constitutes acceptance of the revised policy.
      </LegalSection>

      <LegalSection heading="10. Contact">
        Questions about this policy? Reach out from the Contact Us page.
      </LegalSection>
    </LegalPageLayout>
  );
}
