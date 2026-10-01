'use client';

import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

export const PERIOD_OPTIONS = [
  { value: 'today', label: 'Today' },
  { value: 'yesterday', label: 'Yesterday' },
  { value: 'current_week', label: 'Current Week' },
  { value: 'last_week', label: 'Last Week' },
  { value: 'current_month', label: 'Current Month' },
  { value: 'last_month', label: 'Last Month' },
  { value: 'current_year', label: 'Current Year' },
  { value: 'custom', label: 'Custom Range' },
];

// Query-string tail for the backend's resolve_period_range: custom needs both dates.
export function periodQuery(period, from, to) {
  return `period=${period}${period === 'custom' && from && to ? `&from_date=${from}&to_date=${to}` : ''}`;
}

// A custom range needs both ends picked before there's a real range to fetch.
export function periodReady(period, from, to) {
  return period !== 'custom' || Boolean(from && to);
}

// Shared period dropdown (+ date pickers for "Custom Range") used by Orders and Reports.
export default function PeriodFilter({ period, onPeriodChange, from, to, onFromChange, onToChange }) {
  return (
    <>
      <Select value={period} onValueChange={onPeriodChange}>
        <SelectTrigger className="flex-1 min-w-0 sm:flex-none sm:w-[160px] text-xs sm:text-sm">
          <SelectValue placeholder="Select period" />
        </SelectTrigger>
        <SelectContent className="bg-popover">
          {PERIOD_OPTIONS.map((o) => (
            <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
          ))}
        </SelectContent>
      </Select>
      {period === 'custom' && (
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <Input
            type="date"
            aria-label="From date"
            className="flex-1 min-w-0 sm:flex-none sm:w-[150px] text-xs sm:text-sm"
            value={from}
            max={to || undefined}
            onChange={(e) => onFromChange(e.target.value)}
          />
          <span className="text-muted-foreground text-sm">to</span>
          <Input
            type="date"
            aria-label="To date"
            className="flex-1 min-w-0 sm:flex-none sm:w-[150px] text-xs sm:text-sm"
            value={to}
            min={from || undefined}
            onChange={(e) => onToChange(e.target.value)}
          />
        </div>
      )}
    </>
  );
}
