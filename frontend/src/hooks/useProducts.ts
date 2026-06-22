'use client';

// ─── OmniShop TMA — Products Hook ───

import { useState, useEffect, useCallback, useRef } from 'react';
import { getProducts, type Product } from '@/lib/api';

interface UseProductsReturn {
  products: Product[];
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useProducts(search?: string): UseProductsReturn {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const searchRef = useRef(search);
  searchRef.current = search;

  const fetchProducts = useCallback(async () => {
    // Abort any in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    setLoading(true);
    setError(null);

    try {
      const data = await getProducts({
        search: searchRef.current || undefined,
        limit: 50,
      });
      setProducts(data.items);
    } catch (err) {
      // Don't set error for aborted requests
      if (err instanceof Error && err.name === 'AbortError') return;
      const message =
        err instanceof Error ? err.message : 'Failed to load products';
      setError(message);
      console.error('Failed to fetch products:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Debounce search queries
    const timeoutId = setTimeout(() => {
      fetchProducts();
    }, search !== undefined ? 300 : 0);

    return () => {
      clearTimeout(timeoutId);
    };
  }, [search, fetchProducts]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  return {
    products,
    loading,
    error,
    refetch: fetchProducts,
  };
}
