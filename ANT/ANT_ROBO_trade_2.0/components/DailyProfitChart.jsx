'use client';

// Statically imports recharts + the chart wrapper (which itself statically imports
// recharts as JSX component types - see components/ui/chart.jsx). Consumers should
// next/dynamic this whole file with ssr:false rather than importing it directly.
import { Bar, BarChart, CartesianGrid, XAxis, YAxis, Cell } from 'recharts';
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart';

const chartConfig = {
  pnl: { label: 'P&L', color: '#F5B400' },
};

function formatBucketLabel(bucket, granularity) {
  if (granularity === 'hour') return `${bucket} Hrs`;
  const d = new Date(bucket);
  return Number.isNaN(d.getTime()) ? bucket : d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export default function DailyProfitChart({ data, granularity }) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-muted-foreground text-sm">
        No trade data available for this period
      </div>
    );
  }

  return (
    <ChartContainer config={chartConfig} className="aspect-auto h-72 w-full">
      <BarChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
        <CartesianGrid vertical={false} strokeDasharray="3 3" />
        <XAxis
          dataKey="bucket"
          tickLine={false}
          axisLine={false}
          tickMargin={8}
          minTickGap={24}
          tick={{ fontSize: 11 }}
          tickFormatter={(value) => formatBucketLabel(value, granularity)}
        />
        <YAxis
          tickLine={false}
          axisLine={false}
          tickMargin={8}
          width={70}
          tick={{ fontSize: 11 }}
          tickFormatter={(value) => `$${Number(value).toLocaleString()}`}
        />
        <ChartTooltip
          cursor={{ fill: 'rgba(0,0,0,0.05)' }}
          content={
            <ChartTooltipContent
              labelFormatter={(value) => formatBucketLabel(value, granularity)}
            />
          }
        />
        <Bar dataKey="pnl" radius={4}>
          {data.map((entry, index) => (
            <Cell key={index} fill={entry.pnl >= 0 ? '#16a34a' : '#dc2626'} />
          ))}
        </Bar>
      </BarChart>
    </ChartContainer>
  );
}
