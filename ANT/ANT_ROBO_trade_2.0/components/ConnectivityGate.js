'use client';

import { useEffect, useState, useCallback } from 'react';
import { getApiBaseUrl } from '@/lib/apiConfig';
import OfflineScreen from './OfflineScreen';
import MaintenanceScreen from './MaintenanceScreen';

// Mounted once at the root layout so the whole app - not just one page - falls
// back to a dedicated screen instead of a broken/blank page when the device
// loses its network connection, or our own backend is fully unreachable
// (502 specifically). A plain 500 is deliberately NOT treated as maintenance -
// that's usually a bug in one endpoint, not the whole backend being down, and
// a dashboard that fires several parallel calls where only one 500s while the
// rest succeed would otherwise flicker the whole app in and out of takeover
// as each promise settles in turn. Let each page's own error handling deal
// with a 500 instead.
export function ConnectivityGate({ children }) {
  const [isOffline, setIsOffline] = useState(false);
  const [isMaintenance, setIsMaintenance] = useState(false);

  useEffect(() => {
    setIsOffline(typeof navigator !== 'undefined' && !navigator.onLine);
    const handleOnline = () => setIsOffline(false);
    const handleOffline = () => setIsOffline(true);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  useEffect(() => {
    // Wraps window.fetch once so every call our own pages make to the backend
    // is observed for 5xx responses (502 in particular means the reverse
    // proxy can't reach the backend at all) without changing what each
    // page's own fetch() call receives back - this only sets shared state as
    // a side effect, the original Response/rejection is always returned or
    // thrown unchanged so existing per-page error handling keeps working.
    // Scoped to our own API base URL so a flaky third-party call (e.g. the
    // IFSC lookup on the Wallet page) can't trigger an app-wide takeover.
    const originalFetch = window.fetch;
    const apiBase = getApiBaseUrl();

    window.fetch = async (...args) => {
      const requestUrl = typeof args[0] === 'string' ? args[0] : args[0]?.url || '';
      const isOwnApiCall = requestUrl.startsWith(apiBase);

      try {
        const response = await originalFetch(...args);
        if (isOwnApiCall) {
          setIsMaintenance(response.status === 502);
        }
        return response;
      } catch (err) {
        // A rejected fetch to our own API is either "no network" (already
        // handled by the online/offline listeners above) or the backend
        // being fully unreachable - only escalate to the maintenance screen
        // for the latter, so the two screens don't fight over one failure.
        if (isOwnApiCall && navigator.onLine) {
          setIsMaintenance(true);
        }
        throw err;
      }
    };

    return () => {
      window.fetch = originalFetch;
    };
  }, []);

  const handleRetry = useCallback(() => {
    window.location.reload();
  }, []);

  if (isOffline) {
    return <OfflineScreen onRetry={handleRetry} />;
  }
  if (isMaintenance) {
    return <MaintenanceScreen onRetry={handleRetry} />;
  }
  return children;
}
