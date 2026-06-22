'use client';

// ─── OmniShop TMA — Auth Hook ───

import { useState, useEffect, useCallback } from 'react';
import type { UserInfo } from '@/lib/api';
import { autoAuth, getUser, logout as logoutAuth, isAdmin as checkAdmin } from '@/lib/auth';
import { isTelegramEnvironment } from '@/lib/telegram';

interface UseAuthReturn {
  user: UserInfo | null;
  loading: boolean;
  isAdmin: boolean;
  error: string | null;
  authenticate: () => Promise<void>;
  logout: () => void;
}

export function useAuth(): UseAuthReturn {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const authenticate = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await autoAuth();
      if (response) {
        setUser(response.user);
      } else {
        // Check if we already have a user from a previous auth
        const existingUser = getUser();
        if (existingUser) {
          setUser(existingUser);
        }
      }
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Authentication failed';
      setError(message);
      console.error('Auth error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    logoutAuth();
    setUser(null);
    setError(null);
  }, []);

  // Auto-authenticate on mount if in Telegram
  useEffect(() => {
    if (isTelegramEnvironment()) {
      authenticate();
    } else {
      // Not in Telegram, skip auth
      setLoading(false);
    }
  }, [authenticate]);

  const isAdmin = user?.is_admin === true || checkAdmin();

  return {
    user,
    loading,
    isAdmin,
    error,
    authenticate,
    logout,
  };
}
