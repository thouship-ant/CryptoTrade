'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Users, Copy, Check, Share2, Gift } from 'lucide-react';
import Navigation from '@/components/Navigation';
import { getApiBaseUrl } from '@/lib/apiConfig';
import TransactionList from '@/components/TransactionList';
import TablePagination from '@/components/TablePagination';

export default function ReferralPage() {
  const router = useRouter();
  const [userId, setUserId] = useState('');
  const [userName, setUserName] = useState('');
  const [userConfig, setUserConfig] = useState(null);
  const [wallet, setWallet] = useState(null);
  const [copied, setCopied] = useState(false);
  const [copiedLink, setCopiedLink] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const storedUserId = localStorage.getItem('user_id');
    const storedUserName = localStorage.getItem('full_name');
    
    if (!storedUserId) {
      router.push('/');
      return;
    }
    
    setUserId(storedUserId);
    setUserName(storedUserName);
    fetchData(storedUserId);
  }, [router]);

  const fetchData = async (uid) => {
    try {
      const [configRes, walletRes] = await Promise.all([
        fetch(`${getApiBaseUrl()}/api/config/${uid}`),
        fetch(`${getApiBaseUrl()}/api/wallet/${uid}`)
      ]);

      const configData = await configRes.json();
      const walletData = await walletRes.json();

      setUserConfig(configData);
      setWallet(walletData.wallet);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const referralCode = userConfig?.referal_code || '';
  const referralLink = `${typeof window !== 'undefined' ? window.location.origin : ''}/?ref=${referralCode}`;

  const copyCode = () => {
    navigator.clipboard.writeText(referralCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const copyLink = () => {
    navigator.clipboard.writeText(referralLink);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2000);
  };

  const shareViaWhatsApp = () => {
    const message = `Join me on ANT Crypto Robo Trade! Use my referral code ${referralCode} or click this link: ${referralLink}`;
    window.open(`https://wa.me/?text=${encodeURIComponent(message)}`, '_blank');
  };

  const shareViaTelegram = () => {
    const message = `Join me on ANT Crypto Robo Trade! Use my referral code ${referralCode} or click this link: ${referralLink}`;
    window.open(`https://t.me/share/url?url=${encodeURIComponent(referralLink)}&text=${encodeURIComponent(message)}`, '_blank');
  };

  // Keep in sync with LEVEL_COMMISSION_PERCENTS in backend/main.py
  const commissionLevels = [
    { level: 1, percentage: 15, description: 'Direct Referrals', color: 'from-green-500 to-green-600', icon: '🎯',
      detail: 'Earn 15% commission on bot plan purchases made by users you directly refer' },
    { level: 2, percentage: 10, description: 'Second Level', color: 'from-amber-400 to-amber-600', icon: '🥈',
      detail: 'Earn 10% on purchases made by the users your referrals bring in' },
    { level: 3, percentage: 5, description: 'Third Level', color: 'from-yellow-500 to-yellow-600', icon: '🥉',
      detail: 'Earn 5% on purchases one level further down your network' },
  ];

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-amber-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-accent/30">
      <Navigation userName={userName} />

      <div className="container mx-auto px-4 py-8">
        <div className="mb-8 text-center">
          <div className="flex items-center justify-center gap-3 mb-3">
            <Users className="h-10 w-10 text-amber-600" />
            <h1 className="text-4xl font-bold">Referral Program</h1>
          </div>
          <p className="text-muted-foreground text-lg">
            Earn commission by referring friends and family
          </p>
        </div>

        {/* Earnings Overview */}
        <div className="grid gap-6 mb-8 max-w-md mx-auto">
          <Card className="border-l-4 border-green-500">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Gift className="h-5 w-5 text-green-600" />
                Referral Income
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-green-600">
                ${parseFloat(wallet?.referal_income || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
              <p className="text-sm text-muted-foreground mt-1">Total earned from referrals (USDT)</p>
            </CardContent>
          </Card>
        </div>

        {/* Referral Code & Link */}
        <Card className="mb-8 bg-gradient-to-r from-accent to-accent/60">
          <CardHeader>
            <CardTitle>Your Referral Code</CardTitle>
            <CardDescription>Share this code or link with others to earn rewards</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Referral Code</label>
              <div className="flex gap-2">
                <Input value={referralCode} readOnly autoComplete="off" className="text-lg font-mono font-bold" />
                <Button onClick={copyCode} variant="outline">
                  {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                </Button>
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Referral Link</label>
              <div className="flex gap-2">
                <Input value={referralLink} readOnly autoComplete="off" className="text-sm" />
                <Button onClick={copyLink} variant="outline">
                  {copiedLink ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                </Button>
              </div>
            </div>

            <div className="flex gap-2 pt-2">
              <Button onClick={shareViaWhatsApp} className="flex-1 gap-2 bg-green-600 hover:bg-green-700">
                <Share2 className="h-4 w-4" />
                Share via WhatsApp
              </Button>
              <Button onClick={shareViaTelegram} className="flex-1 gap-2 bg-amber-600 hover:bg-amber-700">
                <Share2 className="h-4 w-4" />
                Share via Telegram
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Commission Structure */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold mb-6 text-center">3-Level Commission Structure</h2>
          <div className="grid md:grid-cols-3 gap-6">
            {commissionLevels.map((level) => (
              <Card key={level.level} className="relative overflow-hidden">
                <div className={`absolute top-0 left-0 right-0 h-2 bg-gradient-to-r ${level.color}`}></div>
                <CardHeader className="text-center pb-4 pt-8">
                  <div className="text-4xl mb-2">{level.icon}</div>
                  <CardTitle className="text-xl">Level {level.level}</CardTitle>
                  <CardDescription>{level.description}</CardDescription>
                </CardHeader>
                <CardContent className="text-center">
                  <div className="text-5xl font-bold bg-gradient-to-r from-amber-400 to-amber-600 bg-clip-text text-transparent mb-4">
                    {level.percentage}%
                  </div>
                  <p className="text-sm text-muted-foreground">{level.detail}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        {/* How It Works */}
        <Card>
          <CardHeader>
            <CardTitle>How Referral Program Works</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-4 gap-6">
              <div className="text-center">
                <div className="h-12 w-12 mx-auto rounded-full bg-amber-100 flex items-center justify-center mb-3">
                  <span className="text-2xl font-bold text-amber-600">1</span>
                </div>
                <h3 className="font-semibold mb-2">Share Your Code</h3>
                <p className="text-sm text-muted-foreground">
                  Share your unique referral code or link with friends
                </p>
              </div>
              <div className="text-center">
                <div className="h-12 w-12 mx-auto rounded-full bg-amber-100 flex items-center justify-center mb-3">
                  <span className="text-2xl font-bold text-amber-600">2</span>
                </div>
                <h3 className="font-semibold mb-2">They Register</h3>
                <p className="text-sm text-muted-foreground">
                  Your friends register using your code
                </p>
              </div>
              <div className="text-center">
                <div className="h-12 w-12 mx-auto rounded-full bg-green-100 flex items-center justify-center mb-3">
                  <span className="text-2xl font-bold text-green-600">3</span>
                </div>
                <h3 className="font-semibold mb-2">They Purchase</h3>
                <p className="text-sm text-muted-foreground">
                  When they buy a bot plan
                </p>
              </div>
              <div className="text-center">
                <div className="h-12 w-12 mx-auto rounded-full bg-yellow-100 flex items-center justify-center mb-3">
                  <span className="text-2xl font-bold text-yellow-600">4</span>
                </div>
                <h3 className="font-semibold mb-2">You Earn</h3>
                <p className="text-sm text-muted-foreground">
                  Commission lands instantly in your Earnings Wallet (USDT)
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Level-wise Purchase Details */}
        <div className="mt-8">
          <h2 className="text-2xl font-bold mb-6 text-center">Your Downline Purchase History</h2>
          <div className="space-y-6">
            {commissionLevels.map((level) => (
              <LevelPurchaseSection key={level.level} userId={userId} level={level} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// One level's paginated purchase/commission history, backed by
// /api/referral/level-purchases/{user_id} - reuses the same list template and
// pagination (with page-size dropdown) as the Wallet page's Transaction History.
function LevelPurchaseSection({ userId, level }) {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(5);
  const [totalPages, setTotalPages] = useState(1);

  useEffect(() => {
    if (!userId) return;
    let cancelled = false;
    setLoading(true);
    fetch(`${getApiBaseUrl()}/api/referral/level-purchases/${userId}?level=${level.level}&page=${page}&limit=${pageSize}`)
      .then((res) => res.json())
      .then((data) => {
        if (cancelled) return;
        setTransactions(data.transactions || []);
        setTotalPages(data.total_pages || 1);
      })
      .catch((error) => console.error('Error fetching level purchases:', error))
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [userId, level.level, page, pageSize]);

  return (
    <Card className="relative overflow-hidden">
      <div className={`absolute top-0 left-0 right-0 h-2 bg-gradient-to-r ${level.color}`}></div>
      <CardHeader className="pt-6">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{level.icon}</span>
          <div>
            <CardTitle>Level {level.level} — {level.description}</CardTitle>
            <CardDescription>{level.percentage}% commission on purchases at this level</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <TransactionList
          transactions={transactions}
          loading={loading}
          emptyMessage="No purchases yet at this level"
        />
        <div className="mt-6">
          <TablePagination
            page={page}
            totalPages={totalPages}
            onPageChange={setPage}
            pageSize={pageSize}
            onPageSizeChange={(size) => { setPageSize(size); setPage(1); }}
          />
        </div>
      </CardContent>
    </Card>
  );
}
