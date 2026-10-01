'use client';

import { useState } from 'react';

// Base asset of a Binance pair: BTCUSDT / BTC/USDT -> BTC
function baseAsset(symbol) {
  const s = (symbol || '').trim().toUpperCase().replace('/', '');
  return s.endsWith('USDT') && s.length > 4 ? s.slice(0, -4) : s;
}

// Coin logo from the open-source cryptocurrency-icons set; falls back to a gold
// initials badge for coins it doesn't cover (or when offline), so a row never shows a
// broken image.
export default function CoinIcon({ symbol, size = 32, className = '' }) {
  const base = baseAsset(symbol);
  const [failed, setFailed] = useState(false);

  if (!base || failed) {
    return (
      <div
        className={`flex-shrink-0 flex items-center justify-center rounded-full bg-gradient-to-br from-amber-300 to-amber-600 font-bold text-black ${className}`}
        style={{ width: size, height: size, fontSize: Math.max(10, Math.round(size * 0.34)) }}
        aria-label={`${base || 'Coin'} logo`}
      >
        {base.slice(0, 3)}
      </div>
    );
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={`https://cdn.jsdelivr.net/gh/spothq/cryptocurrency-icons@master/svg/color/${base.toLowerCase()}.svg`}
      alt={`${base} logo`}
      width={size}
      height={size}
      loading="lazy"
      className={`flex-shrink-0 rounded-full ${className}`}
      onError={() => setFailed(true)}
    />
  );
}
