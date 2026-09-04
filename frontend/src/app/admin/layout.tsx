'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import Header from '@/components/Header';
import EmptyState from '@/components/EmptyState';
import styles from './layout.module.css';

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { isAdmin, loading } = useAuth();
  const pathname = usePathname();

  if (loading) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        background: '#1a1a2e',
        color: '#eaeaea'
      }}>
        <span>Loading Seller Hub...</span>
      </div>
    );
  }

  // If user is not admin, provide direct admin login
  if (!isAdmin) {
    return <AdminLoginForm />;
  }

  return (
    <div className="page-container" style={{ paddingBottom: '90px' }}>
      <Header />
      
      {/* Admin Subheader / Navigation Tab Bar */}
      <div className={styles.navBar}>
        <Link
          href="/admin"
          className={`${styles.navItem} ${pathname === '/admin' ? styles.active : ''}`}
        >
          📈 Stats
        </Link>
        <Link
          href="/admin/products"
          className={`${styles.navItem} ${pathname.startsWith('/admin/products') ? styles.active : ''}`}
        >
          📦 Inventory
        </Link>
        <Link
          href="/admin/orders"
          className={`${styles.navItem} ${pathname.startsWith('/admin/orders') ? styles.active : ''}`}
        >
          🛒 Orders
        </Link>
      </div>

      <main className={styles.main}>
        {children}
      </main>
    </div>
  );
}

function AdminLoginForm() {
  const { loginWithPassword } = useAuth();
  const [password, setPassword] = React.useState('');
  const [error, setError] = React.useState<string | null>(null);
  const [submitting, setSubmitting] = React.useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password) return;
    setError(null);
    setSubmitting(true);
    try {
      await loginWithPassword(password);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Invalid admin password');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="page-container">
      <Header />
      <div style={{
        maxWidth: '400px',
        margin: '60px auto',
        padding: '24px',
        background: 'rgba(255, 255, 255, 0.05)',
        borderRadius: '16px',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        backdropFilter: 'blur(10px)',
      }}>
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <span style={{ fontSize: '2.5rem' }}>🔐</span>
          <h2 style={{ margin: '12px 0 6px', color: '#fff' }}>Seller Hub Login</h2>
          <p style={{ color: 'rgba(255, 255, 255, 0.6)', fontSize: '14px', margin: 0 }}>
            Enter your admin password to access the operations console.
          </p>
        </div>

        {error && (
          <div style={{
            background: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            color: '#ef4444',
            padding: '10px 14px',
            borderRadius: '8px',
            fontSize: '13px',
            marginBottom: '16px',
          }}>
            ⚠️ {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', fontSize: '13px', marginBottom: '6px', color: 'rgba(255, 255, 255, 0.8)' }}>
              Admin Password
            </label>
            <input
              type="password"
              placeholder="Enter password..."
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              style={{
                width: '100%',
                padding: '12px',
                background: 'rgba(0, 0, 0, 0.3)',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                borderRadius: '8px',
                color: '#fff',
                fontSize: '15px',
                outline: 'none',
                boxSizing: 'border-box',
              }}
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="btn-primary"
            style={{ width: '100%', padding: '12px', fontSize: '15px', fontWeight: 600 }}
          >
            {submitting ? 'Logging In…' : 'Unlock Dashboard'}
          </button>
        </form>

        <div style={{ textAlign: 'center', marginTop: '20px' }}>
          <Link href="/" style={{ color: 'rgba(255, 255, 255, 0.5)', fontSize: '13px', textDecoration: 'none' }}>
            ← Return to Storefront
          </Link>
        </div>
      </div>
    </div>
  );
}
