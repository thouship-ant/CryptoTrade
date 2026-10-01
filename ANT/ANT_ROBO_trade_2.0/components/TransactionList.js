'use client';

import { Badge } from '@/components/ui/badge';
import { ArrowUpRight, ArrowDownRight, User } from 'lucide-react';

const CREDIT_TYPES = new Set(['deposit', 'referal_income']);

// Shared wallet-transaction row template, used by the Wallet page's Transaction History
// and the Referral page's per-level purchase history so both look and paginate the same way.
export default function TransactionList({ transactions, loading, emptyMessage = 'No transactions yet' }) {
  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-amber-500"></div>
      </div>
    );
  }

  if (!transactions || transactions.length === 0) {
    return <div className="text-center py-8 text-muted-foreground">{emptyMessage}</div>;
  }

  return (
    <div className="space-y-4">
      {transactions.map((txn, index) => {
        const isCredit = CREDIT_TYPES.has(txn.transaction_type);

        return (
          <div key={txn.transaction_id || index} className="flex items-center justify-between p-4 border rounded-lg">
            <div className="flex items-center gap-4 min-w-0">
              <div className={`h-10 w-10 shrink-0 rounded-full flex items-center justify-center ${
                isCredit ? 'bg-green-100' : 'bg-red-100'
              }`}>
                {isCredit ? (
                  <ArrowUpRight className="h-5 w-5 text-green-600" />
                ) : (
                  <ArrowDownRight className="h-5 w-5 text-red-600" />
                )}
              </div>
              <div className="min-w-0">
                <div className="font-medium capitalize flex items-center gap-2">
                  {(txn.transaction_type || '').replace(/_/g, ' ')}
                  {txn.payment_method === 'usdt_onchain' && (
                    <Badge variant="outline" className="text-xs">
                      USDT
                    </Badge>
                  )}
                </div>
                <div className="text-sm text-muted-foreground">
                  {txn.txn_date ? new Date(txn.txn_date).toLocaleString() : ''}
                </div>
                {(txn.source_full_name || txn.source_username) && (
                  <div className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
                    <User className="h-3 w-3 shrink-0" />
                    <span className="truncate">
                      {txn.source_full_name || 'Unknown user'}
                      {txn.source_username && ` (@${txn.source_username})`}
                    </span>
                  </div>
                )}
                {txn.description && (
                  <div className="text-xs text-muted-foreground/70 mt-1 break-words">{txn.description}</div>
                )}
              </div>
            </div>
            <div className="text-right shrink-0 pl-4">
              <div className={`text-lg font-bold whitespace-nowrap ${
                isCredit ? 'text-green-600' : 'text-red-600'
              }`}>
                {isCredit ? '+' : '-'}${parseFloat(txn.amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} USDT
              </div>
              <Badge variant={
                txn.status === 'completed' ? 'default' :
                txn.status === 'pending' ? 'secondary' :
                'destructive'
              }>
                {txn.status}
              </Badge>
            </div>
          </div>
        );
      })}
    </div>
  );
}
