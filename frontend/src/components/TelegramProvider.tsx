'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import { isTelegramEnvironment, signalReady, expandViewport, setHeaderColor } from '@/lib/telegram';
import { useAuth } from '@/hooks/useAuth';
import { setUser, initAuth } from '@/lib/auth';

interface TelegramContextType {
  isReady: boolean;
  isInTelegram: boolean;
  authError: string | null;
}

const TelegramContext = createContext<TelegramContextType>({
  isReady: false,
  isInTelegram: false,
  authError: null,
});

export const useTelegram = () => useContext(TelegramContext);

export default function TelegramProvider({ children }: { children: React.ReactNode }) {
  const [isReady, setIsReady] = useState(false);
  const [isInTelegram, setIsInTelegram] = useState(false);
  const { authenticate, error } = useAuth();

  useEffect(() => {
    const isTg = isTelegramEnvironment();
    setIsInTelegram(isTg);

    if (isTg) {
      // Signal to Telegram native client immediately so splash screen dismisses
      signalReady();
      expandViewport();
      setHeaderColor('#1a1a2e'); // match dark theme bg

      // Allow UI to mount immediately; authenticate in the background
      setIsReady(true);
      authenticate().catch((err) => {
        console.warn('Background Telegram authentication pending/failed:', err);
      });
    } else {
      // Development/Local browser fallback
      console.log('Running outside of Telegram.');
      setIsReady(true);
    }
  }, [authenticate]);

  return (
    <TelegramContext.Provider value={{ isReady, isInTelegram, authError: error }}>
      {children}
    </TelegramContext.Provider>
  );
}
