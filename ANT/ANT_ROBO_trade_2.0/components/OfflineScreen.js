'use client';

export default function OfflineScreen({ onRetry }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="flex flex-col items-center text-center max-w-sm">
        <img
          src="/assets/images/offline.gif"
          alt=""
          width={140}
          height={140}
          className="mb-6"
        />
        <h1 className="text-2xl font-bold text-foreground mb-2">You&apos;re Offline</h1>
        <p className="text-muted-foreground mb-6">
          Check your internet connection. We&apos;ll reconnect automatically once you&apos;re back online.
        </p>
        <button
          type="button"
          onClick={onRetry}
          className="btn bg-primary hover:bg-primary/90 text-white rounded-md px-5 py-2.5 text-sm font-medium transition-colors"
        >
          Try Again
        </button>
      </div>
    </div>
  );
}
