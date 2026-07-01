/**
 * useOrders — fetches the admin order list with optional status filtering.
 * Wraps the `listOrders` API call with loading/error state.
 */
'use client';

import { useCallback, useEffect, useState } from 'react';
import { listOrders, type Order } from '@/lib/api';

interface UseOrdersOptions {
  status?: string;
  limit?: number;
}

interface UseOrdersResult {
  orders: Order[];
  total: number;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useOrders(options: UseOrdersOptions = {}): UseOrdersResult {
  const [orders, setOrders] = useState<Order[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(() => {
    setLoading(true);
    listOrders({
      status: options.status === 'all' ? undefined : options.status,
      limit: options.limit ?? 100,
    })
      .then((res) => {
        setOrders(res.items);
        setTotal(res.total);
        setError(null);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Failed to load orders');
      })
      .finally(() => setLoading(false));
  }, [options.status, options.limit]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { orders, total, loading, error, refetch: fetch };
}
