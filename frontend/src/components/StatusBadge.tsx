import React from 'react';
import type { OrderStatus } from '@/lib/api';

interface StatusBadgeProps {
  status: OrderStatus | 'pending' | 'paid' | 'cancelled' | string;
}

const STATUS_CONFIG: Record<string, { label: string; cls: string }> = {
  // OmniBot order statuses
  awaiting_payment: { label: '⏳ Awaiting Payment', cls: 'badge-warning' },
  paid:             { label: '💰 Paid',             cls: 'badge-success' },
  preparing:        { label: '👨‍🍳 Preparing',        cls: 'badge-info'    },
  dispatched:       { label: '🚴 Dispatched',        cls: 'badge-primary'  },
  delivered:        { label: '✅ Delivered',         cls: 'badge-success' },
  cancelled:        { label: '❌ Cancelled',         cls: 'badge-danger'  },
  payment_expired:  { label: '🕐 Expired',           cls: 'badge-danger'  },
  // Legacy transaction statuses (kept for backward compat)
  pending:          { label: '⏳ Pending',           cls: 'badge-warning' },
};

export default function StatusBadge({ status }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status];
  if (config) {
    return <span className={`badge ${config.cls}`}>{config.label}</span>;
  }
  // Fallback for unknown statuses
  return <span className="badge">{status.replace(/_/g, ' ').toUpperCase()}</span>;
}
