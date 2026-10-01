'use client';

import { LegalPageLayout, LegalSection } from '@/components/LegalPageLayout';

export default function RefundsPage() {
  return (
    <LegalPageLayout title="Refunds & Cancellations">
      <LegalSection>
        This page explains our policy on wallet deposits, bot plan purchases, and withdrawals on
        ANT Crypto Robo Trade. All wallet amounts are in USDT.
      </LegalSection>

      <LegalSection heading="Wallet deposits">
        Deposits are USDT sent on-chain (BEP20 / BSC) to the address shown in the wallet. After you
        submit the transaction hash, an admin verifies the transfer and credits your activation
        balance. Blockchain transfers are irreversible: funds sent to the wrong address, on the
        wrong network, or in a different coin cannot be recovered by us. If a valid USDT transfer to
        our address is not credited, contact support with the transaction hash.
      </LegalSection>

      <LegalSection heading="Bot plan & power purchases">
        Once a bot plan or power top-up is purchased from your activation balance, it is
        non-refundable - the amount is deducted immediately to activate the plan or add power. If
        you no longer want to use the bot, you can stop it from Settings; your remaining power and
        any active plan period are not refunded.
      </LegalSection>

      <LegalSection heading="Withdrawing your earnings">
        Your earnings wallet (referral commissions) can be withdrawn in USDT (BEP20) to your own
        address from the Wallet page, less a flat network fee shown before you confirm. Withdrawals
        are sent manually by an admin and are typically processed within 1-3 business days.
        Activation balance cannot be withdrawn - it can only be used for plan and power purchases,
        though you can move earnings into it with a transfer.
      </LegalSection>

      <LegalSection heading="Trading losses">
        The bot places real orders through your own Binance account, using your own capital. We do
        not refund trading losses - see our Terms & Conditions for how the platform role differs
        from investment advice.
      </LegalSection>

      <LegalSection heading="Questions">
        For anything not covered here, reach out from the Contact Us page.
      </LegalSection>
    </LegalPageLayout>
  );
}
