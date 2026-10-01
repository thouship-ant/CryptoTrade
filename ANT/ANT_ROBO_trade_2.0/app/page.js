'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { InputOTP, InputOTPGroup, InputOTPSlot } from '@/components/ui/input-otp';
import { TrendingUp, BarChart3, Shield, Sun, Moon, Globe } from 'lucide-react';
import { getApiBaseUrl } from '@/lib/apiConfig';
import { useAlert } from '@/components/AlertProvider';
import { useTheme } from '@/components/ThemeProvider';
import { validateMobileNumber } from '@/lib/mobileValidation';

const OTP_RESEND_COOLDOWN_SECONDS = 60;


export default function HomePage() {
  const router = useRouter();
  const alert = useAlert();
  const { theme, toggleTheme } = useTheme();
  // 'login' | 'register' | 'otp' | 'forgot' | 'reset' - all non-login/register steps
  // are shown in place of the Tabs, not a tab itself
  const [authStep, setAuthStep] = useState('login');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    full_name: '',
    email_id: '',
    mobile_number: '',
    referal_code: ''
  });

  // Login uses a separate identifier field (not formData.username) so switching
  // to the Register tab never carries a typed "username or email" value into
  // the actual account-username field there.
  const [loginIdentifier, setLoginIdentifier] = useState('');

  const [otpUserId, setOtpUserId] = useState(null);
  const [otpValue, setOtpValue] = useState('');
  const [otpLoading, setOtpLoading] = useState(false);
  const [otpError, setOtpError] = useState('');
  // Shared between the register-verify OTP step and the password-reset OTP step -
  // only one of those flows is ever active at a time, so one cooldown clock is enough.
  const [resendCooldown, setResendCooldown] = useState(0);

  // Monthly login step-up OTP - separate from otpUserId (registration
  // verification) since it's a different backend flow (verify-login-otp) that
  // completes the login on success instead of sending the user back to it.
  // Reuses otpValue/otpLoading/otpError/resendCooldown above, same sharing
  // rationale as registration/reset.
  const [monthlyOtpUserId, setMonthlyOtpUserId] = useState(null);

  // Forgot/reset password
  const [resetIdentifier, setResetIdentifier] = useState('');
  const [resetUserId, setResetUserId] = useState(null);
  const [resetOtpValue, setResetOtpValue] = useState('');
  const [resetNewPassword, setResetNewPassword] = useState('');
  const [resetConfirmPassword, setResetConfirmPassword] = useState('');
  const [resetLoading, setResetLoading] = useState(false);
  const [resetError, setResetError] = useState('');

  const isLogin = authStep === 'login';

  useEffect(() => {
    // Check if user is already logged in
    const userId = localStorage.getItem('user_id');
    if (userId) {
      router.push('/dashboard');
      return;
    }

    // Pre-fill referral code from a shared referral link (?ref=CODE)
    const refCode = new URLSearchParams(window.location.search).get('ref');
    if (refCode) {
      setFormData((prev) => ({ ...prev, referal_code: refCode }));
      setAuthStep('register');
    }
  }, [router]);

  useEffect(() => {
    if (resendCooldown <= 0) return;
    const timer = setInterval(() => setResendCooldown((s) => Math.max(0, s - 1)), 1000);
    return () => clearInterval(timer);
  }, [resendCooldown]);

  const completeLogin = (data) => {
    localStorage.setItem('user_id', data.user_id);
    localStorage.setItem('username', data.username);
    localStorage.setItem('full_name', data.full_name);
    localStorage.setItem('role', (data.role || '').toLowerCase());
    router.push('/dashboard');
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await fetch(`${getApiBaseUrl()}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          identifier: loginIdentifier,
          password: formData.password
        })
      });

      const data = await response.json();

      if (response.ok) {
        completeLogin(data);
      } else if (response.status === 403 && data.detail && data.detail.otp_required) {
        // Account exists but hasn't completed email verification yet - send them to OTP entry
        setOtpUserId(data.detail.user_id);
        setAuthStep('otp');
        setError('');
      } else if (response.status === 403 && data.detail && data.detail.monthly_otp_required) {
        // Password was correct, but the monthly login re-confirmation is due -
        // an OTP was already emailed by the backend at this point.
        setMonthlyOtpUserId(data.detail.user_id);
        setOtpValue('');
        setResendCooldown(OTP_RESEND_COOLDOWN_SECONDS);
        setAuthStep('monthly_otp');
        setError('');
      } else {
        setError((typeof data.detail === 'string' && data.detail) || 'Login failed');
      }
    } catch (err) {
      setError('Server error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setError('');

    const mobileCheck = validateMobileNumber(formData.mobile_number);
    if (mobileCheck.error) {
      setError(mobileCheck.error);
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });

      const data = await response.json();

      if (response.ok) {
        setError('');
        setOtpUserId(data.user_id);
        setOtpValue('');
        setResendCooldown(OTP_RESEND_COOLDOWN_SECONDS);
        setAuthStep('otp');
      } else {
        setError(data.detail || 'Registration failed');
      }
    } catch (err) {
      setError('Server error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    setOtpLoading(true);
    setOtpError('');

    try {
      const response = await fetch(`${getApiBaseUrl()}/api/auth/verify-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: otpUserId, otp_code: otpValue })
      });

      const data = await response.json();

      if (response.ok) {
        setAuthStep('login');
        setOtpUserId(null);
        setOtpValue('');
        alert.success('Email verified! Please login.');
      } else {
        setOtpError(data.detail || 'Verification failed');
      }
    } catch (err) {
      setOtpError('Server error. Please try again.');
    } finally {
      setOtpLoading(false);
    }
  };

  const handleResendOtp = async () => {
    if (resendCooldown > 0) return;
    setOtpError('');

    try {
      const response = await fetch(`${getApiBaseUrl()}/api/auth/resend-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: otpUserId })
      });

      const data = await response.json();

      if (response.ok) {
        setResendCooldown(OTP_RESEND_COOLDOWN_SECONDS);
        alert.success('A new code has been sent to your email.');
      } else {
        setOtpError(data.detail || 'Could not resend code');
      }
    } catch (err) {
      setOtpError('Server error. Please try again.');
    }
  };

  const handleVerifyMonthlyOtp = async (e) => {
    e.preventDefault();
    setOtpLoading(true);
    setOtpError('');

    try {
      const response = await fetch(`${getApiBaseUrl()}/api/auth/verify-login-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: monthlyOtpUserId, otp_code: otpValue })
      });

      const data = await response.json();

      if (response.ok) {
        setMonthlyOtpUserId(null);
        setOtpValue('');
        completeLogin(data);
      } else {
        setOtpError(data.detail || 'Verification failed');
      }
    } catch (err) {
      setOtpError('Server error. Please try again.');
    } finally {
      setOtpLoading(false);
    }
  };

  const handleResendMonthlyOtp = async () => {
    if (resendCooldown > 0) return;
    setOtpError('');

    try {
      const response = await fetch(`${getApiBaseUrl()}/api/auth/resend-login-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: monthlyOtpUserId })
      });

      const data = await response.json();

      if (response.ok) {
        setResendCooldown(OTP_RESEND_COOLDOWN_SECONDS);
        alert.success('A new code has been sent to your email.');
      } else {
        setOtpError(data.detail || 'Could not resend code');
      }
    } catch (err) {
      setOtpError('Server error. Please try again.');
    }
  };

  const handleForgotPassword = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await fetch(`${getApiBaseUrl()}/api/auth/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ identifier: resetIdentifier })
      });

      const data = await response.json();

      if (response.ok) {
        setResetUserId(data.user_id);
        setResetOtpValue('');
        setResetNewPassword('');
        setResetConfirmPassword('');
        setResetError('');
        setResendCooldown(OTP_RESEND_COOLDOWN_SECONDS);
        setAuthStep('reset');
      } else {
        setError(data.detail || 'Could not send reset code');
      }
    } catch (err) {
      setError('Server error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleResendResetOtp = async () => {
    if (resendCooldown > 0) return;
    setResetError('');

    try {
      const response = await fetch(`${getApiBaseUrl()}/api/auth/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ identifier: resetIdentifier })
      });

      const data = await response.json();

      if (response.ok) {
        setResendCooldown(OTP_RESEND_COOLDOWN_SECONDS);
        alert.success('A new code has been sent to your email.');
      } else {
        setResetError(data.detail || 'Could not resend code');
      }
    } catch (err) {
      setResetError('Server error. Please try again.');
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    setResetError('');

    if (resetNewPassword.length < 6) {
      setResetError('Password must be at least 6 characters');
      return;
    }
    if (resetNewPassword !== resetConfirmPassword) {
      setResetError('Passwords do not match');
      return;
    }

    setResetLoading(true);

    try {
      const response = await fetch(`${getApiBaseUrl()}/api/auth/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: resetUserId,
          otp_code: resetOtpValue,
          new_password: resetNewPassword
        })
      });

      const data = await response.json();

      if (response.ok) {
        setAuthStep('login');
        setResetUserId(null);
        setResetIdentifier('');
        setResetOtpValue('');
        setResetNewPassword('');
        setResetConfirmPassword('');
        alert.success('Password reset! Please login with your new password.');
      } else {
        setResetError(data.detail || 'Reset failed');
      }
    } catch (err) {
      setResetError('Server error. Please try again.');
    } finally {
      setResetLoading(false);
    }
  };

  // Recomputed on every render off the raw string - cheap, no need to memoize -
  // drives both the inline error/country-name display below and handleRegister's
  // submit guard above.
  const mobileValidation = validateMobileNumber(formData.mobile_number);

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-primary/20">
      {/* Header */}
      <header className="border-b bg-background/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <div className="relative flex items-center justify-between">
            {/* Desktop logo - left-aligned, hidden on mobile in favor of the centered one below */}
            <div className="hidden sm:flex items-center gap-2">
              <h1 className="text-2xl bg-gradient-to-r from-amber-600 to-amber-600 bg-clip-text text-transparent">
                <span className="d-none">
                    <img src="/assets/images/app_name_light.png" alt="ANT Crypto Robo Trade" height={75} width={200} className="dark:hidden"/>
                    <img src="/assets/images/app_name_dark.png" alt="ANT Crypto Robo Trade" height={75} width={200} className="hidden dark:block"/>
                </span>
              </h1>
            </div>

            {/* Mobile logo - centered in the header regardless of the theme toggle's width,
                same size as the desktop logo above */}
            <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 sm:hidden">
              <img src="/assets/images/app_name_light.png" alt="ANT Crypto Robo Trade" height={75} width={200} className="dark:hidden"/>
              <img src="/assets/images/app_name_dark.png" alt="ANT Crypto Robo Trade" height={75} width={200} className="hidden dark:block"/>
            </div>

            <button
              type="button"
              onClick={toggleTheme}
              aria-label="Toggle dark mode"
              className="ml-auto shrink-0 inline-flex h-9 w-9 items-center justify-center rounded-md hover:bg-accent transition-colors"
            >
              {theme === 'dark' ? <Moon className="h-5 w-5" /> : <Sun className="h-5 w-5" />}
            </button>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="py-20">
        <div className="container mx-auto px-4">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            {/* Left Side - Features */}
            <div className="space-y-8">
              <div>
                <h2 className="text-4xl mb-4">
                  <strong>Crypto Trading on Autopilot</strong>
                </h2>
                <p className="text-lg">
                  Automated crypto trading on your own Binance account - 24/7, no withdrawal access required
                </p>
              </div>

              <div className="space-y-6">
                <div className="flex gap-4">
                  <div className="flex-shrink-0">
                    <div className="h-12 w-12 rounded-lg bg-amber-100 flex items-center justify-center">
                      <TrendingUp className="h-6 w-6 text-amber-600" />
                    </div>
                  </div>
                  <div>
                    <h3 className="mb-1"><strong>Real-time Analytics</strong></h3>
                    <p className="text-sm">
                      Track every position, coin-wise P&amp;L and daily profit with live Binance prices
                    </p>
                  </div>
                </div>

                <div className="flex gap-4">
                  <div className="flex-shrink-0">
                    <div className="h-12 w-12 rounded-lg bg-amber-100 flex items-center justify-center">
                      <BarChart3 className="h-6 w-6 text-amber-600" />
                    </div>
                  </div>
                  <div>
                    <h3 className="mb-1"><strong>Automated Trading</strong></h3>
                    <p className="text-sm">
                      Our bots open and close long/short positions on USDT pairs from technical signals, around the clock
                    </p>
                  </div>
                </div>

                <div className="flex gap-4">
                  <div className="flex-shrink-0">
                    <div className="h-12 w-12 rounded-lg bg-green-100 flex items-center justify-center">
                      <Shield className="h-6 w-6 text-green-600" />
                    </div>
                  </div>
                  <div>
                    <h3 className="mb-1"><strong>Secure Platform</strong></h3>
                    <p className="text-sm">
                      Your funds stay on Binance. We only need a trade-only API key - withdrawals are never enabled
                    </p>
                  </div>
                </div>
              </div>
              
              {/* Supported exchange */}
              <div className="pt-2">
                <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                  <span>Trades on:</span>
                  <span className="flex items-center gap-1.5 rounded-full border bg-background px-2.5 py-1">
                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-amber-400 text-[11px] font-black text-black">B</span>
                    Binance
                  </span>
                  <span className="rounded-full border bg-background px-2.5 py-1">USDT pairs</span>
                  <span className="rounded-full border bg-background px-2.5 py-1">Spot &amp; Futures</span>
                </div>
              </div>

            </div>
            {/* Right Side - Auth Forms */}
            <div>
              <Card className="shadow-xl bg-card" style={{
                backgroundImage: 'none',
                backgroundSize: '100px 100px'
              }}>
                <CardHeader className="bg-card/95">
                  <CardTitle className="text-2xl text-foreground">
                    {authStep === 'otp' ? 'Verify Your Email'
                      : authStep === 'monthly_otp' ? 'Confirm Your Login'
                      : authStep === 'forgot' ? 'Forgot Password'
                      : authStep === 'reset' ? 'Reset Password'
                      : isLogin ? 'Welcome Back' : 'Create Account'}
                  </CardTitle>
                  <CardDescription className="text-muted-foreground">
                    {authStep === 'otp'
                      ? `Enter the 6-digit code we emailed to ${formData.email_id || 'your email'}`
                      : authStep === 'monthly_otp'
                      ? 'For your security, please confirm the 6-digit code we emailed you to complete this login'
                      : authStep === 'forgot'
                      ? "Enter your username or email and we'll send you a reset code"
                      : authStep === 'reset'
                      ? 'Enter the code we emailed you and choose a new password'
                      : isLogin
                      ? 'Login to access your trading dashboard'
                      : 'Start your trading journey today'}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {authStep === 'forgot' ? (
                    <form onSubmit={handleForgotPassword} className="space-y-4">
                      <div className="space-y-2">
                        <Label htmlFor="reset_identifier">Username or Email</Label>
                        <Input
                          id="reset_identifier"
                          autoComplete="off"
                          placeholder="Enter your username or email"
                          value={resetIdentifier}
                          onChange={(e) => setResetIdentifier(e.target.value)}
                          required
                        />
                      </div>
                      {error && <p className="text-sm text-red-500">{error}</p>}
                      <Button type="submit" className="w-full btn bg-primary hover:bg-primary/90 text-white" disabled={loading}>
                        {loading ? 'Sending code...' : 'Send Reset Code'}
                      </Button>
                      <div className="text-center">
                        <button
                          type="button"
                          className="text-sm text-muted-foreground hover:underline"
                          onClick={() => { setError(''); setAuthStep('login'); }}
                        >
                          Back to login
                        </button>
                      </div>
                    </form>
                  ) : authStep === 'reset' ? (
                    <form onSubmit={handleResetPassword} className="space-y-4">
                      <div className="flex justify-center">
                        <InputOTP maxLength={6} value={resetOtpValue} onChange={setResetOtpValue}>
                          <InputOTPGroup>
                            <InputOTPSlot index={0} />
                            <InputOTPSlot index={1} />
                            <InputOTPSlot index={2} />
                            <InputOTPSlot index={3} />
                            <InputOTPSlot index={4} />
                            <InputOTPSlot index={5} />
                          </InputOTPGroup>
                        </InputOTP>
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="new_password">New Password</Label>
                        <Input
                          id="new_password"
                          type="password"
                          autoComplete="off"
                          placeholder="Enter a new password"
                          value={resetNewPassword}
                          onChange={(e) => setResetNewPassword(e.target.value)}
                          required
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="confirm_new_password">Confirm New Password</Label>
                        <Input
                          id="confirm_new_password"
                          type="password"
                          autoComplete="off"
                          placeholder="Re-enter the new password"
                          value={resetConfirmPassword}
                          onChange={(e) => setResetConfirmPassword(e.target.value)}
                          required
                        />
                      </div>
                      {resetError && <p className="text-sm text-red-500 text-center">{resetError}</p>}
                      <Button
                        type="submit"
                        className="w-full btn bg-primary hover:bg-primary/90 text-white"
                        disabled={resetLoading || resetOtpValue.length !== 6}
                      >
                        {resetLoading ? 'Resetting...' : 'Reset Password'}
                      </Button>
                      <div className="text-center text-sm text-muted-foreground">
                        Didn&apos;t get a code?{' '}
                        <button
                          type="button"
                          className="text-primary hover:underline disabled:text-muted-foreground disabled:no-underline"
                          onClick={handleResendResetOtp}
                          disabled={resendCooldown > 0}
                        >
                          {resendCooldown > 0 ? `Resend code (${resendCooldown}s)` : 'Resend code'}
                        </button>
                      </div>
                      <div className="text-center">
                        <button
                          type="button"
                          className="text-sm text-muted-foreground hover:underline"
                          onClick={() => { setResetError(''); setAuthStep('login'); }}
                        >
                          Back to login
                        </button>
                      </div>
                    </form>
                  ) : authStep === 'otp' ? (
                    <form onSubmit={handleVerifyOtp} className="space-y-4">
                      <div className="flex justify-center">
                        <InputOTP maxLength={6} value={otpValue} onChange={setOtpValue}>
                          <InputOTPGroup>
                            <InputOTPSlot index={0} />
                            <InputOTPSlot index={1} />
                            <InputOTPSlot index={2} />
                            <InputOTPSlot index={3} />
                            <InputOTPSlot index={4} />
                            <InputOTPSlot index={5} />
                          </InputOTPGroup>
                        </InputOTP>
                      </div>
                      {otpError && <p className="text-sm text-red-500 text-center">{otpError}</p>}
                      <Button
                        type="submit"
                        className="w-full btn bg-primary hover:bg-primary/90 text-white"
                        disabled={otpLoading || otpValue.length !== 6}
                      >
                        {otpLoading ? 'Verifying...' : 'Verify'}
                      </Button>
                      <div className="text-center text-sm text-muted-foreground">
                        Didn&apos;t get a code?{' '}
                        <button
                          type="button"
                          className="text-primary hover:underline disabled:text-muted-foreground disabled:no-underline"
                          onClick={handleResendOtp}
                          disabled={resendCooldown > 0}
                        >
                          {resendCooldown > 0 ? `Resend code (${resendCooldown}s)` : 'Resend code'}
                        </button>
                      </div>
                      <div className="text-center">
                        <button
                          type="button"
                          className="text-sm text-muted-foreground hover:underline"
                          onClick={() => setAuthStep('login')}
                        >
                          Back to login
                        </button>
                      </div>
                    </form>
                  ) : authStep === 'monthly_otp' ? (
                    <form onSubmit={handleVerifyMonthlyOtp} className="space-y-4">
                      <div className="flex justify-center">
                        <InputOTP maxLength={6} value={otpValue} onChange={setOtpValue}>
                          <InputOTPGroup>
                            <InputOTPSlot index={0} />
                            <InputOTPSlot index={1} />
                            <InputOTPSlot index={2} />
                            <InputOTPSlot index={3} />
                            <InputOTPSlot index={4} />
                            <InputOTPSlot index={5} />
                          </InputOTPGroup>
                        </InputOTP>
                      </div>
                      {otpError && <p className="text-sm text-red-500 text-center">{otpError}</p>}
                      <Button
                        type="submit"
                        className="w-full btn bg-primary hover:bg-primary/90 text-white"
                        disabled={otpLoading || otpValue.length !== 6}
                      >
                        {otpLoading ? 'Verifying...' : 'Verify & Continue'}
                      </Button>
                      <div className="text-center text-sm text-muted-foreground">
                        Didn&apos;t get a code?{' '}
                        <button
                          type="button"
                          className="text-primary hover:underline disabled:text-muted-foreground disabled:no-underline"
                          onClick={handleResendMonthlyOtp}
                          disabled={resendCooldown > 0}
                        >
                          {resendCooldown > 0 ? `Resend code (${resendCooldown}s)` : 'Resend code'}
                        </button>
                      </div>
                      <div className="text-center">
                        <button
                          type="button"
                          className="text-sm text-muted-foreground hover:underline"
                          onClick={() => { setMonthlyOtpUserId(null); setOtpValue(''); setOtpError(''); setAuthStep('login'); }}
                        >
                          Back to login
                        </button>
                      </div>
                    </form>
                  ) : (
                  <Tabs value={authStep} className="w-full">
                    <TabsList className="grid w-full grid-cols-2">
                      <TabsTrigger value="login" className="btn hover:bg-grey-600" onClick={() => setAuthStep('login')}>
                        Login
                      </TabsTrigger>
                      <TabsTrigger value="register" className="btn hover:bg-grey-600" onClick={() => setAuthStep('register')}>
                        Register
                      </TabsTrigger>
                    </TabsList>

                    <TabsContent value="login">
                      <form onSubmit={handleLogin} className="space-y-4">
                        <div className="space-y-2">
                          <Label htmlFor="username">Username or Email</Label>
                          <Input
                            id="username"
                            placeholder="Enter your username or email"
                            value={loginIdentifier}
                            onChange={(e) => setLoginIdentifier(e.target.value)}
                            required
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="password">Password</Label>
                          <Input
                            id="password"
                            type="password"
                            placeholder="Enter your password"
                            value={formData.password}
                            onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                            required
                          />
                        </div>
                        <div className="text-right">
                          <button
                            type="button"
                            className="text-sm text-amber-600 hover:underline"
                            onClick={() => {
                              setError('');
                              setResetIdentifier(loginIdentifier || '');
                              setAuthStep('forgot');
                            }}
                          >
                            Forgot password?
                          </button>
                        </div>
                        {error && <p className="text-sm text-red-500">{error}</p>}
                        <Button type="submit" className="w-full btn bg-primary hover:bg-primary/90 text-white" disabled={loading}>
                          {loading ? 'Logging in...' : 'Login'}
                        </Button>
                      </form>
                    </TabsContent>

                    <TabsContent value="register">
                      <form onSubmit={handleRegister} className="space-y-4">
                        <div className="space-y-2">
                          <Label htmlFor="full_name">Full Name</Label>
                          <Input
                            id="full_name"
                            autoComplete="off"
                            placeholder="Enter your full name"
                            value={formData.full_name}
                            onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                            required
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="email">Email</Label>
                          <Input
                            id="email"
                            type="email"
                            autoComplete="off"
                            placeholder="Enter your email"
                            value={formData.email_id}
                            onChange={(e) => setFormData({ ...formData, email_id: e.target.value })}
                            required
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="mobile">Mobile Number</Label>
                          <Input
                            id="mobile"
                            autoComplete="off"
                            placeholder="Enter your mobile number"
                            value={formData.mobile_number}
                            onChange={(e) => setFormData({ ...formData, mobile_number: e.target.value })}
                            required
                          />
                          {/* No space allowed, at least 10 digits, and anything beyond the
                              last 10 digits is read as a country code (with or without a
                              leading + or 00) - see lib/mobileValidation.js. */}
                          {mobileValidation.error && formData.mobile_number && (
                            <p className="text-xs text-red-500">{mobileValidation.error}</p>
                          )}
                          {!mobileValidation.error && mobileValidation.countryCode && (
                            <p className="text-xs text-muted-foreground flex items-center gap-1">
                              <Globe className="h-3 w-3" />
                              {mobileValidation.countryName
                                ? `Country: ${mobileValidation.countryName} (+${mobileValidation.countryCode})`
                                : `Country code +${mobileValidation.countryCode} not recognized`}
                            </p>
                          )}
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="reg_username">Username</Label>
                          <Input
                            id="reg_username"
                            autoComplete="off"
                            placeholder="Choose a username"
                            value={formData.username}
                            onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                            required
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="reg_password">Password</Label>
                          <Input
                            id="reg_password"
                            type="password"
                            autoComplete="off"
                            placeholder="Choose a password"
                            value={formData.password}
                            onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                            required
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="referal_code">Referral Code (optional)</Label>
                          <Input
                            id="referal_code"
                            autoComplete="off"
                            placeholder="Enter a referral code, if you have one"
                            value={formData.referal_code}
                            onChange={(e) => setFormData({ ...formData, referal_code: e.target.value })}
                          />
                        </div>
                        {error && <p className="text-sm text-red-500">{error}</p>}
                        <Button
                          type="submit"
                          className="w-full btn bg-primary hover:bg-primary/90 text-white"
                          disabled={loading || !!mobileValidation.error}
                        >
                          {loading ? 'Creating Account...' : 'Create Account'}
                        </Button>
                      </form>
                    </TabsContent>
                  </Tabs>
                  )}
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </section>

      <footer className="flex flex-wrap items-center justify-center gap-x-3 gap-y-1 py-6 text-sm text-muted-foreground">
        <Link href="/contact-us" className="hover:text-foreground">Contact Us</Link>
        <span aria-hidden="true">·</span>
        <Link href="/terms" className="hover:text-foreground">Terms &amp; Conditions</Link>
        <span aria-hidden="true">·</span>
        <Link href="/privacy" className="hover:text-foreground">Privacy Policy</Link>
        <span aria-hidden="true">·</span>
        <Link href="/refunds" className="hover:text-foreground">Refunds &amp; Cancellations</Link>
      </footer>
    </div>
  );
}
