'use client';

// Statically imports recharts - see DailyProfitChart.jsx's own comment on why
// (consumers should next/dynamic this whole file with ssr:false).
import { Bar, ComposedChart, CartesianGrid, XAxis, YAxis, ResponsiveContainer, Tooltip, ReferenceLine } from 'recharts';

const UP_COLOR = '#16a34a';
const DOWN_COLOR = '#dc2626';

// Recharts has no built-in candlestick mark - the standard technique is a Bar
// whose dataKey is the candle's [low, high] range, so recharts itself computes
// the pixel y/height spanning that range; a custom `shape` then draws the real
// wick + body by linearly interpolating where open/close fall inside that
// already-computed [low, high] pixel span, rather than needing direct access
// to the y-axis scale function (which Bar's shape props don't reliably expose).
function Candle(props) {
  const { x, y, width, height, payload } = props;
  const { open, high, low, close } = payload;
  const isUp = close >= open;
  const color = isUp ? UP_COLOR : DOWN_COLOR;
  const wickX = x + width / 2;
  const range = high - low || 1;
  const pixelFor = (value) => y + height * (high - value) / range;
  const bodyTop = pixelFor(Math.max(open, close));
  const bodyBottom = pixelFor(Math.min(open, close));
  const bodyHeight = Math.max(bodyBottom - bodyTop, 1);

  return (
    <g>
      <line x1={wickX} x2={wickX} y1={y} y2={y + height} stroke={color} strokeWidth={1} />
      <rect x={x} y={bodyTop} width={width} height={bodyHeight} fill={color} />
    </g>
  );
}

function CandleTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null;
  const d = payload[0].payload;
  return (
    <div className="rounded-md border bg-background px-3 py-2 text-xs shadow-md">
      <div className="font-medium mb-1">{new Date(label).toLocaleString()}</div>
      <div>O: {d.open} &nbsp; H: {d.high} &nbsp; L: {d.low} &nbsp; C: {d.close}</div>
    </div>
  );
}

// entryPrice draws a dashed reference line at the price the position was opened at, so
// it's visually obvious whether the market has since moved through that level.
export default function CandlestickChart({ candles, entryPrice }) {
  if (!candles || candles.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-muted-foreground text-sm">
        No candle data available for this position
      </div>
    );
  }

  const data = candles.map((c) => ({ ...c, range: [c.low, c.high] }));
  const lows = data.map((c) => c.low);
  const highs = data.map((c) => c.high);
  const min = Math.min(...lows, entryPrice ?? Infinity);
  const max = Math.max(...highs, entryPrice ?? -Infinity);
  const pad = (max - min) * 0.05 || 1;

  return (
    <ResponsiveContainer width="100%" height={288}>
      <ComposedChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
        <CartesianGrid vertical={false} strokeDasharray="3 3" />
        <XAxis
          dataKey="time"
          tickLine={false}
          axisLine={false}
          tickMargin={8}
          minTickGap={40}
          tick={{ fontSize: 11 }}
          tickFormatter={(value) => new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        />
        <YAxis
          domain={[min - pad, max + pad]}
          tickLine={false}
          axisLine={false}
          tickMargin={8}
          width={70}
          tick={{ fontSize: 11 }}
          tickFormatter={(value) => Number(value) >= 100 ? Number(value).toFixed(1) : Number(value).toPrecision(4)}
        />
        <Tooltip content={<CandleTooltip />} />
        {entryPrice != null && (
          <ReferenceLine y={entryPrice} stroke="#F5B400" strokeDasharray="4 4" label={{ value: 'Entry', position: 'insideTopLeft', fontSize: 11, fill: '#F5B400' }} />
        )}
        <Bar dataKey="range" shape={<Candle />} isAnimationActive={false} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
