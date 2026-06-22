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

  // If user is not admin, deny access
  if (!isAdmin) {
    return (
      <div className="page-container">
        <Header />
        <EmptyState
          icon="🔒"
          title="Access Denied"
          description="You do not have the required permissions to view the Seller Hub."
          action={{ label: 'Return to Shop', href: '/' }}
        />
      </div>
    );
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
