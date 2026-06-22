// ─── OmniShop TMA — Telegram Mini App Helpers ───

/* eslint-disable @typescript-eslint/no-explicit-any */

// ─── Type Declarations ───

interface TelegramWebApp {
  initData: string;
  initDataUnsafe: {
    query_id?: string;
    user?: {
      id: number;
      is_bot?: boolean;
      first_name: string;
      last_name?: string;
      username?: string;
      language_code?: string;
      is_premium?: boolean;
    };
    auth_date: number;
    hash: string;
  };
  version: string;
  platform: string;
  colorScheme: 'light' | 'dark';
  themeParams: {
    bg_color?: string;
    text_color?: string;
    hint_color?: string;
    link_color?: string;
    button_color?: string;
    button_text_color?: string;
    secondary_bg_color?: string;
  };
  isExpanded: boolean;
  viewportHeight: number;
  viewportStableHeight: number;
  headerColor: string;
  backgroundColor: string;
  isClosingConfirmationEnabled: boolean;
  ready: () => void;
  expand: () => void;
  close: () => void;
  enableClosingConfirmation: () => void;
  disableClosingConfirmation: () => void;
  setHeaderColor: (color: string) => void;
  setBackgroundColor: (color: string) => void;
  showPopup: (params: {
    title?: string;
    message: string;
    buttons?: Array<{
      id?: string;
      type?: 'default' | 'ok' | 'close' | 'cancel' | 'destructive';
      text?: string;
    }>;
  }, callback?: (buttonId: string) => void) => void;
  showAlert: (message: string, callback?: () => void) => void;
  showConfirm: (message: string, callback?: (ok: boolean) => void) => void;
  openLink: (url: string, options?: { try_instant_view?: boolean }) => void;
  openTelegramLink: (url: string) => void;
  HapticFeedback: {
    impactOccurred: (style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft') => void;
    notificationOccurred: (type: 'error' | 'success' | 'warning') => void;
    selectionChanged: () => void;
  };
  MainButton: {
    text: string;
    color: string;
    textColor: string;
    isVisible: boolean;
    isProgressVisible: boolean;
    isActive: boolean;
    setText: (text: string) => void;
    onClick: (callback: () => void) => void;
    offClick: (callback: () => void) => void;
    show: () => void;
    hide: () => void;
    enable: () => void;
    disable: () => void;
    showProgress: (leaveActive?: boolean) => void;
    hideProgress: () => void;
  };
  BackButton: {
    isVisible: boolean;
    onClick: (callback: () => void) => void;
    offClick: (callback: () => void) => void;
    show: () => void;
    hide: () => void;
  };
}

declare global {
  interface Window {
    Telegram?: {
      WebApp: TelegramWebApp;
    };
  }
}

// ─── Helper Functions ───

/**
 * Get the Telegram WebApp instance, if available.
 */
export function getTelegramWebApp(): TelegramWebApp | null {
  if (typeof window !== 'undefined' && window.Telegram?.WebApp) {
    return window.Telegram.WebApp;
  }
  return null;
}

/**
 * Check if we're running inside the Telegram Mini App environment.
 */
export function isTelegramEnvironment(): boolean {
  return getTelegramWebApp() !== null;
}

/**
 * Get the initData string from Telegram WebApp for authentication.
 */
export function getInitData(): string | null {
  try {
    const webapp = getTelegramWebApp();
    if (webapp && webapp.initData) {
      return webapp.initData;
    }
  } catch (error) {
    console.warn('Failed to get Telegram initData:', error);
  }
  return null;
}

/**
 * Get the current Telegram user info from initDataUnsafe.
 */
export function getTelegramUser() {
  try {
    const webapp = getTelegramWebApp();
    return webapp?.initDataUnsafe?.user || null;
  } catch {
    return null;
  }
}

/**
 * Expand the Mini App to full viewport height.
 */
export function expandViewport(): void {
  try {
    const webapp = getTelegramWebApp();
    if (webapp && !webapp.isExpanded) {
      webapp.expand();
    }
  } catch (error) {
    console.warn('Failed to expand viewport:', error);
  }
}

/**
 * Enable closing confirmation to prevent accidental closure.
 */
export function enableClosingConfirmation(): void {
  try {
    const webapp = getTelegramWebApp();
    webapp?.enableClosingConfirmation();
  } catch (error) {
    console.warn('Failed to enable closing confirmation:', error);
  }
}

/**
 * Set the header color of the Mini App.
 */
export function setHeaderColor(color: string): void {
  try {
    const webapp = getTelegramWebApp();
    webapp?.setHeaderColor(color);
  } catch (error) {
    console.warn('Failed to set header color:', error);
  }
}

/**
 * Set the background color of the Mini App.
 */
export function setBackgroundColor(color: string): void {
  try {
    const webapp = getTelegramWebApp();
    webapp?.setBackgroundColor(color);
  } catch (error) {
    console.warn('Failed to set background color:', error);
  }
}

/**
 * Trigger haptic feedback.
 */
export function hapticFeedback(
  type: 'impact' | 'notification' | 'selection',
  style?: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft' | 'error' | 'success' | 'warning'
): void {
  try {
    const webapp = getTelegramWebApp();
    if (!webapp?.HapticFeedback) return;

    switch (type) {
      case 'impact':
        webapp.HapticFeedback.impactOccurred(
          (style as 'light' | 'medium' | 'heavy' | 'rigid' | 'soft') || 'medium'
        );
        break;
      case 'notification':
        webapp.HapticFeedback.notificationOccurred(
          (style as 'error' | 'success' | 'warning') || 'success'
        );
        break;
      case 'selection':
        webapp.HapticFeedback.selectionChanged();
        break;
    }
  } catch (error) {
    console.warn('Haptic feedback failed:', error);
  }
}

/**
 * Show a native Telegram popup.
 */
export function showPopup(
  title: string,
  message: string,
  buttons?: Array<{ id?: string; type?: 'default' | 'ok' | 'close' | 'cancel' | 'destructive'; text?: string }>
): Promise<string> {
  return new Promise((resolve) => {
    try {
      const webapp = getTelegramWebApp();
      if (webapp) {
        webapp.showPopup(
          { title, message, buttons: buttons || [{ type: 'ok' }] },
          (buttonId: string) => resolve(buttonId)
        );
      } else {
        // Fallback for non-Telegram environments
        alert(`${title}\n\n${message}`);
        resolve('ok');
      }
    } catch {
      alert(`${title}\n\n${message}`);
      resolve('ok');
    }
  });
}

/**
 * Show a native Telegram alert.
 */
export function showAlert(message: string): Promise<void> {
  return new Promise((resolve) => {
    try {
      const webapp = getTelegramWebApp();
      if (webapp) {
        webapp.showAlert(message, () => resolve());
      } else {
        alert(message);
        resolve();
      }
    } catch {
      alert(message);
      resolve();
    }
  });
}

/**
 * Show a native Telegram confirm dialog.
 */
export function showConfirm(message: string): Promise<boolean> {
  return new Promise((resolve) => {
    try {
      const webapp = getTelegramWebApp();
      if (webapp) {
        webapp.showConfirm(message, (ok: boolean) => resolve(ok));
      } else {
        resolve(confirm(message));
      }
    } catch {
      resolve(confirm(message));
    }
  });
}

/**
 * Open an external link.
 */
export function openLink(url: string, tryInstantView: boolean = false): void {
  try {
    const webapp = getTelegramWebApp();
    if (webapp) {
      webapp.openLink(url, { try_instant_view: tryInstantView });
    } else {
      window.open(url, '_blank');
    }
  } catch {
    window.open(url, '_blank');
  }
}

/**
 * Signal to Telegram that the Mini App is ready.
 */
export function signalReady(): void {
  try {
    const webapp = getTelegramWebApp();
    webapp?.ready();
  } catch (error) {
    console.warn('Failed to signal ready:', error);
  }
}

/**
 * Convenience wrapper used throughout UI components.
 * Maps shorthand style strings to the correct HapticFeedback calls.
 *
 * @param style  'light' | 'medium' | 'heavy' (impact) OR 'notification' (first arg)
 * @param notifType  Used only when style === 'notification'
 */
export function triggerHaptic(
  style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft' | 'notification',
  notifType?: 'success' | 'error' | 'warning'
): void {
  if (style === 'notification') {
    hapticFeedback('notification', notifType ?? 'success');
  } else {
    hapticFeedback('impact', style);
  }
}
