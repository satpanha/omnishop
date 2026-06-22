// ─── OmniShop TMA — Auth Utilities ───

import {
  authenticateTelegram,
  setAuthToken,
  getAuthToken,
  type UserInfo,
  type AuthResponse,
} from './api';
import { getInitData } from './telegram';

// ─── Module-level State ───

let currentUser: UserInfo | null = null;
let authPromise: Promise<AuthResponse | null> | null = null;

// ─── Public Functions ───

/**
 * Initialize authentication using Telegram initData.
 * Returns the auth response or null if authentication fails.
 */
export async function initAuth(initData: string): Promise<AuthResponse | null> {
  // Prevent duplicate auth calls
  if (authPromise) {
    return authPromise;
  }

  authPromise = (async () => {
    try {
      const response = await authenticateTelegram(initData);
      currentUser = response.user;
      setAuthToken(response.access_token);
      return response;
    } catch (error) {
      console.error('Authentication failed:', error);
      currentUser = null;
      setAuthToken(null);
      return null;
    } finally {
      authPromise = null;
    }
  })();

  return authPromise;
}

/**
 * Try to authenticate automatically from Telegram context.
 */
export async function autoAuth(): Promise<AuthResponse | null> {
  const initData = getInitData();
  if (!initData) {
    // Try loading from stored token
    const token = getAuthToken();
    if (token) {
      // We have a stored token but no user info
      // In a real app, we'd validate the token with the server
      return null;
    }
    return null;
  }
  return initAuth(initData);
}

/**
 * Get the current authenticated user.
 */
export function getUser(): UserInfo | null {
  return currentUser;
}

/**
 * Set user manually (useful for dev/testing).
 */
export function setUser(user: UserInfo | null): void {
  currentUser = user;
}

/**
 * Check if the current user has admin privileges.
 */
export function isAdmin(): boolean {
  return currentUser?.is_admin === true;
}

/**
 * Clear auth state and log out.
 */
export function logout(): void {
  currentUser = null;
  setAuthToken(null);
  authPromise = null;
}

/**
 * Check if the user is currently authenticated.
 */
export function isAuthenticated(): boolean {
  return currentUser !== null || getAuthToken() !== null;
}
