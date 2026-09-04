// ─── OmniShop TMA — Auth Utilities ───

import {
  authenticateTelegram,
  guestLogin,
  adminLogin as apiAdminLogin,
  getMe,
  logoutApi,
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
  if (authPromise) {
    return authPromise;
  }

  authPromise = (async () => {
    const response = await authenticateTelegram(initData);
    currentUser = response.user;
    setAuthToken(response.access_token);
    return response;
  })();

  try {
    return await authPromise;
  } catch (error) {
    console.error('Authentication failed:', error);
    currentUser = null;
    setAuthToken(null);
    throw error;
  } finally {
    authPromise = null;
  }
}

/**
 * Log in directly using the admin password (desktop browser).
 */
export async function loginWithAdminPassword(password: string): Promise<AuthResponse> {
  const response = await apiAdminLogin(password);
  currentUser = response.user;
  setAuthToken(response.access_token);
  return response;
}

/**
 * Try to authenticate automatically from Telegram context or stored session,
 * falling back to a guest session so checkout is never blocked.
 */
export async function autoAuth(): Promise<AuthResponse | null> {
  const initData = getInitData();
  if (initData) {
    try {
      return await initAuth(initData);
    } catch (err) {
      console.warn('Telegram initData authentication failed, falling back to guest session:', err);
    }
  }

  // Outside Telegram or fallback: rehydrate from token/cookie
  const token = getAuthToken();
  if (token) {
    try {
      const userInfo = await getMe();
      currentUser = userInfo;
      return {
        access_token: token,
        token_type: 'bearer',
        user: userInfo,
      };
    } catch {
      currentUser = null;
      setAuthToken(null);
    }
  }

  // Fallback to guest session so purchasing is never blocked
  try {
    const guestResp = await guestLogin();
    currentUser = guestResp.user;
    setAuthToken(guestResp.access_token);
    return guestResp;
  } catch (guestErr) {
    console.error('Guest authentication failed:', guestErr);
    return null;
  }
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
export async function logout(): Promise<void> {
  currentUser = null;
  setAuthToken(null);
  authPromise = null;
  try {
    await logoutApi();
  } catch {
    // Silently ignore network failures on logout
  }
}

/**
 * Check if the user is currently authenticated.
 */
export function isAuthenticated(): boolean {
  return currentUser !== null || getAuthToken() !== null;
}
