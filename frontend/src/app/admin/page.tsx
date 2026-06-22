'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { getProducts, getTransactions, type Product, type Transaction } from '@/lib/api';
import StatusBadge from '@/components/StatusBadge';
import LoadingSkeleton from '@/components/LoadingSkeleton';
import styles from './page.module.css';

export default function AdminDashboard() {
  const [productsCount, setProductsCount] = useState(0);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      getProducts({ limit: 1 }), // just to get total count
      getTransactions({ limit: 10 }) // get recent transactions
    ])
      .then(([productsRes, transactionsRes]) => {
        setProductsCount(productsRes.total);
        setTransactions(transactionsRes.items);
        setError(null);
      })
      .catch((err) => {
        setError(err.message || 'Failed to fetch dashboard statistics');
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  if (loading) {
    return <LoadingSkeleton type="list" count={4} />;
  }

  if (error) {
    return (
      <div className={styles.errorAlert}>
        <span>⚠️ {error}</span>
      </div>
    );
  }

  // Calculate quick metrics
  const totalOrders = transactions.length;
  const pendingOrders = transactions.filter((t) => t.status === 'pending').length;
  const revenue = transactions
    .filter((t) => t.status === 'paid')
    .reduce((sum, t) => sum + Number(t.total_price), 0);

  return (
    <div className="fade-in">
      <h1 className={styles.heading}>Seller Dashboard</h1>

      {/* Grid Metrics cards */}
      <div className={styles.statsGrid}>
        <div className={`${styles.statCard} glass-card`}>
          <span className={styles.statIcon}>📦</span>
          <span className={styles.statVal}>{productsCount}</span>
          <span className={styles.statLabel}>Products</span>
        </div>

        <div className={`${styles.statCard} glass-card`}>
          <span className={styles.statIcon}>🕒</span>
          <span className={styles.statVal}>{pendingOrders}</span>
          <span className={styles.statLabel}>Pending Orders</span>
        </div>

        <div className={`${styles.statCard} glass-card`}>
          <span className={styles.statIcon}>💰</span>
          <span className={styles.statVal}>${revenue.toFixed(2)}</span>
          <span className={styles.statLabel}>Revenue (Paid)</span>
        </div>

        <div className={`${styles.statCard} glass-card`}>
          <span className={styles.statIcon}>🧾</span>
          <span className={styles.statVal}>{totalOrders}</span>
          <span className={styles.statLabel}>Total Orders</span>
        </div>
      </div>

      {/* Recent Orders List */}
      <section className={styles.recentSection}>
        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>Recent Orders</h2>
          <Link href="/admin/orders" className={styles.viewAllLink}>
            View All →
          </Link>
        </div>

        {transactions.length === 0 ? (
          <div className={styles.emptyCard}>
            <p>No orders recorded yet.</p>
          </div>
        ) : (
          <div className={styles.ordersList}>
            {transactions.slice(0, 5).map((tx) => (
              <div key={tx.id} className={`${styles.orderItem} glass-card`}>
                <div className={styles.orderMeta}>
                  <span className={styles.orderId}>ID: #{tx.id.substring(0, 8)}</span>
                  <span className={styles.orderTime}>
                    {new Date(tx.created_at).toLocaleDateString()}
                  </span>
                </div>

                <div className={styles.orderDetail}>
                  <span>{tx.quantity} items</span>
                  <span className={styles.orderPrice}>${Number(tx.total_price).toFixed(2)}</span>
                </div>

                <div className={styles.orderStatus}>
                  <StatusBadge status={tx.status} />
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
