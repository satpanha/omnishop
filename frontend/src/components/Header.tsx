'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useCart } from '@/hooks/useCart';
import { useAuth } from '@/hooks/useAuth';
import styles from './Header.module.css';

interface HeaderProps {
  onCartClick?: () => void;
}

export default function Header({ onCartClick }: HeaderProps) {
  const pathname = usePathname();
  const { totalItems } = useCart();
  const { isAdmin } = useAuth();

  const isStorefront = !pathname.startsWith('/admin');

  return (
    <header className={styles.header}>
      <div className={styles.container}>
        <Link href="/" className={styles.logoLink}>
          <span className="gradient-text font-bold">OmniShop</span>
        </Link>

        <nav className={styles.nav}>
          {isAdmin && (
            <Link
              href={isStorefront ? '/admin' : '/'}
              className={`${styles.navLink} btn-secondary`}
            >
              {isStorefront ? 'Seller Hub' : 'Storefront'}
            </Link>
          )}

          {isStorefront && onCartClick && (
            <button
              onClick={onCartClick}
              className={styles.cartButton}
              aria-label="Shopping Cart"
            >
              <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <circle cx="9" cy="21" r="1" />
                <circle cx="20" cy="21" r="1" />
                <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6" />
              </svg>
              {totalItems > 0 && (
                <span className={`${styles.badge} pulse`}>
                  {totalItems}
                </span>
              )}
            </button>
          )}
        </nav>
      </div>
    </header>
  );
}
