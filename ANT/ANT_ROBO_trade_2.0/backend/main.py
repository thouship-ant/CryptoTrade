from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta, date
import pymysql
import uuid
import bcrypt
import re
import os
import time
import smtplib
import secrets
import asyncio
import html
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import ccxt
from cryptography.fernet import Fernet, InvalidToken

load_dotenv()

app = FastAPI(title="ANT Robo Trade - Crypto API")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')

# Sentinel stored in ant_user_data.referal_by for accounts with no real referrer
# (NOT NULL column, so "no referrer" needs a value). Never matches a real user_id.
ROOT_REFERRER = 'root'

# On-chain withdrawals are settled manually by an admin. A flat network fee in USDT is
# held back from the amount the user asks for; minimum keeps dust requests out.
MIN_WITHDRAWAL_USDT = float(os.getenv('MIN_WITHDRAWAL_USDT', '10'))
WITHDRAWAL_FEE_USDT = float(os.getenv('WITHDRAWAL_FEE_USDT', '1'))
MIN_DEPOSIT_USDT = float(os.getenv('MIN_DEPOSIT_USDT', '10'))

# Referral commission paid up the referral chain on a bot purchase: direct referrer
# 15%, their referrer 10%, and the next 5% (carried over from the 1.0 crypto app).
LEVEL_COMMISSION_PERCENTS = [0.15, 0.10, 0.05]

# Minimum energy_power required to keep trading - the trading engine (BNB_ABT) keeps
# its own copy of this threshold; the two processes share no code by design.
MIN_TRADING_POWER = 500

MAX_QR_IMAGE_LENGTH = 2_000_000  # base64 chars - generous for a QR PNG/JPEG

# SMTP (email) configuration - real values (including credentials) belong in backend/.env
# (gitignored, see .env.example), loaded above via load_dotenv(). Never hardcode real
# credentials here - this file is committed to git.
SMTP_HOST = os.getenv('SMTP_HOST', '')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER = os.getenv('SMTP_USER', '')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
SMTP_FROM = os.getenv('SMTP_FROM', SMTP_USER)

def send_email(to_email: str, subject: str, body: str, html_body: Optional[str] = None) -> bool:
    """Send an email via SMTP - plain text only if html_body is omitted (unchanged
    behavior for any caller that hasn't been updated to the branded template yet),
    or multipart/alternative (plain text + html_body) when it is, so clients that
    can't/won't render HTML still get a readable fallback. Returns False (and logs)
    instead of raising, since a failed notification shouldn't take down the request
    that triggered it."""
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASSWORD:
        print(f"SMTP not configured - skipping email to {to_email}: {subject}")
        return False
    try:
        if html_body:
            msg = MIMEMultipart('alternative')
            # Per RFC 2046, alternative parts go from least to most preferred -
            # the client renders the LAST part it understands, so plain text
            # first, HTML last.
            msg.attach(MIMEText(body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))
        else:
            msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = SMTP_FROM
        msg['To'] = to_email
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, [to_email], msg.as_string())
        return True
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")
        return False

# Shared branding for every HTML email this app sends - keep these in sync with
# app/globals.css / the login page if the app's own palette ever changes.
EMAIL_BRAND_NAME = "ANT Crypto Trade"
EMAIL_BRAND_TAGLINE = "Automated Crypto Trading"
EMAIL_ACCENT_COLOR = "#D4A017"   # gold - used for the wordmark accent and CTA button
EMAIL_DARK_COLOR = "#0b0b0c"     # header black

def render_email_html(heading: str, body_html: str, preheader: str = "", cta_label: Optional[str] = None, cta_url: Optional[str] = None) -> str:
    """Wraps body_html (caller-controlled, trusted markup - escape any raw user
    input before passing it in) in the branded, table-based email shell every HTML
    email in this app uses. Table layout + inline styles throughout, not a <style>
    block or flexbox/grid - this is the "bulletproof email" approach, since Outlook
    (Word's rendering engine) and a good chunk of webmail clients ignore or strip
    both. preheader is the short summary text shown next to the subject line in an
    inbox list (Gmail/Apple Mail) - hidden in the body itself via display:none.
    cta_label/cta_url render an optional single button (e.g. "Open Dashboard")."""
    cta_html = ""
    if cta_label and cta_url:
        cta_html = f"""
          <tr>
            <td align="center" style="padding:8px 40px 32px 40px;">
              <a href="{cta_url}" target="_blank" rel="noopener noreferrer"
                 style="display:inline-block; background-color:{EMAIL_ACCENT_COLOR}; color:#1a1300; text-decoration:none;
                        font-weight:600; font-size:15px; padding:12px 32px; border-radius:6px; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
                {cta_label}
              </a>
            </td>
          </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="color-scheme" content="light">
<title>{heading}</title>
</head>
<body style="margin:0; padding:0; background-color:#f1f5f9; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
  <div style="display:none; max-height:0; overflow:hidden; mso-hide:all; opacity:0;">{preheader}</div>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f1f5f9;">
    <tr>
      <td align="center" style="padding:32px 16px;">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0"
               style="max-width:600px; width:100%; background-color:#ffffff; border-radius:8px; border:1px solid #e2e8f0;">
          <tr>
            <td style="background-color:{EMAIL_DARK_COLOR}; padding:28px 40px; border-radius:8px 8px 0 0;" align="center">
              <span style="color:#ffffff; font-size:20px; font-weight:700; letter-spacing:0.5px;">
                <span style="color:{EMAIL_ACCENT_COLOR};">&#9650;</span> {EMAIL_BRAND_NAME.upper()}
              </span>
              <div style="color:#94a3b8; font-size:12px; margin-top:4px; letter-spacing:0.5px; text-transform:uppercase;">
                {EMAIL_BRAND_TAGLINE}
              </div>
            </td>
          </tr>
          <tr>
            <td style="padding:40px 40px 24px 40px;">
              <h1 style="margin:0 0 16px 0; font-size:20px; line-height:1.3; color:#0f172a; font-weight:700;">{heading}</h1>
              <div style="font-size:15px; line-height:1.6; color:#334155;">
                {body_html}
              </div>
            </td>
          </tr>{cta_html}
          <tr>
            <td style="background-color:#f8fafc; border-top:1px solid #e2e8f0; padding:24px 40px; text-align:center; border-radius:0 0 8px 8px;">
              <p style="margin:0 0 8px 0; font-size:12px; color:#94a3b8;">
                This is an automated message from {EMAIL_BRAND_NAME} - please don't reply to this email.
              </p>
              <p style="margin:0; font-size:11px; color:#cbd5e1; line-height:1.5;">
                Crypto trading involves substantial risk, including the possible loss of your entire capital. Past performance is not indicative of future results.<br>
                &copy; {datetime.now().year} {EMAIL_BRAND_NAME}. All rights reserved.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

def build_otp_email_body(full_name: str, username: str, otp_code: str, purpose_phrase: str, expiry_minutes: int = 10) -> str:
    """GitHub-style OTP email body (matches the reference "Please verify your
    identity" / sudo-authentication-code layout) - shared by every OTP-sending
    call site (registration, resend, forgot-password, monthly login) so the
    wording/structure stays identical across all of them. purpose_phrase slots
    into "Here is your ANT Crypto Trade {purpose_phrase} code" - e.g. "account
    verification", "password reset", "login verification". Plain-text fallback for
    build_otp_email_html - see send_email's multipart/alternative handling."""
    display_name = f"{full_name} ({username})" if full_name else username
    return (
        f"Please verify your identity, {display_name}\n\n"
        f"Here is your ANT Crypto Trade {purpose_phrase} code:\n\n"
        f"{otp_code}\n\n"
        f"This code is valid for {expiry_minutes} minutes and can only be used once.\n\n"
        "Please don't share this code with anyone: we'll never ask for it on the phone or via email.\n\n"
        "Thanks,\n"
        "The ANT Crypto Trade Team\n\n"
        "You're receiving this email because a verification code was requested for your ANT Crypto Trade "
        "account. If this wasn't you, please ignore this email."
    )

def build_otp_email_html(full_name: str, username: str, otp_code: str, purpose_phrase: str, expiry_minutes: int = 10) -> str:
    """HTML counterpart to build_otp_email_body, rendered through the shared brand
    shell (render_email_html) - the code itself is shown as a large, letter-spaced,
    monospace badge, which is the standard treatment for a one-time code (matches
    GitHub/Google/Stripe's own OTP emails) so it's unmistakable at a glance."""
    display_name = html.escape(f"{full_name} ({username})" if full_name else username)
    body_html = f"""
      <p style="margin:0 0 16px 0;">Please verify your identity, <strong>{display_name}</strong>.</p>
      <p style="margin:0 0 20px 0;">Here is your {EMAIL_BRAND_NAME} {html.escape(purpose_phrase)} code:</p>
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td align="center" style="padding:0 0 24px 0;">
            <span style="display:inline-block; background-color:#fffbeb; border:1px solid #fde68a; color:#92400e;
                         font-size:28px; font-weight:700; letter-spacing:8px; padding:16px 28px; border-radius:8px;
                         font-family:'Courier New',Courier,monospace;">
              {otp_code}
            </span>
          </td>
        </tr>
      </table>
      <p style="margin:0 0 12px 0; font-size:13px; color:#64748b;">This code is valid for {expiry_minutes} minutes and can only be used once.</p>
      <p style="margin:0 0 20px 0; font-size:13px; color:#64748b;">Please don&rsquo;t share this code with anyone - we&rsquo;ll never ask for it over the phone or via email.</p>
      <p style="margin:0;">Thanks,<br>The {EMAIL_BRAND_NAME} Team</p>
    """
    preheader = f"Your {purpose_phrase} code is {otp_code} - valid for {expiry_minutes} minutes."
    return render_email_html(heading="Verify your identity", body_html=body_html, preheader=preheader)

def build_generic_email_html(subject: str, plain_body: str) -> str:
    """Wraps a free-form plain-text message (an admin's Users-tab email, a
    broker-change-approval notice, anything read out of scheduled_emails.body) in
    the branded shell - every double-newline becomes a new paragraph, single
    newlines become <br>. plain_body is untrusted (admin-typed, not markup this
    codebase authored), so it's html.escape()'d before going anywhere near the
    HTML - this must stay a plain-text-in, escaped-out helper, never take raw HTML."""
    paragraphs = [p for p in plain_body.split('\n\n') if p.strip()]
    if paragraphs:
        body_html = "".join(
            f'<p style="margin:0 0 16px 0;">{html.escape(p).replace(chr(10), "<br>")}</p>'
            for p in paragraphs
        )
    else:
        body_html = f'<p style="margin:0;">{html.escape(plain_body)}</p>'
    preheader = plain_body.strip().replace('\n', ' ')[:120]
    return render_email_html(heading=subject, body_html=body_html, preheader=preheader)


# Database connection
# Real connection details belong in backend/.env (gitignored, see .env.example), loaded
# above via load_dotenv(). Never hardcode real credentials here.
def get_db_connection():
    return pymysql.connect(
        host=os.getenv('DB_HOST', ''),
        port=int(os.getenv('DB_PORT', '3306')),
        user=os.getenv('DB_USER', ''),
        password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME', 'ant_cryptotradingbot_v2'),
        cursorclass=pymysql.cursors.DictCursor
    )

# Pydantic models
class UserCreate(BaseModel):
    full_name: str
    username: str
    password: str
    mobile_number: str
    email_id: str
    referal_code: Optional[str] = None

class UserLogin(BaseModel):
    identifier: str  # username or email
    password: str

class OtpVerify(BaseModel):
    user_id: str
    otp_code: str

class OtpResend(BaseModel):
    user_id: str

class ForgotPasswordRequest(BaseModel):
    identifier: str  # username or email

class ResetPasswordConfirm(BaseModel):
    user_id: str
    otp_code: str
    new_password: str

class ConfigUpdate(BaseModel):
    # Exchange credentials. api_secret is write-only: GET /api/config never returns it.
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    usdt_address: Optional[str] = None
    mobile_number: Optional[str] = None
    single_trade_amount: Optional[float] = None
    total_investment_amount: Optional[float] = None
    max_trade: Optional[int] = None
    leverage: Optional[int] = None
    stoploss_percent: Optional[float] = None
    target_percent: Optional[float] = None
    trade_long: Optional[bool] = None
    trade_short: Optional[bool] = None

class TradingStatusUpdate(BaseModel):
    is_trading_active: bool

class DepositRequestCreate(BaseModel):
    amount: float
    tx_hash: str

class WithdrawalRequestCreate(BaseModel):
    amount: float
    usdt_address: str

class WalletTransferCreate(BaseModel):
    amount: float

class DepositSettingsUpdate(BaseModel):
    admin_user_id: str
    usdt_address: Optional[str] = None
    network: Optional[str] = None
    qr_image: Optional[str] = None  # base64 image data URI
    note: Optional[str] = None
    is_enabled: Optional[bool] = None

class DepositRequestAction(BaseModel):
    admin_user_id: str
    action: str  # 'approve' | 'reject'
    admin_note: Optional[str] = None

class WithdrawalRequestAction(BaseModel):
    admin_user_id: str
    action: str  # 'complete' | 'reject'
    admin_note: Optional[str] = None
    tx_hash: Optional[str] = None

class BotPurchase(BaseModel):
    bot_name: str

class PowerActivation(BaseModel):
    power_name: str

class AdminEmailRequest(BaseModel):
    admin_user_id: str
    target_user_id: str
    subject: str
    body: str
    send_at: Optional[datetime] = None

# Helper functions
def safe_error_detail(e: Exception) -> str:
    """Maps low-level DB errors (pymysql.err.Error and subclasses) to a generic message
    safe to show in the UI - raw connection failures otherwise leak internal details
    like the DB host's IP address straight into API error responses. Every other
    exception still surfaces its real message, since those (validation errors, etc.)
    are meant to be shown as-is."""
    if isinstance(e, pymysql.err.Error):
        print(f"DB error suppressed from API response: {e}")
        return "Database server issue. Please try again later."
    return str(e)

def add_one_year(dt):
    """dt + 1 calendar year, used for bot-plan (yearly billing) expiry dates.
    Falls back to Feb 28 for a Feb 29 purchase landing on a non-leap year."""
    try:
        return dt.replace(year=dt.year + 1)
    except ValueError:
        return dt.replace(year=dt.year + 1, day=28)

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

# --- Exchange-secret encryption at rest -------------------------------------------------
# Binance API secrets are encrypted with Fernet before they touch the database, so a leaked
# DB dump alone cannot be used to trade on a user's account. API_ENCRYPTION_KEY must be set
# (generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())").
# The trading engine (BNB_ABT) needs the same key to decrypt: Fernet(key).decrypt(value[4:].encode()).
# Stored values carry an "enc:" prefix; an unprefixed value is a legacy plaintext secret and is
# still readable (and gets re-encrypted the next time the user saves their keys).
ENC_PREFIX = 'enc:'
ALLOW_PLAINTEXT_SECRETS = os.getenv('ALLOW_PLAINTEXT_SECRETS', '') == '1'  # local development only

def _fernet():
    key = os.getenv('API_ENCRYPTION_KEY', '').strip()
    if not key:
        return None
    try:
        return Fernet(key.encode())
    except ValueError:
        raise HTTPException(status_code=500, detail="API_ENCRYPTION_KEY is not a valid Fernet key")

def encrypt_secret(plain: str) -> str:
    f = _fernet()
    if f is None:
        if ALLOW_PLAINTEXT_SECRETS:
            return plain
        raise HTTPException(status_code=500, detail="Server is not configured to store API secrets securely (API_ENCRYPTION_KEY missing)")
    return ENC_PREFIX + f.encrypt(plain.encode()).decode()

def decrypt_secret(stored: str) -> str:
    if not stored or not stored.startswith(ENC_PREFIX):
        return stored  # legacy plaintext
    f = _fernet()
    if f is None:
        raise HTTPException(status_code=500, detail="API_ENCRYPTION_KEY missing - cannot read stored API secret")
    try:
        return f.decrypt(stored[len(ENC_PREFIX):].encode()).decode()
    except InvalidToken:
        raise HTTPException(status_code=500, detail="Stored API secret cannot be decrypted with the configured key")

def get_user_role(user_id: str, cursor) -> str:
    """Fetch user role from database"""
    cursor.execute("SELECT role FROM ant_user_data WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()
    return user['role'] if user else 'user'

# Shared period filter (today/yesterday/current_week/last_week/current_month/last_month/
# current_year), matching the Select options in the Reports / Orders UI. from_date/
# to_date (YYYY-MM-DD) are only consulted for period == "custom".
def resolve_period_range(period: str, from_date: str = None, to_date: str = None):
    if period == "custom" and from_date and to_date:
        try:
            return (
                datetime.strptime(from_date, "%Y-%m-%d").date(),
                datetime.strptime(to_date, "%Y-%m-%d").date()
            )
        except ValueError:
            pass  # malformed dates - fall through to the default range below
    today = date.today()
    if period == "today":
        return today, today
    if period == "yesterday":
        start_date = today - timedelta(days=1)
        return start_date, start_date
    if period == "current_week":
        return today - timedelta(days=today.weekday()), today
    if period == "last_week":
        start_date = today - timedelta(days=today.weekday() + 7)
        return start_date, start_date + timedelta(days=6)
    if period == "current_month":
        return today.replace(day=1), today
    if period == "last_month":
        first_day_this_month = today.replace(day=1)
        end_date = first_day_this_month - timedelta(days=1)
        return end_date.replace(day=1), end_date
    if period == "current_year":
        return today.replace(month=1, day=1), today
    return today - timedelta(days=30), today

def require_admin(admin_user_id: str, cursor, conn) -> None:
    """Raise 403 (closing the given connection first) unless admin_user_id has the admin role."""
    admin_role = get_user_role(admin_user_id, cursor)
    if not admin_role or admin_role.lower() != 'admin':
        cursor.close()
        conn.close()
        raise HTTPException(status_code=403, detail="Admin access required")

def log_wallet_txn(cursor, user_id, txn_type, amount, status, method, description, transaction_id, source_user_id=None):
    cursor.execute("""
        INSERT INTO wallet_transactions
        (user_id, transaction_type, amount, status, payment_method, description, transaction_id, source_user_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (user_id, txn_type, amount, status, method, description, transaction_id, source_user_id))

# --- P&L SQL fragments -----------------------------------------------------------
# One row per position in crypto_signal_data. direction is +1 for LONG, -1 for SHORT;
# realized P&L is net of the commission recorded on the row.
DIR_EXPR = "(CASE WHEN s.side = 'SHORT' THEN -1 ELSE 1 END)"
REALIZED_PNL_EXPR = f"((s.exit_price - s.entry_price) * s.quantity * {DIR_EXPR} - COALESCE(s.commission, 0))"
UNREALIZED_PNL_EXPR = f"((COALESCE(s.current_price, s.entry_price) - s.entry_price) * s.quantity * {DIR_EXPR})"
# Margin tied up by a position (notional / leverage)
MARGIN_EXPR = "(s.entry_price * s.quantity / GREATEST(s.leverage, 1))"


# Schema bootstrap - runs every CREATE TABLE IF NOT EXISTS / INSERT IGNORE in
# database/schema.sql at startup, so a fresh empty database comes up ready. Only ever
# additive - never drops or alters existing data.
SCHEMA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'database', 'schema.sql')

def _load_schema_statements():
    with open(SCHEMA_FILE, 'r', encoding='utf-8') as f:
        text = f.read()
    text = re.sub(r'--[^\n]*', '', text)  # strip comments (none of the schema's string literals contain "--")
    statements = []
    for raw in text.split(';'):
        stmt = raw.strip()
        if not stmt:
            continue
        upper = stmt.upper()
        if upper.startswith('CREATE DATABASE') or upper.startswith('USE '):
            continue  # the connection already targets DB_NAME
        statements.append(stmt)
    return statements

def ensure_schema():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        for statement in _load_schema_statements():
            try:
                cursor.execute(statement)
                conn.commit()
            except Exception as e:
                print(f"ensure_schema statement failed (continuing): {e}")
    finally:
        cursor.close()
        conn.close()

# --- Daily P&L backfill ---
#
# The trading engine writes a daily_profit_report row at the end of each UTC day. Any
# downtime across that window would permanently lose the day's row and understate Total
# P&L, so this loop (crypto trades every day - there is no market calendar) catches up
# any recent day that has closed trades but no row.
DAILY_PNL_BACKFILL_LOOKBACK_DAYS = 14
DAILY_PNL_BACKFILL_INTERVAL_SECONDS = 3600

def _backfill_one_day(cursor, conn, user_id: str, report_date: date):
    date_str = report_date.isoformat()
    cursor.execute(f"""
        SELECT auw.current_investment, SUM({REALIZED_PNL_EXPR}) AS pnl
        FROM crypto_signal_data s
        INNER JOIN ant_user_wallet auw ON auw.user_id = s.user_id
        WHERE s.exit_price IS NOT NULL AND s.user_id = %s
          AND DATE(s.last_update_DateTime) = %s
        GROUP BY auw.current_investment
    """, (user_id, date_str))
    row = cursor.fetchone()
    if not row or row['current_investment'] is None or row['pnl'] is None:
        return  # nothing closed that day
    current_investment = float(row['current_investment'])
    pnl = float(row['pnl'])
    if current_investment <= 0:
        return  # avoids a divide-by-zero on profit_percent
    end_amount = current_investment + pnl
    cursor.execute("""
        INSERT INTO daily_profit_report (date, user_id, start_amount, end_amount, profit_amount, profit_percent, update_date, commission_price)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 0)
    """, (date_str, user_id, current_investment, end_amount, pnl, (pnl / current_investment) * 100, datetime.now()))
    cursor.execute("UPDATE ant_user_wallet SET current_investment = %s WHERE user_id = %s", (end_amount, user_id))
    cursor.execute("UPDATE ant_user_data SET total_profit_amount = COALESCE(total_profit_amount, 0) + %s WHERE user_id = %s", (pnl, user_id))
    conn.commit()
    print(f"Backfilled daily_profit_report for {user_id} on {date_str}: PnL={pnl}")

def _run_daily_pnl_backfill():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT user_id FROM ant_user_data WHERE is_Active = 1")
        users = cursor.fetchall()
        days = [date.today() - timedelta(days=i) for i in range(DAILY_PNL_BACKFILL_LOOKBACK_DAYS, 0, -1)]  # oldest first, never today
        for user in users:
            for d in days:  # oldest first - each day's wallet read must see the prior day's write
                cursor.execute("SELECT 1 FROM daily_profit_report WHERE user_id = %s AND date = %s", (user['user_id'], d))
                if cursor.fetchone():
                    continue
                _backfill_one_day(cursor, conn, user['user_id'], d)
    finally:
        cursor.close()
        conn.close()

async def daily_pnl_backfill_loop():
    while True:
        try:
            await asyncio.to_thread(_run_daily_pnl_backfill)
        except Exception as e:
            print(f"daily_pnl_backfill_loop error: {e}")
        await asyncio.sleep(DAILY_PNL_BACKFILL_INTERVAL_SECONDS)

def _send_due_emails():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, to_email, subject, body FROM scheduled_emails
            WHERE status = 'pending' AND send_at IS NOT NULL AND send_at <= NOW()
        """)
        for row in cursor.fetchall():
            sent = send_email(
                row['to_email'], row['subject'], row['body'],
                html_body=build_generic_email_html(row['subject'], row['body'])
            )
            cursor.execute(
                "UPDATE scheduled_emails SET status = %s, sent_at = %s WHERE id = %s",
                ('sent' if sent else 'failed', datetime.now(), row['id'])
            )
        conn.commit()
    finally:
        cursor.close()
        conn.close()

# Poll scheduled_emails for due rows and send them.
async def email_poller_loop():
    while True:
        try:
            await asyncio.to_thread(_send_due_emails)
        except Exception as e:
            print(f"email_poller_loop error: {e}")
        await asyncio.sleep(60)

@app.on_event("startup")
def on_startup():
    ensure_schema()
    asyncio.create_task(email_poller_loop())
    asyncio.create_task(daily_pnl_backfill_loop())

# Routes
@app.get("/")
def read_root():
    return {"message": "ANT Robo Trade - Crypto API", "status": "running"}

# Authentication
@app.post("/api/auth/register")
def register(user: UserCreate):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT * FROM ant_user_data WHERE username = %s OR email_id = %s", 
                      (user.username, user.email_id))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="User already exists")
        
        user_id = str(uuid.uuid4())
        hashed_pwd = hash_password(user.password)
        referal_code = f"REF{uuid.uuid4().hex[:8].upper()}"

        # Resolve the referral code (if any) to the referrer's user_id.
        # ant_user_data.referal_by is NOT NULL - it's an
        # explicit column in the INSERT below, that default won't kick in on its own.
        referal_by = ROOT_REFERRER
        if user.referal_code:
            cursor.execute("SELECT user_id FROM ant_user_data WHERE referal_code = %s", (user.referal_code.strip(),))
            referrer = cursor.fetchone()
            if referrer:
                referal_by = referrer['user_id']

        cursor.execute("""
            INSERT INTO ant_user_data
            (user_id, full_name, username, password, mobile_number, email_id, referal_code, referal_by, created_date, is_verified)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 0)
        """, (user_id, user.full_name, user.username, hashed_pwd,
               user.mobile_number, user.email_id, referal_code, referal_by, datetime.now()))
        
        # Create wallet for user
        cursor.execute("""
            INSERT INTO ant_user_wallet (user_id) VALUES (%s)
        """, (user_id,))

        # Issue an email OTP - account stays unverified (and login-blocked) until confirmed
        otp_code = f"{secrets.randbelow(1000000):06d}"
        expires_at = datetime.now() + timedelta(minutes=10)
        cursor.execute("""
            INSERT INTO email_otp_verifications (user_id, otp_code, expires_at, purpose)
            VALUES (%s, %s, %s, 'verify_email')
        """, (user_id, otp_code, expires_at))

        conn.commit()
        cursor.close()
        conn.close()

        send_email(
            user.email_id,
            "Verify your ANT Crypto Trade account",
            build_otp_email_body(user.full_name, user.username, otp_code, "account verification"),
            html_body=build_otp_email_html(user.full_name, user.username, otp_code, "account verification")
        )

        return {"message": "User registered successfully", "user_id": user_id, "otp_required": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))

@app.post("/api/auth/verify-otp")
def verify_otp(payload: OtpVerify):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM email_otp_verifications
            WHERE user_id = %s AND is_used = 0 AND purpose = 'verify_email'
            ORDER BY created_at DESC LIMIT 1
        """, (payload.user_id,))
        otp_row = cursor.fetchone()

        if not otp_row:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=400, detail="No pending verification found. Please request a new code.")

        if otp_row['expires_at'] < datetime.now():
            cursor.close()
            conn.close()
            raise HTTPException(status_code=400, detail="This code has expired. Please request a new one.")

        if otp_row['attempts'] >= 5:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=429, detail="Too many attempts. Please request a new code.")

        if otp_row['otp_code'] != payload.otp_code.strip():
            cursor.execute(
                "UPDATE email_otp_verifications SET attempts = attempts + 1 WHERE id = %s",
                (otp_row['id'],)
            )
            conn.commit()
            cursor.close()
            conn.close()
            raise HTTPException(status_code=400, detail="Incorrect code")

        cursor.execute("UPDATE email_otp_verifications SET is_used = 1 WHERE id = %s", (otp_row['id'],))
        cursor.execute("UPDATE ant_user_data SET is_verified = 1 WHERE user_id = %s", (payload.user_id,))
        conn.commit()
        cursor.close()
        conn.close()

        return {"message": "Email verified successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))

@app.post("/api/auth/resend-otp")
def resend_otp(payload: OtpResend):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT email_id, username, full_name FROM ant_user_data WHERE user_id = %s", (payload.user_id,))
        user = cursor.fetchone()
        if not user:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail="User not found")

        cursor.execute("""
            SELECT created_at FROM email_otp_verifications
            WHERE user_id = %s AND purpose = 'verify_email' ORDER BY created_at DESC LIMIT 1
        """, (payload.user_id,))
        last = cursor.fetchone()
        if last and (datetime.now() - last['created_at']) < timedelta(seconds=60):
            cursor.close()
            conn.close()
            raise HTTPException(status_code=429, detail="Please wait a moment before requesting another code")

        otp_code = f"{secrets.randbelow(1000000):06d}"
        expires_at = datetime.now() + timedelta(minutes=10)
        cursor.execute("""
            INSERT INTO email_otp_verifications (user_id, otp_code, expires_at, purpose)
            VALUES (%s, %s, %s, 'verify_email')
        """, (payload.user_id, otp_code, expires_at))
        conn.commit()
        cursor.close()
        conn.close()

        send_email(
            user['email_id'],
            "Your new ANT Crypto Trade verification code",
            build_otp_email_body(user['full_name'], user['username'], otp_code, "account verification"),
            html_body=build_otp_email_html(user['full_name'], user['username'], otp_code, "account verification")
        )

        return {"message": "A new code has been sent"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))

@app.post("/api/auth/forgot-password")
def forgot_password(payload: ForgotPasswordRequest):
    """Sends a 6-digit OTP to the account's registered email to authorize a password
    reset. Looked up by username or email, matching the login form's username field
    while still letting someone reset with just their email. Shares
    email_otp_verifications with registration OTPs (see purpose column) and the same
    60s resend cooldown / 10-minute expiry / 5-attempt lockout as verify-otp."""
    try:
        identifier = payload.identifier.strip()
        if not identifier:
            raise HTTPException(status_code=400, detail="Please enter your username or email")

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT user_id, email_id, username, full_name FROM ant_user_data WHERE username = %s OR email_id = %s",
            (identifier, identifier)
        )
        user = cursor.fetchone()
        if not user:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail="No account found with that username or email")

        user_id = user['user_id']

        cursor.execute("""
            SELECT created_at FROM email_otp_verifications
            WHERE user_id = %s AND purpose = 'password_reset' ORDER BY created_at DESC LIMIT 1
        """, (user_id,))
        last = cursor.fetchone()
        if last and (datetime.now() - last['created_at']) < timedelta(seconds=60):
            cursor.close()
            conn.close()
            raise HTTPException(status_code=429, detail="Please wait a moment before requesting another code")

        otp_code = f"{secrets.randbelow(1000000):06d}"
        expires_at = datetime.now() + timedelta(minutes=10)
        cursor.execute("""
            INSERT INTO email_otp_verifications (user_id, otp_code, expires_at, purpose)
            VALUES (%s, %s, %s, 'password_reset')
        """, (user_id, otp_code, expires_at))
        conn.commit()
        cursor.close()
        conn.close()

        send_email(
            user['email_id'],
            "Your ANT Crypto Trade password reset code",
            build_otp_email_body(user['full_name'], user['username'], otp_code, "password reset"),
            html_body=build_otp_email_html(user['full_name'], user['username'], otp_code, "password reset")
        )

        return {"message": "A password reset code has been sent to your email", "user_id": user_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))

@app.post("/api/auth/reset-password")
def reset_password(payload: ResetPasswordConfirm):
    """Verifies the password_reset OTP (same expiry/attempts rules as verify-otp) and,
    on success, overwrites the account's password - one-shot, the OTP is consumed
    either way it resolves so it can't be replayed."""
    try:
        new_password = payload.new_password
        if len(new_password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM email_otp_verifications
            WHERE user_id = %s AND is_used = 0 AND purpose = 'password_reset'
            ORDER BY created_at DESC LIMIT 1
        """, (payload.user_id,))
        otp_row = cursor.fetchone()

        if not otp_row:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=400, detail="No pending reset request found. Please request a new code.")

        if otp_row['expires_at'] < datetime.now():
            cursor.close()
            conn.close()
            raise HTTPException(status_code=400, detail="This code has expired. Please request a new one.")

        if otp_row['attempts'] >= 5:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=429, detail="Too many attempts. Please request a new code.")

        if otp_row['otp_code'] != payload.otp_code.strip():
            cursor.execute(
                "UPDATE email_otp_verifications SET attempts = attempts + 1 WHERE id = %s",
                (otp_row['id'],)
            )
            conn.commit()
            cursor.close()
            conn.close()
            raise HTTPException(status_code=400, detail="Incorrect code")

        cursor.execute("UPDATE email_otp_verifications SET is_used = 1 WHERE id = %s", (otp_row['id'],))
        cursor.execute(
            "UPDATE ant_user_data SET password = %s WHERE user_id = %s",
            (hash_password(new_password), payload.user_id)
        )
        conn.commit()
        cursor.close()
        conn.close()

        return {"message": "Password reset successfully. Please login with your new password."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))

def _login_success_payload(user):
    return {
        "message": "Login successful",
        "user_id": user['user_id'],
        "username": user['username'],
        "full_name": user['full_name'],
        "role": user['role']
    }

# How often a completed login must be re-confirmed with an emailed OTP, on top
# of the normal password check - see /api/auth/login's monthly_otp_required
# branch and /api/auth/verify-login-otp.
MONTHLY_LOGIN_OTP_INTERVAL_DAYS = 30

@app.post("/api/auth/login")
def login(credentials: UserLogin):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM ant_user_data WHERE username = %s OR email_id = %s",
                      (credentials.identifier, credentials.identifier))
        user = cursor.fetchone()

        if not user or not verify_password(credentials.password, user['password']):
            cursor.close()
            conn.close()
            raise HTTPException(status_code=401, detail="Invalid credentials")

        uid = user['user_id']
        uid = uid.decode('utf-8') if isinstance(uid, bytes) else uid

        # Demo accounts are admin-provisioned paper-trading logins - no real email
        # inbox to verify and no broker/money behind them - so both OTP steps
        # (registration email verification and the monthly step-up below) are skipped.
        is_demo_user = (user.get('role') or '').lower() == 'demo'

        if not is_demo_user and not user.get('is_verified'):
            cursor.close()
            conn.close()
            raise HTTPException(status_code=403, detail={"message": "Please verify your email before logging in", "otp_required": True, "user_id": uid})

        # Monthly step-up: even with a correct password, an OTP re-confirmation is
        # required once every MONTHLY_LOGIN_OTP_INTERVAL_DAYS. last_otp_login_at
        # NULL (never done) is treated the same as overdue.
        last_otp_login_at = user.get('last_otp_login_at')
        otp_overdue = last_otp_login_at is None or \
            (datetime.now() - last_otp_login_at) >= timedelta(days=MONTHLY_LOGIN_OTP_INTERVAL_DAYS)
        if otp_overdue and not is_demo_user:
            otp_code = f"{secrets.randbelow(1000000):06d}"
            expires_at = datetime.now() + timedelta(minutes=10)
            cursor.execute("""
                INSERT INTO email_otp_verifications (user_id, otp_code, expires_at, purpose)
                VALUES (%s, %s, %s, 'monthly_login')
            """, (uid, otp_code, expires_at))
            conn.commit()
            cursor.close()
            conn.close()

            send_email(
                user['email_id'],
                "Your ANT Crypto Trade login verification code",
                build_otp_email_body(user['full_name'], user['username'], otp_code, "login verification"),
                html_body=build_otp_email_html(user['full_name'], user['username'], otp_code, "login verification")
            )

            raise HTTPException(status_code=403, detail={
                "message": "Please confirm the code we emailed you to complete this login",
                "monthly_otp_required": True,
                "user_id": uid
            })

        cursor.close()
        conn.close()
        return _login_success_payload(user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))

@app.post("/api/auth/verify-login-otp")
def verify_login_otp(payload: OtpVerify):
    """Completes a login that /api/auth/login paused for the monthly OTP
    step-up (see MONTHLY_LOGIN_OTP_INTERVAL_DAYS) - same 10-minute expiry/5-
    attempt lockout as email-verification OTPs, just scoped to purpose=
    'monthly_login' so it can't be satisfied by (or interfere with) a pending
    registration-verification code."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM email_otp_verifications
            WHERE user_id = %s AND is_used = 0 AND purpose = 'monthly_login'
            ORDER BY created_at DESC LIMIT 1
        """, (payload.user_id,))
        otp_row = cursor.fetchone()

        if not otp_row:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=400, detail="No pending verification found. Please log in again.")

        if otp_row['expires_at'] < datetime.now():
            cursor.close()
            conn.close()
            raise HTTPException(status_code=400, detail="This code has expired. Please log in again.")

        if otp_row['attempts'] >= 5:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=429, detail="Too many attempts. Please log in again.")

        if otp_row['otp_code'] != payload.otp_code.strip():
            cursor.execute(
                "UPDATE email_otp_verifications SET attempts = attempts + 1 WHERE id = %s",
                (otp_row['id'],)
            )
            conn.commit()
            cursor.close()
            conn.close()
            raise HTTPException(status_code=400, detail="Incorrect code")

        cursor.execute("UPDATE email_otp_verifications SET is_used = 1 WHERE id = %s", (otp_row['id'],))
        cursor.execute("UPDATE ant_user_data SET last_otp_login_at = %s WHERE user_id = %s", (datetime.now(), payload.user_id))
        conn.commit()

        cursor.execute("SELECT * FROM ant_user_data WHERE user_id = %s", (payload.user_id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return _login_success_payload(user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))

@app.post("/api/auth/resend-login-otp")
def resend_login_otp(payload: OtpResend):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT email_id, username, full_name FROM ant_user_data WHERE user_id = %s", (payload.user_id,))
        user = cursor.fetchone()
        if not user:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail="User not found")

        cursor.execute("""
            SELECT created_at FROM email_otp_verifications
            WHERE user_id = %s AND purpose = 'monthly_login' ORDER BY created_at DESC LIMIT 1
        """, (payload.user_id,))
        last = cursor.fetchone()
        if last and (datetime.now() - last['created_at']) < timedelta(seconds=60):
            cursor.close()
            conn.close()
            raise HTTPException(status_code=429, detail="Please wait a moment before requesting another code")

        otp_code = f"{secrets.randbelow(1000000):06d}"
        expires_at = datetime.now() + timedelta(minutes=10)
        cursor.execute("""
            INSERT INTO email_otp_verifications (user_id, otp_code, expires_at, purpose)
            VALUES (%s, %s, %s, 'monthly_login')
        """, (payload.user_id, otp_code, expires_at))
        conn.commit()
        cursor.close()
        conn.close()

        send_email(
            user['email_id'],
            "Your new ANT Crypto Trade login verification code",
            build_otp_email_body(user['full_name'], user['username'], otp_code, "login verification"),
            html_body=build_otp_email_html(user['full_name'], user['username'], otp_code, "login verification")
        )

        return {"message": "A new code has been sent"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))


# --- Trading data helpers ---------------------------------------------------------

# Today's P&L: closed positions use exit_price (attributed to the day they closed, via
# last_update_DateTime), still-open ones use current_price. Unrealized P&L is NOT
# date-scoped - an open position's mark-to-market always counts, even if the engine was
# down and its row's last_update_DateTime went stale.
def get_today_pnl(cursor, user_id: str) -> dict:
    today = date.today()
    cursor.execute(f"""
        SELECT
            SUM(CASE WHEN s.exit_price IS NOT NULL AND DATE(s.last_update_DateTime) = %s
                     THEN {REALIZED_PNL_EXPR} ELSE 0 END) AS realized_pnl,
            SUM(CASE WHEN s.exit_price IS NULL AND s.is_Active = 1
                     THEN {UNREALIZED_PNL_EXPR} ELSE 0 END) AS unrealized_pnl
        FROM crypto_signal_data s
        WHERE s.user_id = %s
    """, (today, user_id))
    row = cursor.fetchone()
    realized = float(row['realized_pnl']) if row and row['realized_pnl'] is not None else 0
    unrealized = float(row['unrealized_pnl']) if row and row['unrealized_pnl'] is not None else 0
    return {"total": realized + unrealized, "realized": realized, "unrealized": unrealized}

def get_open_orders(cursor, user_id: str, limit: int = 50):
    cursor.execute(f"""
        SELECT s.*,
            ROUND({UNREALIZED_PNL_EXPR}, 2) AS PandL,
            ROUND({UNREALIZED_PNL_EXPR} / NULLIF({MARGIN_EXPR}, 0) * 100, 2) AS PandL_percent,
            ROUND({MARGIN_EXPR}, 2) AS margin
        FROM crypto_signal_data s
        WHERE s.user_id = %s AND s.is_Active = 1
        ORDER BY s.created_DateTime DESC
        LIMIT %s
    """, (user_id, limit))
    return cursor.fetchall()

def compute_live_current_investment(cursor, user_id: str, wallet) -> float:
    """Live capital: the Binance USDT balance the engine last synced (available_funds,
    falling back to binance_exchange_usdt) plus the margin tied up in open positions.
    Deliberately distinct from ant_user_wallet.current_investment, the stable day-to-day
    compounding baseline daily_profit_report is built from."""
    funds = 0.0
    if wallet:
        if wallet.get('available_funds') is not None:
            funds = float(wallet['available_funds'])
        elif wallet.get('binance_exchange_usdt') is not None:
            funds = float(wallet['binance_exchange_usdt'])
    cursor.execute(f"""
        SELECT COALESCE(SUM({MARGIN_EXPR}), 0) AS open_value
        FROM crypto_signal_data s
        WHERE s.user_id = %s AND s.is_Active = 1
    """, (user_id,))
    row = cursor.fetchone()
    return funds + (float(row['open_value']) if row and row['open_value'] is not None else 0.0)

# Dashboard
@app.get("/api/dashboard/{user_id}")
def get_dashboard(user_id: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM ant_user_data WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail="User not found")

        cursor.execute("SELECT * FROM ant_user_wallet WHERE user_id = %s", (user_id,))
        wallet = cursor.fetchone()

        total_profit = float(user['total_profit_amount'] or 0)
        today = date.today()
        today_pnl = get_today_pnl(cursor, user_id)
        today_profit = today_pnl['total']

        cursor.execute("""
            SELECT SUM(profit_amount) AS month_profit FROM daily_profit_report
            WHERE user_id = %s AND date >= %s
        """, (user_id, today.replace(day=1)))
        month_data = cursor.fetchone()

        cursor.execute("""
            SELECT date, start_amount, profit_amount, profit_percent FROM daily_profit_report
            WHERE user_id = %s ORDER BY date DESC LIMIT 7
        """, (user_id,))
        recent_profits = cursor.fetchall()

        open_orders = get_open_orders(cursor, user_id)
        total_investment = compute_live_current_investment(cursor, user_id, wallet)

        cursor.close()
        conn.close()

        wallet_balance = float(wallet['ant_wallet_balance']) if wallet else 0
        month_profit = float(month_data['month_profit']) if month_data and month_data['month_profit'] else 0

        # total_profit_amount and daily_profit_report only cover *prior* days (written at
        # end-of-day) - fold today's live P&L in so Total/Month are not stale by a day.
        total_profit += today_profit
        month_profit += today_profit

        def pct(v):
            return round(v / total_investment * 100, 2) if total_investment > 0 else 0

        return {
            "total_investment": round(total_investment, 2),
            "total_profit": total_profit,
            "total_profit_percent": pct(total_profit),
            "today_profit": today_profit,
            "today_profit_percent": pct(today_profit),
            "today_realized_profit": round(today_pnl['realized'], 2),
            "today_unrealized_profit": round(today_pnl['unrealized'], 2),
            "month_profit": month_profit,
            "month_profit_percent": pct(month_profit),
            "wallet_balance": wallet_balance,
            "open_orders_count": len(open_orders),
            "open_orders": open_orders,
            "recent_profits": recent_profits
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))

# Lightweight endpoint for polling just Open Orders + P&L cards (called every minute
# from the dashboard without re-fetching the whole page)
@app.get("/api/dashboard/{user_id}/live")
def get_dashboard_live(user_id: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM ant_user_wallet WHERE user_id = %s", (user_id,))
        wallet = cursor.fetchone()
        total_investment = compute_live_current_investment(cursor, user_id, wallet)

        today_pnl = get_today_pnl(cursor, user_id)
        today_profit = today_pnl['total']
        open_orders = get_open_orders(cursor, user_id)

        cursor.execute("SELECT total_profit_amount FROM ant_user_data WHERE user_id = %s", (user_id,))
        profit_row = cursor.fetchone()
        total_profit = float(profit_row['total_profit_amount'] or 0) + today_profit if profit_row else today_profit

        cursor.execute("""
            SELECT SUM(profit_amount) AS month_profit FROM daily_profit_report
            WHERE user_id = %s AND date >= %s
        """, (user_id, date.today().replace(day=1)))
        month_data = cursor.fetchone()
        month_profit = (float(month_data['month_profit']) if month_data and month_data['month_profit'] else 0) + today_profit

        cursor.close()
        conn.close()

        def pct(v):
            return round(v / total_investment * 100, 2) if total_investment > 0 else 0

        return {
            "total_investment": round(total_investment, 2),
            "today_profit": today_profit,
            "today_profit_percent": pct(today_profit),
            "today_realized_profit": round(today_pnl['realized'], 2),
            "today_unrealized_profit": round(today_pnl['unrealized'], 2),
            "total_profit": total_profit,
            "total_profit_percent": pct(total_profit),
            "month_profit": month_profit,
            "month_profit_percent": pct(month_profit),
            "open_orders_count": len(open_orders),
            "open_orders": open_orders
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))

# Trade list with filters. status: 'all' (default), 'open' or 'closed'.
@app.get("/api/trades/{user_id}")
def get_trades(user_id: str, period: str = "today", page: int = 1, limit: int = 20,
               from_date: str = None, to_date: str = None, status: str = "all"):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        start_date, end_date = resolve_period_range(period, from_date, to_date)
        offset = (max(page, 1) - 1) * limit

        status_sql = ""
        if status == "open":
            status_sql = "AND s.is_Active = 1"
        elif status == "closed":
            status_sql = "AND s.is_Active = 0"

        cursor.execute(f"""
            SELECT s.*,
                ROUND(CASE WHEN s.exit_price IS NOT NULL THEN {REALIZED_PNL_EXPR} ELSE {UNREALIZED_PNL_EXPR} END, 2) AS PandL,
                ROUND(CASE WHEN s.exit_price IS NOT NULL THEN {REALIZED_PNL_EXPR} ELSE {UNREALIZED_PNL_EXPR} END
                      / NULLIF({MARGIN_EXPR}, 0) * 100, 2) AS PandL_percent
            FROM crypto_signal_data s
            WHERE s.user_id = %s
              AND DATE(s.created_DateTime) BETWEEN %s AND %s
              {status_sql}
            ORDER BY (s.is_Active = 1) DESC, s.created_DateTime DESC
            LIMIT %s OFFSET %s
        """, (user_id, start_date, end_date, limit, offset))
        trades = cursor.fetchall()

        cursor.execute(f"""
            SELECT COUNT(*) AS total FROM crypto_signal_data s
            WHERE s.user_id = %s AND DATE(s.created_DateTime) BETWEEN %s AND %s {status_sql}
        """, (user_id, start_date, end_date))
        total_count = cursor.fetchone()['total']

        cursor.close()
        conn.close()

        return {
            "trades": trades,
            "total": total_count,
            "page": page,
            "limit": limit,
            "total_pages": (total_count + limit - 1) // limit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))

# Max Profit / Max Loss / win-rate stat tiles - aggregated in SQL over EVERY closed
# trade in the period, not just whichever page of get_trades is on screen. Only a strictly
# positive P&L counts as Max Profit and only a strictly negative one as Max Loss, so a
# period with no losers correctly returns None instead of mislabelling the smallest win.
@app.get("/api/trades/{user_id}/pnl-summary")
def get_trades_pnl_summary(user_id: str, period: str = "today", from_date: str = None, to_date: str = None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        start_date, end_date = resolve_period_range(period, from_date, to_date)

        cursor.execute(f"""
            SELECT
                MAX(CASE WHEN t.pnl_amt > 0 THEN t.pnl_amt END) AS max_profit,
                MIN(CASE WHEN t.pnl_amt < 0 THEN t.pnl_amt END) AS max_loss,
                COUNT(*) AS closed_trades,
                SUM(CASE WHEN t.pnl_amt > 0 THEN 1 ELSE 0 END) AS winning_trades,
                SUM(t.pnl_amt) AS net_pnl
            FROM (
                SELECT {REALIZED_PNL_EXPR} AS pnl_amt
                FROM crypto_signal_data s
                WHERE s.user_id = %s AND s.exit_price IS NOT NULL
                  AND DATE(s.created_DateTime) BETWEEN %s AND %s
            ) t
        """, (user_id, start_date, end_date))
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        closed = int(row['closed_trades'] or 0) if row else 0
        wins = int(row['winning_trades'] or 0) if row else 0
        return {
            "max_profit": float(row['max_profit']) if row and row['max_profit'] is not None else None,
            "max_loss": float(row['max_loss']) if row and row['max_loss'] is not None else None,
            "closed_trades": closed,
            "winning_trades": wins,
            "win_rate": round(wins / closed * 100, 2) if closed else None,
            "net_pnl": float(row['net_pnl']) if row and row['net_pnl'] is not None else 0.0,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))

# Order reports - the individual exchange orders. An entry order exists for every
# position (BUY for LONG, SELL for SHORT) from the moment it opens; the exit order (the
# opposite side) exists once the position has closed.
@app.get("/api/order-reports/{user_id}")
def get_order_reports(user_id: str, period: str = "today", from_date: str = None, to_date: str = None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        start_date, end_date = resolve_period_range(period, from_date, to_date)

        cursor.execute("""
            SELECT
                s.created_DateTime AS date,
                s.symbol_name AS symbol,
                CASE WHEN s.side = 'SHORT' THEN 'Sell' ELSE 'Buy' END AS type,
                s.side AS position_side,
                s.quantity,
                s.entry_price AS avg_price,
                s.quantity * s.entry_price AS order_value,
                'Filled' AS status
            FROM crypto_signal_data s
            WHERE s.user_id = %s AND DATE(s.created_DateTime) BETWEEN %s AND %s
        """, (user_id, start_date, end_date))
        entry_orders = cursor.fetchall()

        cursor.execute("""
            SELECT
                s.last_update_DateTime AS date,
                s.symbol_name AS symbol,
                CASE WHEN s.side = 'SHORT' THEN 'Buy' ELSE 'Sell' END AS type,
                s.side AS position_side,
                s.quantity,
                s.exit_price AS avg_price,
                s.quantity * s.exit_price AS order_value,
                'Filled' AS status
            FROM crypto_signal_data s
            WHERE s.user_id = %s AND s.exit_price IS NOT NULL
              AND DATE(s.last_update_DateTime) BETWEEN %s AND %s
        """, (user_id, start_date, end_date))
        exit_orders = cursor.fetchall()

        cursor.close()
        conn.close()

        # fetchall() returns a tuple (not list) for empty result sets on this PyMySQL
        # version, so normalise before concatenating/sorting.
        all_orders = list(entry_orders) + list(exit_orders)
        all_orders.sort(key=lambda x: x['date'], reverse=True)

        return {
            "orders": all_orders,
            "period": period,
            "start_date": str(start_date),
            "end_date": str(end_date)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))

# Cumulative profit/loss by coin (closed trades only)
@app.get("/api/symbol-pnl/{user_id}")
def get_symbol_pnl(user_id: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT
                s.symbol_name,
                COUNT(*) AS total_trades,
                SUM(CASE WHEN {REALIZED_PNL_EXPR} > 0 THEN 1 ELSE 0 END) AS winning_trades,
                SUM({REALIZED_PNL_EXPR}) AS total_pnl
            FROM crypto_signal_data s
            WHERE s.user_id = %s AND s.exit_price IS NOT NULL
            GROUP BY s.symbol_name
            ORDER BY total_pnl DESC
        """, (user_id,))
        symbol_pnl = cursor.fetchall()
        cursor.close()
        conn.close()
        return {"symbol_pnl": symbol_pnl}
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))

# Number of trailing days each daily-profit chart period covers ('1d' is handled
# separately with hourly buckets, since a single day has only one date value).
DAILY_PROFIT_PERIOD_DAYS = {'1d': 1, '1w': 7, '1m': 30, '3m': 90, '6m': 180, '1y': 365}

# Daily profit chart for the Reports page. Pulls straight from the position table
# rather than the daily_profit_report rollup, so today's still-open positions show up
# immediately instead of only after end-of-day settlement. Realized rows bucket by the
# day/hour they closed (last_update_DateTime), open rows by the day they opened.
@app.get("/api/reports/daily-profit/{user_id}")
def get_daily_profit_chart(user_id: str, period: str = "1m"):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        today = date.today()

        if period == "1d":
            cursor.execute(f"""
                SELECT
                    CASE WHEN s.exit_price IS NOT NULL THEN HOUR(s.last_update_DateTime) ELSE HOUR(s.created_DateTime) END AS bucket,
                    SUM(CASE WHEN s.exit_price IS NOT NULL THEN {REALIZED_PNL_EXPR} ELSE {UNREALIZED_PNL_EXPR} END) AS pnl
                FROM crypto_signal_data s
                WHERE s.user_id = %s
                    AND (
                        (s.exit_price IS NOT NULL AND DATE(s.last_update_DateTime) = %s)
                        OR (s.exit_price IS NULL AND DATE(s.created_DateTime) = %s)
                    )
                GROUP BY bucket
                ORDER BY bucket ASC
            """, (user_id, today, today))
            rows = cursor.fetchall()
            data = [{"bucket": f"{int(r['bucket']):02d}:00", "pnl": float(r['pnl'] or 0)} for r in rows]
            granularity = "hour"
        else:
            days = DAILY_PROFIT_PERIOD_DAYS.get(period, 30)
            start_date = today - timedelta(days=days - 1)
            cursor.execute(f"""
                SELECT
                    CASE WHEN s.exit_price IS NOT NULL THEN DATE(s.last_update_DateTime) ELSE DATE(s.created_DateTime) END AS bucket,
                    SUM(CASE WHEN s.exit_price IS NOT NULL THEN {REALIZED_PNL_EXPR}
                             WHEN s.is_Active = 1 THEN {UNREALIZED_PNL_EXPR}
                             ELSE 0 END) AS pnl
                FROM crypto_signal_data s
                WHERE s.user_id = %s
                    AND (
                        (s.exit_price IS NOT NULL AND DATE(s.last_update_DateTime) BETWEEN %s AND %s)
                        OR (s.exit_price IS NULL AND DATE(s.created_DateTime) BETWEEN %s AND %s)
                    )
                GROUP BY bucket
                ORDER BY bucket ASC
            """, (user_id, start_date, today, start_date, today))
            rows = cursor.fetchall()
            data = [{"bucket": str(r['bucket']), "pnl": float(r['pnl'] or 0)} for r in rows]
            granularity = "day"

        cursor.close()
        conn.close()
        return {"period": period, "granularity": granularity, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))

# --- Market data (Binance public endpoints via ccxt - no API key needed) -----------

_exchange_public = ccxt.binance({'enableRateLimit': True})
_market_cache = {}  # key -> (expires_at_epoch, value)

def _cached(key: str, ttl: int, loader):
    now = time.time()
    hit = _market_cache.get(key)
    if hit and hit[0] > now:
        return hit[1]
    value = loader()
    _market_cache[key] = (now + ttl, value)
    return value

def _normalize_pair(symbol: str) -> str:
    """BTCUSDT / BTC/USDT / btc -> 'BTC/USDT' (the format ccxt expects)."""
    s = symbol.strip().upper().replace('-', '/').replace('_', '/')
    if '/' in s:
        return s
    if s.endswith('USDT') and len(s) > 4:
        return f"{s[:-4]}/USDT"
    return f"{s}/USDT"

@app.get("/api/market/top-movers")
def get_top_movers(limit: int = 10):
    """Top USDT pairs by 24h change - prefers the engine-maintained crypto_symbols_data
    table; falls back to Binance's public tickers when it is empty."""
    try:
        limit = max(1, min(limit, 50))
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT symbol_name, current_askPrice AS price, `24hrs_change` AS change_percent, Volumes AS volume
            FROM crypto_symbols_data WHERE is_Active = 1 AND current_askPrice IS NOT NULL
            ORDER BY `24hrs_change` DESC LIMIT %s
        """, (limit,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        if rows:
            return {"source": "engine", "coins": rows}

        def load():
            tickers = _exchange_public.fetch_tickers()
            coins = [
                {"symbol_name": t['symbol'].replace('/', ''), "price": t.get('last'),
                 "change_percent": t.get('percentage'), "volume": t.get('quoteVolume')}
                for sym, t in tickers.items()
                if sym.endswith('/USDT') and t.get('percentage') is not None and (t.get('quoteVolume') or 0) > 1_000_000
            ]
            coins.sort(key=lambda c: c['change_percent'], reverse=True)
            return coins
        return {"source": "binance", "coins": _cached('top-movers', 30, load)[:limit]}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Market data unavailable: {safe_error_detail(e)}")

@app.get("/api/market/live/{symbol}")
def get_live_coin(symbol: str):
    try:
        pair = _normalize_pair(symbol)
        t = _cached(f'ticker:{pair}', 10, lambda: _exchange_public.fetch_ticker(pair))
        return {"symbol": pair.replace('/', ''), "price": t.get('last'), "change_percent": t.get('percentage'),
                "high": t.get('high'), "low": t.get('low'), "volume": t.get('quoteVolume')}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Market data unavailable: {safe_error_detail(e)}")

@app.get("/api/market/candles/{symbol}")
def get_coin_candles(symbol: str, from_datetime: Optional[str] = None, timeframe: str = "15m"):
    """OHLCV candles for the position-detail chart: from from_datetime (ISO) to now."""
    if timeframe not in ('1m', '5m', '15m', '30m', '1h', '4h', '1d'):
        raise HTTPException(status_code=400, detail="Unsupported timeframe")
    try:
        pair = _normalize_pair(symbol)
        since = None
        if from_datetime:
            try:
                since = int(datetime.fromisoformat(from_datetime.replace('Z', '+00:00')).timestamp() * 1000)
            except ValueError:
                raise HTTPException(status_code=400, detail="from_datetime must be an ISO-8601 timestamp")
            # Start a few candles before entry so the chart has context.
            since -= 8 * 15 * 60 * 1000
        ohlcv = _cached(f'candles:{pair}:{timeframe}:{since}', 20,
                        lambda: _exchange_public.fetch_ohlcv(pair, timeframe, since=since, limit=300))
        return {"symbol": pair.replace('/', ''), "timeframe": timeframe, "candles": [
            {"time": c[0], "open": c[1], "high": c[2], "low": c[3], "close": c[4], "volume": c[5]} for c in ohlcv
        ]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Market data unavailable: {safe_error_detail(e)}")

@app.get("/api/market/symbols")
def get_market_symbols():
    """USDT pairs the app can show - powers the symbol list/autocomplete."""
    try:
        def load():
            markets = _exchange_public.load_markets()
            return sorted(m['id'] for m in markets.values() if m.get('quote') == 'USDT' and m.get('spot') and m.get('active'))
        return {"symbols": _cached('symbols', 3600, load)}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Market data unavailable: {safe_error_detail(e)}")


# --- Referral commissions -----------------------------------------------------------
def get_upline_chain(cursor, user_id: str, max_levels: int = 3):
    """Walk up the referal_by chain from user_id, returning up to max_levels upline user_ids
    (closest first). Stops as soon as referal_by doesn't resolve to a registered user - root
    accounts carry the ROOT_REFERRER sentinel, which must not count as a chain link."""
    chain = []
    current_id = user_id
    for _ in range(max_levels):
        cursor.execute("SELECT referal_by FROM ant_user_data WHERE user_id = %s", (current_id,))
        row = cursor.fetchone()
        if not row or not row.get('referal_by'):
            break
        upline_id = row['referal_by']
        cursor.execute("SELECT 1 FROM ant_user_data WHERE user_id = %s", (upline_id,))
        if not cursor.fetchone():
            break
        chain.append(upline_id)
        current_id = upline_id
    return chain

def distribute_referral_commissions(cursor, buyer_user_id: str, amount: float, purchase_label: str):
    """Credit the buyer's upline a commission on a bot purchase, per
    LEVEL_COMMISSION_PERCENTS (level 1 = direct referrer). Commission lands in the
    recipient's referal_income (lifetime total) AND ant_wallet_balance (withdrawable
    earnings) - never activation_balance, which is funded only by deposits and explicit
    transfers. If the chain is shorter than the percent table, the unclaimed shares fold
    into the topmost real upline rather than disappearing.

    The leading "Referral commission (ancestor #N)" text of each logged description is
    load-bearing - GET /api/referral/level-purchases filters on it."""
    chain = get_upline_chain(cursor, buyer_user_id, max_levels=len(LEVEL_COMMISSION_PERCENTS))
    if not chain:
        return

    shares = [0.0] * len(chain)
    for i, pct in enumerate(LEVEL_COMMISSION_PERCENTS):
        shares[min(i, len(chain) - 1)] += pct

    for level_index, upline_user_id in enumerate(chain):
        share_amount = round(amount * shares[level_index], 2)
        if share_amount <= 0:
            continue
        cursor.execute("""
            UPDATE ant_user_wallet
            SET referal_income = referal_income + %s, ant_wallet_balance = ant_wallet_balance + %s
            WHERE user_id = %s
        """, (share_amount, share_amount, upline_user_id))
        if cursor.rowcount == 0:
            print(f"distribute_referral_commissions: no wallet for upline_user_id={upline_user_id!r}, skipping")
            continue
        log_wallet_txn(
            cursor, upline_user_id, 'referal_income', share_amount, 'completed', 'Internal',
            f'Referral commission (ancestor #{level_index + 1}) - {shares[level_index] * 100:.0f}% of {purchase_label}',
            f'Internal - {uuid.uuid4()}', source_user_id=buyer_user_id
        )

# --- Wallet --------------------------------------------------------------------------
# Money model (all USDT):
#   activation_balance  - spendable on bot/power plans; funded by approved deposits and by
#                         transfers from earnings. Not withdrawable.
#   ant_wallet_balance  - earnings (referral commissions); withdrawable on-chain, or
#                         transferable into activation_balance.

# Registered before /api/wallet/{user_id} - FastAPI matches in registration order, so this
# static path must come first or the dynamic route would swallow "deposit-info" as a user_id.
@app.get("/api/wallet/deposit-info")
def get_deposit_info():
    """Admin-managed USDT address (and optional QR) shown in the wallet's Add Funds dialog.
    address is None whenever the admin has disabled deposits."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT usdt_address, network, qr_image, note, is_enabled FROM deposit_settings ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if not row or not row.get('is_enabled'):
            return {"usdt_address": None, "network": None, "qr_image": None, "note": None, "min_deposit": MIN_DEPOSIT_USDT}
        return {"usdt_address": row['usdt_address'], "network": row['network'], "qr_image": row['qr_image'],
                "note": row['note'], "min_deposit": MIN_DEPOSIT_USDT}
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))

@app.get("/api/wallet/{user_id}")
def get_wallet(user_id: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM ant_user_wallet WHERE user_id = %s", (user_id,))
        wallet = cursor.fetchone()
        if not wallet:
            cursor.execute("INSERT INTO ant_user_wallet (user_id) VALUES (%s)", (user_id,))
            conn.commit()
            cursor.execute("SELECT * FROM ant_user_wallet WHERE user_id = %s", (user_id,))
            wallet = cursor.fetchone()

        cursor.execute("SELECT usdt_address FROM ant_user_data WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()

        cursor.execute("""
            SELECT * FROM wallet_transactions WHERE user_id = %s ORDER BY txn_date DESC LIMIT 20
        """, (user_id,))
        transactions = cursor.fetchall()

        cursor.close()
        conn.close()
        return {
            "wallet": wallet,
            "transactions": transactions,
            "usdt_address": user['usdt_address'] if user else None,
            "limits": {"min_withdrawal": MIN_WITHDRAWAL_USDT, "withdrawal_fee": WITHDRAWAL_FEE_USDT, "min_deposit": MIN_DEPOSIT_USDT}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))

@app.get("/api/wallet/{user_id}/transactions")
def get_wallet_transactions(user_id: str, page: int = 1, limit: int = 5, transaction_type: Optional[str] = None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        offset = (max(page, 1) - 1) * limit
        type_sql = "AND transaction_type = %s" if transaction_type else ""
        params = (user_id, transaction_type) if transaction_type else (user_id,)

        cursor.execute(f"""
            SELECT * FROM wallet_transactions WHERE user_id = %s {type_sql}
            ORDER BY txn_date DESC LIMIT %s OFFSET %s
        """, (*params, limit, offset))
        transactions = cursor.fetchall()

        cursor.execute(f"SELECT COUNT(*) AS total FROM wallet_transactions WHERE user_id = %s {type_sql}", params)
        total = cursor.fetchone()['total']

        cursor.close()
        conn.close()
        return {
            "transactions": transactions, "page": page, "limit": limit, "total": total,
            "total_pages": (total + limit - 1) // limit if total else 1
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))

TX_HASH_RE = re.compile(r'^0x[0-9a-fA-F]{64}$')
EVM_ADDRESS_RE = re.compile(r'^0x[0-9a-fA-F]{40}$')

@app.post("/api/wallet/deposit-request/{user_id}")
def request_deposit(user_id: str, payload: DepositRequestCreate):
    """User claims to have sent USDT to the admin address. Nothing is credited yet - this is
    an unverified claim, so the wallet is only credited once an admin has matched the
    transaction hash on-chain and approves it. tx_hash is UNIQUE, so one on-chain transfer
    can only ever be claimed once."""
    try:
        if payload.amount < MIN_DEPOSIT_USDT:
            raise HTTPException(status_code=400, detail=f"Minimum deposit is {MIN_DEPOSIT_USDT:g} USDT")
        tx_hash = payload.tx_hash.strip()
        if not TX_HASH_RE.match(tx_hash):
            raise HTTPException(status_code=400, detail="Enter a valid transaction hash (0x followed by 64 hex characters)")
        tx_hash = tx_hash.lower()

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT 1 FROM deposit_requests WHERE tx_hash = %s", (tx_hash,))
            if cursor.fetchone():
                raise HTTPException(status_code=409, detail="This transaction hash has already been submitted")

            cursor.execute("SELECT network FROM deposit_settings ORDER BY id DESC LIMIT 1")
            settings = cursor.fetchone()
            network = settings['network'] if settings else 'BEP20 (BSC)'

            transaction_id = f"DEP-{uuid.uuid4().hex[:12].upper()}"
            log_wallet_txn(cursor, user_id, 'deposit', payload.amount, 'pending', 'usdt_onchain',
                           f"USDT deposit claim, tx {tx_hash[:10]}...{tx_hash[-6:]}", transaction_id)
            cursor.execute("""
                INSERT INTO deposit_requests (user_id, transaction_id, amount, tx_hash, network, status)
                VALUES (%s, %s, %s, %s, %s, 'pending')
            """, (user_id, transaction_id, payload.amount, tx_hash, network))
            conn.commit()
        finally:
            cursor.close()
            conn.close()
        return {"message": "Deposit submitted for verification", "transaction_id": transaction_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))

@app.post("/api/wallet/withdraw/{user_id}")
def request_withdrawal(user_id: str, withdrawal: WithdrawalRequestCreate):
    """Creates a withdrawal request settled manually by an admin (an on-chain USDT send).
    The requested amount is deducted from the earnings wallet immediately so it cannot be
    double-spent while pending; an admin later marks it completed (sent) or rejected
    (refunded). The address is snapshotted onto the request, so a later edit of the user's
    saved address does not rewrite history. The user receives amount - fee."""
    try:
        if withdrawal.amount < MIN_WITHDRAWAL_USDT:
            raise HTTPException(status_code=400, detail=f"Minimum withdrawal is {MIN_WITHDRAWAL_USDT:g} USDT")
        address = withdrawal.usdt_address.strip()
        if not EVM_ADDRESS_RE.match(address):
            raise HTTPException(status_code=400, detail="Enter a valid BEP20 (BSC) address starting with 0x")

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Row lock so two concurrent requests cannot both pass the balance check.
            cursor.execute("SELECT ant_wallet_balance FROM ant_user_wallet WHERE user_id = %s FOR UPDATE", (user_id,))
            wallet = cursor.fetchone()
            available = float(wallet['ant_wallet_balance']) if wallet and wallet['ant_wallet_balance'] else 0
            if not wallet or available < withdrawal.amount:
                raise HTTPException(status_code=400, detail="Insufficient earnings balance")

            transaction_id = f"WD-{uuid.uuid4().hex[:12].upper()}"
            cursor.execute("UPDATE ant_user_wallet SET ant_wallet_balance = ant_wallet_balance - %s WHERE user_id = %s",
                           (withdrawal.amount, user_id))
            log_wallet_txn(cursor, user_id, 'withdrawal', withdrawal.amount, 'pending', 'usdt_onchain',
                           f"Withdrawal request to {address[:8]}...{address[-6:]}", transaction_id)
            cursor.execute("""
                INSERT INTO withdrawal_requests (user_id, transaction_id, amount, fee, usdt_address, status)
                VALUES (%s, %s, %s, %s, %s, 'pending')
            """, (user_id, transaction_id, withdrawal.amount, WITHDRAWAL_FEE_USDT, address))
            cursor.execute("UPDATE ant_user_data SET usdt_address = %s WHERE user_id = %s AND (usdt_address IS NULL OR usdt_address = '')",
                           (address, user_id))
            conn.commit()
        finally:
            cursor.close()
            conn.close()
        return {"message": "Withdrawal request submitted", "transaction_id": transaction_id,
                "amount": withdrawal.amount, "fee": WITHDRAWAL_FEE_USDT,
                "you_receive": round(withdrawal.amount - WITHDRAWAL_FEE_USDT, 2)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))

@app.post("/api/wallet/transfer/{user_id}")
def transfer_earnings(user_id: str, transfer: WalletTransferCreate):
    """Moves earnings into activation_balance so they can pay for plans - instant and
    unconditional (no admin step), since the money never leaves the platform."""
    try:
        if transfer.amount <= 0:
            raise HTTPException(status_code=400, detail="Transfer amount must be greater than zero")

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT ant_wallet_balance FROM ant_user_wallet WHERE user_id = %s FOR UPDATE", (user_id,))
            wallet = cursor.fetchone()
            if not wallet:
                raise HTTPException(status_code=404, detail="Wallet not found")
            if float(wallet['ant_wallet_balance'] or 0) < transfer.amount:
                raise HTTPException(status_code=400, detail="Insufficient earnings balance")

            cursor.execute("""
                UPDATE ant_user_wallet
                SET ant_wallet_balance = ant_wallet_balance - %s,
                    activation_balance = activation_balance + %s,
                    referal_income_transferred = referal_income_transferred + %s
                WHERE user_id = %s
            """, (transfer.amount, transfer.amount, transfer.amount, user_id))
            log_wallet_txn(cursor, user_id, 'transfer', transfer.amount, 'completed', 'Internal',
                           'Transferred earnings to activation balance', f'Internal - {uuid.uuid4()}')
            conn.commit()
        finally:
            cursor.close()
            conn.close()
        return {"message": "Transfer completed successfully", "amount": transfer.amount}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))

# --- Bot plans ------------------------------------------------------------------------
@app.get("/api/bot-plans")
def get_bot_plans():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM master_bot_plan
            ORDER BY (COALESCE(current_status, '') = 'COMING SOON') ASC, bot_price DESC
        """)
        plans = cursor.fetchall()
        cursor.close()
        conn.close()
        return {"plans": plans}
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))

@app.post("/api/bot-plans/purchase/{user_id}")
def purchase_bot_plan(user_id: str, purchase: BotPurchase):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM master_bot_plan WHERE bot_name = %s", (purchase.bot_name,))
            plan = cursor.fetchone()
            if not plan:
                raise HTTPException(status_code=404, detail="Bot plan not found")
            if (plan.get('current_status') or '').strip().upper() == 'COMING SOON':
                raise HTTPException(status_code=400, detail="This bot is coming soon and not available for purchase yet")

            price = float(plan['discount_price'] if plan['discount_price'] is not None else plan['bot_price'])

            cursor.execute("SELECT activation_balance FROM ant_user_wallet WHERE user_id = %s FOR UPDATE", (user_id,))
            wallet = cursor.fetchone()
            if not wallet or float(wallet['activation_balance']) < price:
                raise HTTPException(status_code=400, detail="Insufficient activation balance")

            cursor.execute("UPDATE ant_user_wallet SET activation_balance = activation_balance - %s WHERE user_id = %s",
                           (price, user_id))
            cursor.execute("UPDATE ant_user_data SET current_plan = %s WHERE user_id = %s", (plan['bot_name'], user_id))
            cursor.execute("INSERT INTO ant_user_bot_purchase (user_id, bot_name) VALUES (%s, %s)", (user_id, plan['bot_name']))
            log_wallet_txn(cursor, user_id, 'bot_purchase', price, 'completed', 'Internal',
                           f'Purchased {plan["bot_name"]}', f'Internal - {uuid.uuid4()}')

            cursor.execute("SELECT full_name FROM ant_user_data WHERE user_id = %s", (user_id,))
            buyer = cursor.fetchone()
            buyer_label = f"{buyer['full_name']}'s" if buyer and buyer.get('full_name') else "a downline user's"
            distribute_referral_commissions(cursor, user_id, price, f'{buyer_label} {plan["bot_name"]} purchase (${price:,.2f})')
            conn.commit()
        finally:
            cursor.close()
            conn.close()
        return {"message": "Bot plan purchased successfully", "plan": plan['bot_name'], "amount": price}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))

# --- Power plans ----------------------------------------------------------------------
@app.get("/api/power-plans")
def get_power_plans():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM master_power_plan ORDER BY power_value ASC")
        plans = cursor.fetchall()
        cursor.close()
        conn.close()
        return {"plans": plans}
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))

@app.post("/api/wallet/activate-points/{user_id}")
def activate_points(user_id: str, activation: PowerActivation):
    """Buy a power package with activation_balance (price/points are read from the DB, never
    trusted from the client)."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM master_power_plan WHERE power_name = %s", (activation.power_name,))
            power_plan = cursor.fetchone()
            if not power_plan:
                raise HTTPException(status_code=404, detail="Power plan not found")

            amount = float(power_plan['discount_price'] if power_plan['discount_price'] is not None else power_plan['power_price'])
            points = float(power_plan['power_value'])

            cursor.execute("SELECT activation_balance FROM ant_user_wallet WHERE user_id = %s FOR UPDATE", (user_id,))
            wallet = cursor.fetchone()
            if not wallet or float(wallet['activation_balance']) < amount:
                raise HTTPException(status_code=400, detail="Insufficient activation balance")

            cursor.execute("UPDATE ant_user_wallet SET activation_balance = activation_balance - %s WHERE user_id = %s",
                           (amount, user_id))
            cursor.execute("UPDATE ant_user_data SET energy_power = energy_power + %s WHERE user_id = %s", (points, user_id))
            log_wallet_txn(cursor, user_id, 'points_activation', amount, 'completed', 'Internal',
                           f'Activated {power_plan["power_name"]} ({points:g} power)', f'Internal - {uuid.uuid4()}')
            cursor.execute("INSERT INTO ant_user_power_purchase (user_id, energy_power) VALUES (%s, %s)", (user_id, points))
            conn.commit()
        finally:
            cursor.close()
            conn.close()
        return {"message": "Power activated successfully", "package": power_plan['power_name'], "amount": amount}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))

# Per-level referral commission history for the referral page. Reads the wallet_transactions
# rows distribute_referral_commissions() writes, filtered by its "Referral commission
# (ancestor #N)" prefix.
@app.get("/api/referral/level-purchases/{user_id}")
def get_referral_level_purchases(user_id: str, level: int = 1, page: int = 1, limit: int = 5):
    if level not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="level must be 1, 2, or 3")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        offset = (max(page, 1) - 1) * limit
        like_pattern = f"Referral commission (ancestor #{level})%"

        cursor.execute("""
            SELECT wt.*, du.username AS source_username, du.full_name AS source_full_name
            FROM wallet_transactions wt
            LEFT JOIN ant_user_data du ON du.user_id = wt.source_user_id
            WHERE wt.user_id = %s AND wt.transaction_type = 'referal_income' AND wt.description LIKE %s
            ORDER BY wt.txn_date DESC LIMIT %s OFFSET %s
        """, (user_id, like_pattern, limit, offset))
        transactions = cursor.fetchall()

        cursor.execute("""
            SELECT COUNT(*) AS total, COALESCE(SUM(amount), 0) AS total_amount FROM wallet_transactions
            WHERE user_id = %s AND transaction_type = 'referal_income' AND description LIKE %s
        """, (user_id, like_pattern))
        agg = cursor.fetchone()
        total = agg['total']

        cursor.close()
        conn.close()
        return {
            "level": level, "transactions": transactions, "page": page, "limit": limit, "total": total,
            "total_amount": float(agg['total_amount']),
            "commission_percent": round(LEVEL_COMMISSION_PERCENTS[level - 1] * 100),
            "total_pages": (total + limit - 1) // limit if total else 1
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))

@app.get("/api/bot-plans/purchases/{user_id}")
def get_bot_purchase_history(user_id: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.*, m.bot_price, m.discount_price
            FROM ant_user_bot_purchase p
            LEFT JOIN master_bot_plan m ON m.bot_name = p.bot_name
            WHERE p.user_id = %s
            ORDER BY p.purchased_date DESC
        """, (user_id,))
        purchases = cursor.fetchall()
        cursor.close()
        conn.close()

        # Bot plans bill yearly - each purchase is valid for 1 year from purchased_date.
        now = datetime.now()
        for p in purchases:
            if p.get('purchased_date'):
                p['expiry_date'] = add_one_year(p['purchased_date'])
                p['is_expired'] = p['expiry_date'] < now
        return {"purchases": purchases}
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))

@app.get("/api/power-plans/purchases/{user_id}")
def get_power_purchase_history(user_id: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.*, m.power_name
            FROM ant_user_power_purchase p
            LEFT JOIN master_power_plan m ON m.power_value = p.energy_power
            WHERE p.user_id = %s
            ORDER BY p.purchased_date DESC
        """, (user_id,))
        purchases = cursor.fetchall()
        cursor.close()
        conn.close()
        return {"purchases": purchases}
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))

# --- Configuration (Binance credentials + trading settings) ---------------------------
def _mask_key(key: Optional[str]) -> str:
    if not key:
        return ''
    return key if len(key) <= 8 else f"{key[:4]}{'*' * 8}{key[-4:]}"

@app.get("/api/config/{user_id}")
def get_config(user_id: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM ant_user_data WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail="User not found")

        cursor.execute("SELECT * FROM ant_user_wallet WHERE user_id = %s", (user_id,))
        wallet = cursor.fetchone()
        live_current_investment = compute_live_current_investment(cursor, user_id, wallet)
        cursor.close()
        conn.close()

        return {
            "exchange_name": user.get('exchange_name') or 'Binance',
            # The secret is write-only: the UI only learns whether one is stored.
            "api_key_masked": _mask_key(user.get('api_key')),
            "has_api_key": bool(user.get('api_key')),
            "has_api_secret": bool(user.get('api_secret')),
            "usdt_address": user.get('usdt_address') or '',
            "whatsapp_number": user.get('mobile_number', ''),
            "total_investment_amount": float(user.get('total_investment_amount') or 0),
            "live_current_investment": round(live_current_investment, 2),
            "binance_exchange_usdt": float(wallet['binance_exchange_usdt']) if wallet and wallet.get('binance_exchange_usdt') is not None else 0.0,
            "single_trade_amount": float(user.get('single_trade_amount') or 0),
            "max_trade": user.get('max_trade', 5),
            "leverage": user.get('leverage', 1),
            "stoploss_percent": float(user.get('stoploss_percent') or 0),
            "target_percent": float(user.get('target_percent') or 0),
            "trade_long": bool(user.get('trade_long', 1)),
            "trade_short": bool(user.get('trade_short', 0)),
            "current_plan": user.get('current_plan', ''),
            "energy_power": float(user.get('energy_power') or 0),
            "min_trading_power": MIN_TRADING_POWER,
            "is_trading_active": bool(user.get('is_trading_active', 1)),
            "referal_code": user.get('referal_code', ''),
            "role": user.get('role', ''),
            "full_name": user.get('full_name', ''),
            "username": user.get('username', ''),
            "email_id": user.get('email_id', ''),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))

@app.put("/api/config/{user_id}")
def update_config(user_id: str, config: ConfigUpdate):
    try:
        update_fields = []
        values = []

        def add(column, value):
            update_fields.append(f"{column} = %s")
            values.append(value)

        # Validate everything up front so a bad value never half-applies.
        if config.single_trade_amount is not None:
            if config.single_trade_amount <= 0:
                raise HTTPException(status_code=400, detail="Single trade amount must be greater than zero")
            add("single_trade_amount", config.single_trade_amount)
        if config.total_investment_amount is not None:
            if config.total_investment_amount < 0:
                raise HTTPException(status_code=400, detail="Investment amount cannot be negative")
            add("total_investment_amount", config.total_investment_amount)
        if config.max_trade is not None:
            if not 1 <= config.max_trade <= 50:
                raise HTTPException(status_code=400, detail="Max open trades must be between 1 and 50")
            add("max_trade", config.max_trade)
        if config.leverage is not None:
            if not 1 <= config.leverage <= 20:
                raise HTTPException(status_code=400, detail="Leverage must be between 1x and 20x")
            add("leverage", config.leverage)
        if config.stoploss_percent is not None:
            if not 0 < config.stoploss_percent <= 90:
                raise HTTPException(status_code=400, detail="Stoploss must be between 0 and 90 percent")
            add("stoploss_percent", config.stoploss_percent)
        if config.target_percent is not None:
            if not 0 < config.target_percent <= 500:
                raise HTTPException(status_code=400, detail="Target must be between 0 and 500 percent")
            add("target_percent", config.target_percent)
        if config.trade_long is not None:
            add("trade_long", 1 if config.trade_long else 0)
        if config.trade_short is not None:
            add("trade_short", 1 if config.trade_short else 0)
        if config.usdt_address is not None:
            address = config.usdt_address.strip()
            if address and not EVM_ADDRESS_RE.match(address):
                raise HTTPException(status_code=400, detail="Enter a valid BEP20 (BSC) address starting with 0x")
            add("usdt_address", address or None)
        if config.mobile_number is not None:
            add("mobile_number", config.mobile_number.strip())
        # An empty string means "leave as is" for the credential fields - the UI never has
        # the stored secret to send back, so a blank field must not wipe it.
        if config.api_key is not None and config.api_key.strip():
            add("api_key", config.api_key.strip())
        if config.api_secret is not None and config.api_secret.strip():
            add("api_secret", encrypt_secret(config.api_secret.strip()))

        if not update_fields:
            return {"message": "Nothing to update"}

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            values.append(user_id)
            cursor.execute(f"UPDATE ant_user_data SET {', '.join(update_fields)}, updated_date = NOW() WHERE user_id = %s", tuple(values))
            conn.commit()
        finally:
            cursor.close()
            conn.close()
        return {"message": "Configuration updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))

@app.post("/api/binance/verify/{user_id}")
def verify_binance_keys(user_id: str):
    """Checks the stored Binance API key/secret against the live exchange: confirms they
    authenticate, refuses keys that can withdraw funds (a trading bot never needs that
    permission, so a key that has it is a needless risk), and syncs the account's USDT
    balance into the wallet."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT api_key, api_secret FROM ant_user_data WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if not user['api_key'] or not user['api_secret']:
            raise HTTPException(status_code=400, detail="Save your Binance API key and secret first")

        exchange = ccxt.binance({'apiKey': user['api_key'], 'secret': decrypt_secret(user['api_secret']), 'enableRateLimit': True,
                                 'options': {'defaultType': 'spot'}})
        try:
            restrictions = exchange.sapiGetAccountApiRestrictions()
        except ccxt.AuthenticationError:
            raise HTTPException(status_code=400, detail="Binance rejected these API credentials. Check the key, secret and IP whitelist.")
        except ccxt.BaseError as e:
            raise HTTPException(status_code=502, detail=f"Could not reach Binance: {str(e)[:200]}")

        if str(restrictions.get('enableWithdrawals')).lower() == 'true':
            raise HTTPException(status_code=400, detail="This API key can withdraw funds. Disable 'Enable Withdrawals' on Binance and try again.")
        if str(restrictions.get('enableSpotAndMarginTrading')).lower() != 'true':
            raise HTTPException(status_code=400, detail="This API key does not have 'Enable Spot & Margin Trading'. Enable it on Binance and try again.")

        try:
            balance = exchange.fetch_balance()
        except ccxt.BaseError as e:
            raise HTTPException(status_code=502, detail=f"Could not read balance from Binance: {str(e)[:200]}")
        usdt = balance.get('USDT') or {}
        total = float(usdt.get('total') or 0)
        free = float(usdt.get('free') or 0)

        cursor.execute("""
            UPDATE ant_user_wallet SET binance_exchange_usdt = %s, available_funds = %s WHERE user_id = %s
        """, (total, free, user_id))
        conn.commit()
        return {"message": "Binance account connected", "usdt_total": round(total, 2), "usdt_free": round(free, 2),
                "futures_enabled": str(restrictions.get('enableFutures')).lower() == 'true'}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))
    finally:
        cursor.close()
        conn.close()

@app.put("/api/config/{user_id}/trading-status")
def update_trading_status(user_id: str, payload: TradingStatusUpdate):
    """The Start/Stop toggle on Settings. Turning OFF always succeeds (a user can always
    pause). Turning ON is refused below MIN_TRADING_POWER, the same floor the engine
    auto-stops at, and while no Binance credentials are stored."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT energy_power, api_key, api_secret FROM ant_user_data WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if payload.is_trading_active:
            if not user['api_key'] or not user['api_secret']:
                raise HTTPException(status_code=400, detail="Connect your Binance API keys in Settings before starting the bot")
            if float(user['energy_power'] or 0) < MIN_TRADING_POWER:
                raise HTTPException(status_code=400, detail=f"Power is below {MIN_TRADING_POWER} - trading can't be started until it's topped up")

        cursor.execute("UPDATE ant_user_data SET is_trading_active = %s WHERE user_id = %s",
                       (1 if payload.is_trading_active else 0, user_id))
        conn.commit()
        return {"message": "Trading started" if payload.is_trading_active else "Trading stopped",
                "is_trading_active": payload.is_trading_active}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))
    finally:
        cursor.close()
        conn.close()


# --- Admin ----------------------------------------------------------------------------
@app.get("/api/admin/dashboard/{admin_user_id}")
def get_admin_dashboard(admin_user_id: str, page: int = 1, limit: int = 10, search: Optional[str] = None):
    """Backs both the Users and P&L Report admin tabs (same per-user rows, different
    columns). Each tab tracks its own page/limit frontend-side."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        require_admin(admin_user_id, cursor, conn)

        offset = (max(page, 1) - 1) * limit
        where = ""
        params = []
        if search and search.strip():
            where = "WHERE username LIKE %s OR full_name LIKE %s OR email_id LIKE %s"
            like = f"%{search.strip()}%"
            params = [like, like, like]

        cursor.execute(f"SELECT COUNT(*) AS total FROM ant_user_data {where}", tuple(params))
        total_count = cursor.fetchone()['total']
        total_pages = (total_count + limit - 1) // limit if limit else 1

        cursor.execute(f"""
            SELECT user_id, full_name, username, email_id, mobile_number, role, energy_power,
                   current_plan, created_date, is_trading_active, is_Active, is_verified,
                   (api_key IS NOT NULL AND api_key <> '' AND api_secret IS NOT NULL AND api_secret <> '') AS has_api_keys
            FROM ant_user_data {where}
            ORDER BY created_date DESC
            LIMIT %s OFFSET %s
        """, (*params, limit, offset))
        users = cursor.fetchall()

        if not users:
            cursor.close()
            conn.close()
            return {"users": [], "total": total_count, "page": page, "limit": limit, "total_pages": total_pages}

        user_ids = [u['user_id'] for u in users]
        placeholders = ','.join(['%s'] * len(user_ids))
        today = date.today()

        cursor.execute(f"""
            SELECT user_id,
                SUM(CASE WHEN date = %s THEN profit_amount ELSE 0 END) AS today_pnl,
                SUM(CASE WHEN date >= %s THEN profit_amount ELSE 0 END) AS month_pnl,
                SUM(profit_amount) AS overall_pnl
            FROM daily_profit_report WHERE user_id IN ({placeholders}) GROUP BY user_id
        """, (today, today.replace(day=1), *user_ids))
        pnl_by_user = {row['user_id']: row for row in cursor.fetchall()}

        cursor.execute(f"""
            SELECT user_id, SUM(energy_power) AS total_power_purchased FROM ant_user_power_purchase
            WHERE user_id IN ({placeholders}) GROUP BY user_id
        """, tuple(user_ids))
        power_by_user = {row['user_id']: float(row['total_power_purchased'] or 0) for row in cursor.fetchall()}

        cursor.execute(f"""
            SELECT user_id, ant_wallet_balance, activation_balance, binance_exchange_usdt
            FROM ant_user_wallet WHERE user_id IN ({placeholders})
        """, tuple(user_ids))
        wallet_by_user = {row['user_id']: row for row in cursor.fetchall()}

        cursor.execute(f"""
            SELECT user_id, COUNT(*) AS open_positions FROM crypto_signal_data
            WHERE is_Active = 1 AND user_id IN ({placeholders}) GROUP BY user_id
        """, tuple(user_ids))
        open_by_user = {row['user_id']: row['open_positions'] for row in cursor.fetchall()}

        cursor.close()
        conn.close()

        result = []
        for u in users:
            uid = u['user_id']
            pnl = pnl_by_user.get(uid, {})
            w = wallet_by_user.get(uid, {})
            overall_pnl = float(pnl.get('overall_pnl') or 0)
            total_power_purchased = power_by_user.get(uid, 0)
            result.append({
                "user_id": uid,
                "full_name": u.get('full_name', ''),
                "username": u.get('username', ''),
                "email_id": u.get('email_id', ''),
                "mobile_number": u.get('mobile_number', ''),
                "role": u.get('role', ''),
                "energy_power": float(u.get('energy_power') or 0),
                "current_plan": u.get('current_plan', ''),
                "created_date": u.get('created_date'),
                "is_trading_active": bool(u.get('is_trading_active')),
                "is_active": bool(u.get('is_Active')),
                "is_verified": bool(u.get('is_verified')),
                "has_api_keys": bool(u.get('has_api_keys')),
                "open_positions": open_by_user.get(uid, 0),
                "today_pnl": float(pnl.get('today_pnl') or 0),
                "month_pnl": float(pnl.get('month_pnl') or 0),
                "overall_pnl": overall_pnl,
                "total_power_purchased": total_power_purchased,
                "profit_per_power_percent": round(overall_pnl / total_power_purchased * 100, 2) if total_power_purchased > 0 else None,
                "wallet_balance": float(w.get('ant_wallet_balance') or 0),
                "activation_balance": float(w.get('activation_balance') or 0),
                "binance_usdt": float(w.get('binance_exchange_usdt') or 0),
            })
        return {"users": result, "total": total_count, "page": page, "limit": limit, "total_pages": total_pages}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))

@app.post("/api/admin/send-email")
def admin_send_email(payload: AdminEmailRequest):
    """Send (or schedule) an email to a single user from the admin Users tab."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        require_admin(payload.admin_user_id, cursor, conn)

        cursor.execute("SELECT email_id FROM ant_user_data WHERE user_id = %s", (payload.target_user_id,))
        target = cursor.fetchone()
        if not target:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Target user not found")

        if payload.send_at is None:
            sent = send_email(
                target['email_id'], payload.subject, payload.body,
                html_body=build_generic_email_html(payload.subject, payload.body)
            )
            cursor.execute("""
                INSERT INTO scheduled_emails
                (admin_user_id, target_user_id, to_email, subject, body, send_at, status, sent_at)
                VALUES (%s, %s, %s, %s, %s, NULL, %s, %s)
            """, (payload.admin_user_id, payload.target_user_id, target['email_id'],
                  payload.subject, payload.body, 'sent' if sent else 'failed', datetime.now()))
            conn.commit()
            cursor.close()
            conn.close()
            return {"message": "Email sent" if sent else "Email send failed", "sent": sent}

        cursor.execute("""
            INSERT INTO scheduled_emails
            (admin_user_id, target_user_id, to_email, subject, body, send_at, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'pending')
        """, (payload.admin_user_id, payload.target_user_id, target['email_id'],
              payload.subject, payload.body, payload.send_at))
        conn.commit()
        cursor.close()
        conn.close()
        return {"message": "Email scheduled", "send_at": payload.send_at}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))

# Admin-wide P&L grouped by buy_reason (the strategy/signal label that triggered entry),
# not by coin - the "which signal performs best" breakdown. Optionally narrowed to one user.
@app.get("/api/admin/signal-pnl/{admin_user_id}")
def get_admin_signal_pnl(admin_user_id: str, period: str = "today", user_id: Optional[str] = None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        require_admin(admin_user_id, cursor, conn)
        start_date, end_date = resolve_period_range(period)

        query = f"""
            SELECT
                IFNULL(s.buy_reason, 'No Signal') AS buy_reason,
                COUNT(*) AS total_trades,
                SUM(CASE WHEN {REALIZED_PNL_EXPR} > 0 THEN 1 ELSE 0 END) AS winning_trades,
                SUM({REALIZED_PNL_EXPR}) AS total_pnl
            FROM crypto_signal_data s
            WHERE s.exit_price IS NOT NULL
              AND DATE(s.last_update_DateTime) BETWEEN %s AND %s
        """
        params = [start_date, end_date]
        if user_id:
            query += " AND s.user_id = %s"
            params.append(user_id)
        query += " GROUP BY IFNULL(s.buy_reason, 'No Signal') ORDER BY total_pnl DESC LIMIT 50"
        cursor.execute(query, tuple(params))
        signal_pnl = cursor.fetchall()
        cursor.close()
        conn.close()
        return {"signal_pnl": signal_pnl}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))

def _list_requests(admin_user_id, table, alias, date_col, page, limit, period, from_date, to_date, status, order_pending_first=True):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        require_admin(admin_user_id, cursor, conn)
        offset = (max(page, 1) - 1) * limit
        where_clauses, params = [], []
        if period != "all":
            start_date, end_date = resolve_period_range(period, from_date, to_date)
            where_clauses.append(f"DATE({alias}.{date_col}) BETWEEN %s AND %s")
            params.extend([start_date, end_date])
        if status:
            where_clauses.append(f"{alias}.status = %s")
            params.append(status)
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        cursor.execute(f"""
            SELECT {alias}.*, u.username, u.full_name
            FROM {table} {alias}
            LEFT JOIN ant_user_data u ON {alias}.user_id = u.user_id
            {where_sql}
            ORDER BY ({alias}.status = 'pending') DESC, {alias}.{date_col} DESC
            LIMIT %s OFFSET %s
        """, (*params, limit, offset))
        rows = cursor.fetchall()
        cursor.execute(f"SELECT COUNT(*) AS total FROM {table} {alias} {where_sql}", tuple(params))
        total_count = cursor.fetchone()['total']
        return rows, total_count
    except HTTPException:
        raise
    finally:
        try:
            cursor.close()
            conn.close()
        except Exception:
            pass  # already closed by require_admin on the 403 path

@app.get("/api/admin/deposits/{admin_user_id}")
def get_admin_deposits(admin_user_id: str, page: int = 1, limit: int = 5, period: str = "all",
                       from_date: Optional[str] = None, to_date: Optional[str] = None, status: Optional[str] = None):
    """status is one of deposit_requests.status: 'pending', 'approved', 'rejected'."""
    try:
        rows, total = _list_requests(admin_user_id, 'deposit_requests', 'd', 'requested_at', page, limit, period, from_date, to_date, status)
        return {"deposits": rows, "total": total, "page": page, "limit": limit, "total_pages": (total + limit - 1) // limit}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))

@app.post("/api/admin/deposits/{deposit_id}/process")
def process_deposit(deposit_id: int, payload: DepositRequestAction):
    """Admin approves (credits activation_balance after matching the tx hash on-chain) or
    rejects (no credit) a USDT deposit claim."""
    try:
        if payload.action not in ('approve', 'reject'):
            raise HTTPException(status_code=400, detail="action must be 'approve' or 'reject'")

        conn = get_db_connection()
        cursor = conn.cursor()
        require_admin(payload.admin_user_id, cursor, conn)
        try:
            cursor.execute("SELECT * FROM deposit_requests WHERE id = %s FOR UPDATE", (deposit_id,))
            deposit = cursor.fetchone()
            if not deposit:
                raise HTTPException(status_code=404, detail="Deposit request not found")
            if deposit['status'] != 'pending':
                raise HTTPException(status_code=400, detail="This deposit request has already been processed")

            approve = payload.action == 'approve'
            cursor.execute("UPDATE deposit_requests SET status = %s, admin_note = %s, processed_at = %s WHERE id = %s",
                           ('approved' if approve else 'rejected', payload.admin_note, datetime.now(), deposit_id))
            cursor.execute("UPDATE wallet_transactions SET status = %s WHERE transaction_id = %s",
                           ('completed' if approve else 'failed', deposit['transaction_id']))
            if approve:
                cursor.execute("""
                    UPDATE ant_user_wallet
                    SET activation_balance = activation_balance + %s, total_deposit = total_deposit + %s
                    WHERE user_id = %s
                """, (deposit['amount'], deposit['amount'], deposit['user_id']))
            conn.commit()
        finally:
            cursor.close()
            conn.close()
        return {"message": "Deposit {}".format('approved' if payload.action == 'approve' else 'rejected')}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))

@app.get("/api/admin/withdrawals/{admin_user_id}")
def get_admin_withdrawals(admin_user_id: str, page: int = 1, limit: int = 5, period: str = "all",
                          from_date: Optional[str] = None, to_date: Optional[str] = None, status: Optional[str] = None):
    """status is one of withdrawal_requests.status: 'pending', 'completed', 'rejected'."""
    try:
        rows, total = _list_requests(admin_user_id, 'withdrawal_requests', 'w', 'requested_at', page, limit, period, from_date, to_date, status)
        return {"withdrawals": rows, "total": total, "page": page, "limit": limit, "total_pages": (total + limit - 1) // limit}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))

@app.post("/api/admin/withdrawals/{withdrawal_id}/process")
def process_withdrawal(withdrawal_id: int, payload: WithdrawalRequestAction):
    """Admin marks a pending withdrawal completed (USDT already sent on-chain; the tx hash
    is recorded for the user's history) or rejected (amount refunded to their earnings)."""
    try:
        if payload.action not in ('complete', 'reject'):
            raise HTTPException(status_code=400, detail="action must be 'complete' or 'reject'")
        tx_hash = (payload.tx_hash or '').strip()
        if payload.action == 'complete' and tx_hash and not TX_HASH_RE.match(tx_hash):
            raise HTTPException(status_code=400, detail="tx_hash must be 0x followed by 64 hex characters")

        conn = get_db_connection()
        cursor = conn.cursor()
        require_admin(payload.admin_user_id, cursor, conn)
        try:
            cursor.execute("SELECT * FROM withdrawal_requests WHERE id = %s FOR UPDATE", (withdrawal_id,))
            withdrawal = cursor.fetchone()
            if not withdrawal:
                raise HTTPException(status_code=404, detail="Withdrawal request not found")
            if withdrawal['status'] != 'pending':
                raise HTTPException(status_code=400, detail="This withdrawal request has already been processed")

            complete = payload.action == 'complete'
            cursor.execute("""
                UPDATE withdrawal_requests SET status = %s, admin_note = %s, tx_hash = %s, processed_at = %s WHERE id = %s
            """, ('completed' if complete else 'rejected', payload.admin_note, tx_hash or None, datetime.now(), withdrawal_id))
            cursor.execute("UPDATE wallet_transactions SET status = %s WHERE transaction_id = %s",
                           ('completed' if complete else 'failed', withdrawal['transaction_id']))
            if complete:
                cursor.execute("UPDATE ant_user_wallet SET total_withdrawal = total_withdrawal + %s WHERE user_id = %s",
                               (withdrawal['amount'], withdrawal['user_id']))
            else:
                # Refund the amount deducted up-front when the request was made
                cursor.execute("UPDATE ant_user_wallet SET ant_wallet_balance = ant_wallet_balance + %s WHERE user_id = %s",
                               (withdrawal['amount'], withdrawal['user_id']))
            conn.commit()
        finally:
            cursor.close()
            conn.close()
        return {"message": "Withdrawal {}".format('completed' if payload.action == 'complete' else 'rejected')}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))

@app.get("/api/admin/deposit-settings/{admin_user_id}")
def get_admin_deposit_settings(admin_user_id: str):
    """Admin-only view of the deposit address settings - unlike the public
    GET /api/wallet/deposit-info it always returns the stored values, even when disabled."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        require_admin(admin_user_id, cursor, conn)
        cursor.execute("SELECT usdt_address, network, qr_image, note, is_enabled FROM deposit_settings ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if not row:
            return {"usdt_address": None, "network": "BEP20 (BSC)", "qr_image": None, "note": None, "is_enabled": True}
        return {**row, "is_enabled": bool(row['is_enabled'])}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))

@app.post("/api/admin/deposit-settings")
def update_deposit_settings(payload: DepositSettingsUpdate):
    """Admin sets/replaces the USDT deposit address (and optional QR) and can flip
    is_enabled to show/hide the deposit option for everyone instantly."""
    try:
        if payload.usdt_address is not None and not EVM_ADDRESS_RE.match(payload.usdt_address.strip()):
            raise HTTPException(status_code=400, detail="usdt_address must be a valid BEP20 (BSC) address")
        if payload.qr_image is not None:
            if not payload.qr_image.startswith('data:image/'):
                raise HTTPException(status_code=400, detail="qr_image must be a base64 image data URI")
            if len(payload.qr_image) > MAX_QR_IMAGE_LENGTH:
                raise HTTPException(status_code=400, detail="QR image is too large")

        conn = get_db_connection()
        cursor = conn.cursor()
        require_admin(payload.admin_user_id, cursor, conn)
        try:
            cursor.execute("SELECT id FROM deposit_settings ORDER BY id DESC LIMIT 1")
            existing = cursor.fetchone()
            if existing:
                fields, values = ["uploaded_by = %s", "uploaded_at = NOW()"], [payload.admin_user_id]
                for column, value in (("usdt_address", payload.usdt_address and payload.usdt_address.strip()),
                                      ("network", payload.network), ("qr_image", payload.qr_image),
                                      ("note", payload.note), ("is_enabled", payload.is_enabled)):
                    if value is not None:
                        fields.append(f"{column} = %s")
                        values.append(value)
                values.append(existing['id'])
                cursor.execute(f"UPDATE deposit_settings SET {', '.join(fields)} WHERE id = %s", tuple(values))
            else:
                if not payload.usdt_address:
                    raise HTTPException(status_code=400, detail="usdt_address is required the first time")
                cursor.execute("""
                    INSERT INTO deposit_settings (usdt_address, network, qr_image, note, is_enabled, uploaded_by)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (payload.usdt_address.strip(), payload.network or 'BEP20 (BSC)', payload.qr_image, payload.note,
                      payload.is_enabled if payload.is_enabled is not None else True, payload.admin_user_id))
            conn.commit()
        finally:
            cursor.close()
            conn.close()
        return {"message": "Deposit settings updated"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))

@app.get("/api/admin/wallet-transactions/{admin_user_id}")
def get_admin_wallet_transactions(admin_user_id: str, page: int = 1, limit: int = 10, transaction_type: Optional[str] = None):
    """Platform-wide wallet ledger (all users), newest first."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        require_admin(admin_user_id, cursor, conn)
        offset = (max(page, 1) - 1) * limit
        type_sql = "WHERE t.transaction_type = %s" if transaction_type else ""
        params = (transaction_type,) if transaction_type else ()
        cursor.execute(f"""
            SELECT t.*, u.username, u.full_name FROM wallet_transactions t
            LEFT JOIN ant_user_data u ON t.user_id = u.user_id
            {type_sql} ORDER BY t.txn_date DESC LIMIT %s OFFSET %s
        """, (*params, limit, offset))
        rows = cursor.fetchall()
        cursor.execute(f"SELECT COUNT(*) AS total FROM wallet_transactions t {type_sql}", params)
        total = cursor.fetchone()['total']
        cursor.close()
        conn.close()
        return {"transactions": rows, "total": total, "page": page, "limit": limit, "total_pages": (total + limit - 1) // limit}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_detail(e))
