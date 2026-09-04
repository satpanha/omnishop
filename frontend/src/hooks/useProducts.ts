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

const CACHE_PREFIX = 'omnishop_cat_';

function getInitialCache(category?: string): Product[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = sessionStorage.getItem(`${CACHE_PREFIX}${category || 'All'}`);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function useProducts(search?: string, category?: string): UseProductsReturn {
  const [products, setProducts] = useState<Product[]>(() => getInitialCache(category));
  const [loading, setLoading] = useState<boolean>(() => getInitialCache(category).length === 0);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const searchRef = useRef(search);
  searchRef.current = search;
  const categoryRef = useRef(category);
  categoryRef.current = category;

  const fetchProducts = useCallback(async () => {
    // Abort any in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    // If we already have cached items, keep them visible while refreshing in background
    if (products.length === 0) {
      setLoading(true);
    }
    setError(null);

    try {
      const cat = categoryRef.current;
      const data = await getProducts({
        search: searchRef.current || undefined,
        category: (cat && cat !== 'All') ? cat : undefined,
        limit: 50,
      });
      setProducts(data.items);
      if (typeof window !== 'undefined' && !searchRef.current) {
        try {
          sessionStorage.setItem(`${CACHE_PREFIX}${cat || 'All'}`, JSON.stringify(data.items));
        } catch {
          // Ignore quota errors
        }
      }
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
  }, [products.length]);

  useEffect(() => {
    if (!search) {
      const cached = getInitialCache(category);
      if (cached.length > 0) {
        setProducts(cached);
        setLoading(false);
      }
    }
  }, [category, search]);

  useEffect(() => {
    // Debounce search queries
    const timeoutId = setTimeout(() => {
      fetchProducts();
    }, search !== undefined ? 300 : 0);

    return () => {
      clearTimeout(timeoutId);
    };
  }, [search, category, fetchProducts]);

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
