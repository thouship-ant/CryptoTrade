'use client';

import { LegalPageLayout, LegalSection } from '@/components/LegalPageLayout';

// NOTE: starting-point template for the operator - have it reviewed by a lawyer for the
// jurisdiction(s) you operate in (crypto services are regulated differently per country)
// and fill in the governing-law clause before going live.
export default function TermsPage() {
  return (
    <LegalPageLayout title="Terms & Conditions">
      <LegalSection>
        These Terms & Conditions (&quot;Terms&quot;) govern your access to and use of ANT Crypto Robo Trade,
        an algorithmic crypto trading platform operated by ANT (&quot;we&quot;, &quot;us&quot;, &quot;our&quot;). By registering,
        logging in, or otherwise using the platform, you agree to these Terms. If you do not agree,
        please do not use the platform.
      </LegalSection>

      <LegalSection heading="1. The Service">
        ANT Crypto Robo Trade provides bot-driven trading signals and automated order placement on
        your own Binance account, using an API key you create and connect. Bot plans and power
        (which gates how long the bot keeps opening new trades) are purchased separately.
      </LegalSection>

      <LegalSection heading="2. Not Investment Advice">
        ANT Crypto Robo Trade is a trade-automation tool, not a registered investment, financial or
        tax advisor. Nothing on the platform is a recommendation to buy or sell any asset. Crypto
        assets are highly volatile; trading spot and especially leveraged futures carries a high
        risk of loss, including the loss of your entire capital and, with leverage, more than you
        deposited. Past performance - including any figure shown on the platform - does not
        indicate future results, and no profit is guaranteed. You are solely responsible for your
        trading decisions, your tax obligations, and for checking that crypto trading is lawful where
        you live.
      </LegalSection>

      <LegalSection heading="3. Your Binance Account">
        The bot trades through a Binance account you own and a trade-only API key you provide. You
        must disable withdrawals on that key, and the platform rejects keys that can withdraw. We
        never hold your trading capital - it stays on Binance at all times. You are responsible for
        the funds and margin in that account, for keeping the API key valid, and for revoking it on
        Binance if you stop using the platform.
      </LegalSection>

      <LegalSection heading="4. Accounts & Referrals">
        You are responsible for maintaining the confidentiality of your account credentials and for
        all activity under your account. Referring another user to a paid bot plan earns you a
        commission on that purchase, credited to your earnings wallet - see our Refunds &
        Cancellations page for how plan purchases themselves are handled.
      </LegalSection>

      <LegalSection heading="5. Wallet, Plans & Billing">
        Bot plans and power are paid for in USDT from your in-app activation balance, which you fund
        by sending USDT (BEP20 / BSC) to the address shown in the wallet and submitting the
        transaction hash for verification. Wallet balance is split into a withdrawable earnings
        balance (referral commissions) and a non-withdrawable activation balance used only for plan
        and power purchases. Blockchain transfers are irreversible; sending funds to the wrong
        address or network is at your own risk.
      </LegalSection>

      <LegalSection heading="6. Acceptable Use">
        You agree not to use the platform for any unlawful purpose (including money laundering or
        sanctions evasion), to attempt to gain unauthorized access to another user account or data,
        or to interfere with the platform normal operation.
      </LegalSection>

      <LegalSection heading="7. Suspension & Termination">
        We may suspend access if these Terms are violated, if power runs out (the bot stops opening
        new trades until topped up), or if Binance access can no longer be validated. You may stop
        using the platform at any time.
      </LegalSection>

      <LegalSection heading="8. Limitation of Liability">
        The platform is provided &quot;as is.&quot; To the maximum extent permitted by law, we are not
        liable for trading losses, indirect or consequential damages, or losses arising from
        exchange outages, API failures, slippage, liquidations, or market conditions outside our
        control. Nothing in these Terms limits liability that cannot be excluded under applicable
        law.
      </LegalSection>

      <LegalSection heading="9. Changes to These Terms">
        We may update these Terms from time to time. Continued use of the platform after an
        update constitutes acceptance of the revised Terms.
      </LegalSection>

      <LegalSection heading="10. Governing Law">
        These Terms are governed by the laws of the jurisdiction in which the operator is
        established, without regard to conflict-of-law principles.
      </LegalSection>

      <LegalSection heading="11. Contact">
        Questions about these Terms? Reach out from the Contact Us page.
      </LegalSection>
    </LegalPageLayout>
  );
}
