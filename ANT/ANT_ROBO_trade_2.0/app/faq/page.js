'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Badge } from '@/components/ui/badge';
import { HelpCircle, ShoppingCart, Wallet, TrendingUp, Shield, Zap } from 'lucide-react';
import Navigation from '@/components/Navigation';

const SUPPORT_EMAIL = process.env.NEXT_PUBLIC_SUPPORT_EMAIL || 'support@antcryptotrade.example';

const COLOR_CLASSES = {
  gold: 'from-amber-400 to-amber-600',
  green: 'from-green-500 to-green-600',
  orange: 'from-orange-500 to-orange-600',
  yellow: 'from-yellow-500 to-yellow-600',
  red: 'from-red-500 to-red-600',
};

// Keep the referral percentages in sync with LEVEL_COMMISSION_PERCENTS in backend/main.py,
// and the wallet limits with MIN_DEPOSIT_USDT / MIN_WITHDRAWAL_USDT / WITHDRAWAL_FEE_USDT.
const FAQ_CATEGORIES = [
  {
    category: 'Getting Started',
    icon: HelpCircle,
    color: 'gold',
    faqs: [
      {
        question: 'What is ANT Crypto Robo Trade?',
        answer: 'It is an automated crypto trading platform. A bot opens and closes positions on Binance USDT pairs for you, 24/7, using technical signals, and this app lets you follow every position, order and day of P&L in real time.',
      },
      {
        question: 'How do I get started?',
        answer: 'Register and verify your email, add USDT to your activation balance from the Wallet page, buy a bot plan, then open Settings and connect a Binance API key (trade-only, withdrawals disabled). Verify the connection, set your trade size and risk limits, and start the bot.',
      },
      {
        question: 'Does the platform hold my trading funds?',
        answer: 'No. Your trading capital stays on your own Binance account at all times. The wallet in this app only holds the USDT you pay for plans with, and any referral earnings.',
      },
    ],
  },
  {
    category: 'Binance & API Keys',
    icon: Shield,
    color: 'red',
    faqs: [
      {
        question: 'How do I create the API key?',
        answer: 'On Binance go to Profile > API Management > Create API. Enable "Spot & Margin Trading" (and "Futures" if you want short or leveraged trades). Leave "Enable Withdrawals" switched off. Paste the key and secret into Settings and press Verify.',
      },
      {
        question: 'Why is my key rejected?',
        answer: 'Keys are rejected if Binance does not accept them (typo, deleted key, or an IP restriction that does not include our server), if the key can withdraw funds, or if Spot & Margin Trading is not enabled. The error message tells you which.',
      },
      {
        question: 'How safe is my API secret?',
        answer: 'The secret is encrypted before it is stored and is never displayed again - not even to you. Because withdrawals must be disabled, a key cannot move your funds off Binance. You can revoke the key on Binance at any time, which immediately stops the bot.',
      },
    ],
  },
  {
    category: 'Bot Trading',
    icon: ShoppingCart,
    color: 'gold',
    faqs: [
      {
        question: 'What is a trading bot?',
        answer: 'It is an automated system that watches the market, opens positions when its signals fire, and closes them at your target, your stoploss or on an exit signal. Each position shows the signal that triggered it.',
      },
      {
        question: 'How do bot plans work?',
        answer: 'A plan is a one-year subscription paid in USDT from your activation balance. When it expires you can buy it again. Spot plans trade long only; futures plans can also go short and use leverage.',
      },
      {
        question: 'What is the difference between a bot plan and power?',
        answer: 'The plan licenses the bot for a year. Power is the fuel it consumes while trading: when it drops below the minimum the bot stops opening new trades (open positions are still managed) until you top it up. Power does not improve returns.',
      },
      {
        question: 'Can I control the bot?',
        answer: 'Yes. In Settings you choose the amount per trade, the maximum number of open trades, leverage, stoploss and target percentages, and whether long and/or short trades are allowed. You can pause the bot at any time; positions that are already open continue to be managed.',
      },
    ],
  },
  {
    category: 'Wallet & Payments',
    icon: Wallet,
    color: 'green',
    faqs: [
      {
        question: 'How do I add funds?',
        answer: 'Open Wallet > Add Funds. Send USDT on the BEP20 (BSC) network to the address shown, then enter the amount and the transaction hash (TxID). An admin verifies the transfer on-chain and credits your activation balance, usually within a few hours. Use only the network shown - funds sent on another network cannot be recovered.',
      },
      {
        question: 'What is the difference between the two balances?',
        answer: 'The activation balance is funded by deposits and pays for bot and power plans; it cannot be withdrawn. The earnings wallet holds referral commissions; it can be withdrawn on-chain or transferred into the activation balance.',
      },
      {
        question: 'How do withdrawals work?',
        answer: 'Request a withdrawal of your earnings to your own BEP20 address (minimum 10 USDT, flat 1 USDT network fee). The amount is held immediately and an admin sends the USDT, typically within 1-3 business days. If a request is rejected the amount is returned to your earnings wallet.',
      },
    ],
  },
  {
    category: 'Trading & Performance',
    icon: TrendingUp,
    color: 'orange',
    faqs: [
      {
        question: 'How can I track performance?',
        answer: 'The Dashboard shows your trading capital, total, daily and monthly P/L, and live open positions. Reports has the full trade history with win rate, cumulative P/L by coin and a daily profit chart. Orders lists every individual Binance order.',
      },
      {
        question: 'What returns can I expect?',
        answer: 'There are no guaranteed or expected returns. Crypto is volatile and leveraged trading can lose more than you commit. Results depend on market conditions and your settings, and past performance does not predict future results. Only trade money you can afford to lose.',
      },
      {
        question: 'Which coins does the bot trade?',
        answer: 'Binance USDT pairs with enough liquidity, chosen by the bot from volatility, volume and technical indicators. The pairs it actually traded for you appear in Reports > Cumulative P/L by Coin.',
      },
      {
        question: 'When does the bot trade?',
        answer: 'Crypto markets never close, so the bot runs around the clock, every day of the year, including weekends and holidays.',
      },
    ],
  },
  {
    category: 'Referral Program',
    icon: Zap,
    color: 'yellow',
    faqs: [
      {
        question: 'How does the referral program work?',
        answer: 'Share your referral code or link. When someone registers with it and buys a bot plan you earn a commission: 15% from your direct referrals, 10% from their referrals, and 5% from the third level. Commissions are credited instantly to your earnings wallet.',
      },
      {
        question: 'Where do I find my referral code?',
        answer: 'On the Referral page, which also has a ready-made link and WhatsApp and Telegram share buttons.',
      },
      {
        question: 'Is there a limit to referral earnings?',
        answer: 'No limit is applied to the number of people you refer. Commission is only paid on bot plan purchases, not on deposits or power top-ups.',
      },
    ],
  },
  {
    category: 'Account & Support',
    icon: HelpCircle,
    color: 'gold',
    faqs: [
      {
        question: 'What if I forget my password?',
        answer: 'Choose "Forgot Password" on the login page, enter your username or email, and we will email a 6-digit code. Enter it with your new password to reset it.',
      },
      {
        question: 'Why am I asked for a code when I log in?',
        answer: 'For security we ask you to confirm a one-time code, sent to your email, about once a month even when your password is correct.',
      },
      {
        question: 'How do I contact support?',
        answer: `Email ${SUPPORT_EMAIL}. For deposit or withdrawal questions include the transaction hash. Never share your password or Binance API secret with anyone.`,
      },
    ],
  },
];

export default function FAQPage() {
  const router = useRouter();
  const [userName, setUserName] = useState('');

  useEffect(() => {
    const storedUserId = localStorage.getItem('user_id');
    if (!storedUserId) {
      router.push('/');
      return;
    }
    setUserName(localStorage.getItem('full_name') || '');
  }, [router]);

  return (
    <div className="min-h-screen bg-background">
      <Navigation userName={userName} />

      <div className="container mx-auto px-4 py-8">
        <div className="mb-8 text-center">
          <div className="flex items-center justify-center gap-3 mb-3">
            <HelpCircle className="h-10 w-10 text-amber-600" />
            <h1 className="text-4xl font-bold">Frequently Asked Questions</h1>
          </div>
          <p className="text-muted-foreground text-lg">Find answers to common questions about our platform</p>
        </div>

        <div className="space-y-6">
          {FAQ_CATEGORIES.map((category, catIndex) => {
            const Icon = category.icon;
            return (
              <Card key={category.category} className="overflow-hidden">
                <CardHeader className={`bg-gradient-to-r ${COLOR_CLASSES[category.color]} text-black`}>
                  <CardTitle className="flex items-center gap-3">
                    <Icon className="h-6 w-6" />
                    {category.category}
                    <Badge variant="secondary" className="ml-2">{category.faqs.length} Questions</Badge>
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-6">
                  <Accordion type="single" collapsible className="w-full">
                    {category.faqs.map((faq, faqIndex) => (
                      <AccordionItem key={faq.question} value={`item-${catIndex}-${faqIndex}`}>
                        <AccordionTrigger className="text-left font-medium hover:text-primary">{faq.question}</AccordionTrigger>
                        <AccordionContent className="text-muted-foreground leading-relaxed">{faq.answer}</AccordionContent>
                      </AccordionItem>
                    ))}
                  </Accordion>
                </CardContent>
              </Card>
            );
          })}
        </div>

        <Card className="mt-8">
          <CardHeader>
            <CardTitle>Still have questions?</CardTitle>
            <CardDescription>Our support team is here to help</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="p-4 bg-muted rounded-lg text-center">
              <div className="text-2xl mb-2">📧</div>
              <div className="font-medium">Email Support</div>
              <a href={`mailto:${SUPPORT_EMAIL}`} className="text-sm text-primary hover:underline mt-1 inline-block">{SUPPORT_EMAIL}</a>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
