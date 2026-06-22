import React from 'react';

interface StatusBadgeProps {
  status: 'pending' | 'paid' | 'cancelled' | string;
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const getBadgeClass = () => {
    switch (status) {
      case 'paid':
        return 'badge-success';
      case 'pending':
        return 'badge-warning';
      case 'cancelled':
        return 'badge-danger';
      default:
        return '';
    }
  };

  const getLabel = () => {
    switch (status) {
      case 'paid':
        return 'Paid';
      case 'pending':
        return 'Pending';
      case 'cancelled':
        return 'Cancelled';
      default:
        return status.toUpperCase();
    }
  };

  return <span className={`badge ${getBadgeClass()}`}>{getLabel()}</span>;
}
