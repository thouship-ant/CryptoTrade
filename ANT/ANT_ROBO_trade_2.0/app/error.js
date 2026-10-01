'use client';

import MaintenanceScreen from '@/components/MaintenanceScreen';

// Next.js's own error boundary - catches unexpected render-time crashes that
// ConnectivityGate's fetch interception wouldn't (that only watches API
// responses, not React errors), so a broken page falls back to the same
// maintenance screen instead of Next's default error overlay.
export default function Error({ reset }) {
  return <MaintenanceScreen onRetry={reset} />;
}
