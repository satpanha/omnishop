'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import { isTelegramEnvironment, signalReady, expandViewport, setHeaderColor } from '@/lib/telegram';
import { useAuth } from '@/hooks/useAuth';
import { setUser } from '@/lib/auth';

interface TelegramContextType {
  isReady: boolean;
  isInTelegram: boolean;
}

const TelegramContext = createContext<TelegramContextType>({
  isReady: false,
  isInTelegram: false,
});

export const useTelegram = () => useContext(TelegramContext);

export default function TelegramProvider({ children }: { children: React.ReactNode }) {
  const [isReady, setIsReady] = useState(false);
  const [isInTelegram, setIsInTelegram] = useState(false);
  const { authenticate } = useAuth();

  useEffect(() => {
    const isTg = isTelegramEnvironment();
    setIsInTelegram(isTg);

    if (isTg) {
      // Initialize Telegram App
      signalReady();
      expandViewport();
      setHeaderColor('#1a1a2e'); // match dark theme bg

      // Authenticate with Telegram backend
      authenticate().then(() => {
        setIsReady(true);
      });
    } else {
      // Development/Local browser fallback
      console.log('Running outside of Telegram. Mocking session for testing.');
      
      // Auto-set a mock admin user for local preview
      if (process.env.NODE_ENV === 'development') {
        setUser({
          telegram_id: 123456789,
          first_name: 'Store',
          last_name: 'Owner',
          username: 'admin',
          is_admin: true,
        });
      }
      setIsReady(true);
    }
  }, [authenticate]);

  return (
    <TelegramContext.Provider value={{ isReady, isInTelegram }}>
      {isReady ? children : (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100vh',
          background: '#1a1a2e',
          color: '#eaeaea',
          fontFamily: 'system-ui, sans-serif'
        }}>
          <div className="shimmer" style={{ width: '40px', height: '40px', borderRadius: '50%', marginBottom: '16px' }} />
          <span>Syncing with Telegram...</span>
        </div>
      )}
    </TelegramContext.Provider>
  );
}
