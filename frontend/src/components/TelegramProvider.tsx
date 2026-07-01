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
      // Initialize Telegram App
      signalReady();
      expandViewport();
      setHeaderColor('#1a1a2e'); // match dark theme bg

      // Authenticate with Telegram backend
      authenticate().finally(() => {
        setIsReady(true);
      });
    } else {
      // Development/Local browser fallback
      console.log('Running outside of Telegram. Mocking session for testing.');
      
      // Auto-set a mock admin user for local preview and fetch mock JWT token
      if (process.env.NODE_ENV === 'development') {
        initAuth('mock_admin')
          .then(() => {
            console.log('Mock admin token retrieved successfully.');
          })
          .catch((err) => {
            console.error('Failed to get mock token:', err);
          })
          .finally(() => {
            setIsReady(true);
          });
      } else {
        setIsReady(true);
      }
    }
  }, [authenticate]);

  return (
    <TelegramContext.Provider value={{ isReady, isInTelegram, authError: error }}>
      {isReady ? (
        <>
          {error && (
            <div style={{
              background: '#5c1a1a',
              color: '#ff8a8a',
              padding: '12px 16px',
              textAlign: 'center',
              fontSize: '14px',
              fontFamily: 'system-ui, sans-serif',
              borderBottom: '1px solid #7a2a2a',
            }}>
              Auth error: {error}
            </div>
          )}
          {children}
        </>
      ) : (
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
          {error && (
            <span style={{ color: '#ff8a8a', marginTop: '12px', fontSize: '14px' }}>
              {error}
            </span>
          )}
        </div>
      )}
    </TelegramContext.Provider>
  );
}
