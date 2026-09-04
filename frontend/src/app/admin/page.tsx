'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { getProducts, listOrders, type Order } from '@/lib/api';
import StatusBadge from '@/components/StatusBadge';
import LoadingSkeleton from '@/components/LoadingSkeleton';
import styles from './page.module.css';

export default function AdminDashboard() {
  const [productsCount, setProductsCount] = useState(0);
  const [orders, setOrders] = useState<Order[]>([]);
  const [totalOrdersCount, setTotalOrdersCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      getProducts({ limit: 1 }), // just to get total count
      listOrders({ limit: 50 }) // get recent orders
    ])
      .then(([productsRes, ordersRes]) => {
        setProductsCount(productsRes.total);
        setOrders(ordersRes.items);
        setTotalOrdersCount(ordersRes.total);
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
  const totalOrders = totalOrdersCount;
  const pendingOrders = orders.filter((o) => o.status === 'awaiting_payment').length;
  const revenue = orders
    .filter((o) => ['paid', 'preparing', 'dispatched', 'delivered'].includes(o.status))
    .reduce((sum, o) => sum + Number(o.total_amount), 0);

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
          <span className={styles.statIcon}>⏳</span>
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

        {orders.length === 0 ? (
          <div className={styles.emptyCard}>
            <p>No orders recorded yet.</p>
          </div>
        ) : (
          <div className={styles.ordersList}>
            {orders.slice(0, 5).map((order) => {
              const itemCount = order.line_items?.reduce((sum, item) => sum + item.quantity, 0) ?? 0;
              return (
                <div key={order.id} className={`${styles.orderItem} glass-card`}>
                  <div className={styles.orderMeta}>
                    <span className={styles.orderId}>ID: #{order.id.substring(0, 8)}</span>
                    <span className={styles.orderTime}>
                      {new Date(order.created_at).toLocaleDateString()}
                    </span>
                  </div>

                  <div className={styles.orderDetail}>
                    <span>{itemCount} {itemCount === 1 ? 'item' : 'items'}</span>
                    <span className={styles.orderPrice}>
                      {order.currency === 'KHR' ? '៛' : '$'}{Number(order.total_amount).toFixed(2)}
                    </span>
                  </div>

                  <div className={styles.orderStatus}>
                    <StatusBadge status={order.status} />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
