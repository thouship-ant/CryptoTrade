'use client';

export default function MaintenanceScreen({ onRetry }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="flex flex-col items-center text-center max-w-sm">
        <img
          src="/assets/images/maintenance.png"
          alt=""
          width={220}
          height={220}
          className="mb-6"
        />
        <h1 className="text-2xl font-bold text-foreground mb-2">We&apos;ll Be Right Back</h1>
        <p className="text-muted-foreground mb-6">
          Our servers are temporarily unavailable. Please try again in a few moments.
        </p>
        <button
          type="button"
          onClick={onRetry}
          className="btn bg-primary hover:bg-primary/90 text-white rounded-md px-5 py-2.5 text-sm font-medium transition-colors"
        >
          Retry
        </button>
      </div>
    </div>
  );
}
