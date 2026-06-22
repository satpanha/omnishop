'use client';

import React, { useEffect, useState } from 'react';
import { getTransactions, updateTransactionStatus, type Transaction } from '@/lib/api';
import { triggerHaptic } from '@/lib/telegram';
import StatusBadge from '@/components/StatusBadge';
import LoadingSkeleton from '@/components/LoadingSkeleton';
import EmptyState from '@/components/EmptyState';
import styles from './page.module.css';

const TABS = ['all', 'pending', 'paid', 'cancelled'];

export default function AdminOrders() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('all');

  const fetchOrders = () => {
    setLoading(true);
    // Request with status filter if activeTab is not 'all'
    const filterStatus = activeTab === 'all' ? undefined : activeTab;
    getTransactions({ status: filterStatus, limit: 100 })
      .then((res) => {
        setTransactions(res.items);
        setError(null);
      })
      .catch((err) => {
        setError(err.message || 'Failed to load transactions');
      })
      .finally(() => {
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchOrders();
  }, [activeTab]);

  const handleStatusChange = async (id: string, newStatus: 'pending' | 'paid' | 'cancelled') => {
    triggerHaptic('medium');
    try {
      await updateTransactionStatus(id, newStatus);
      triggerHaptic('notification', 'success');
      // Optimistic state update or full refetch
      fetchOrders();
    } catch (err: any) {
      triggerHaptic('notification', 'error');
      alert(err.message || 'Failed to update order status');
    }
  };

  return (
    <div className="fade-in">
      <h1 className={styles.heading}>Transactions</h1>

      {/* Filter Tabs */}
      <div className={styles.tabsRow}>
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`${styles.tabBtn} ${activeTab === tab ? styles.active : ''}`}
          >
            {tab.toUpperCase()}
          </button>
        ))}
      </div>

      {loading ? (
        <LoadingSkeleton type="list" count={4} />
      ) : error ? (
        <EmptyState icon="⚠️" title="Error Loading Orders" description={error} />
      ) : transactions.length === 0 ? (
        <EmptyState
          icon="🧾"
          title="No Orders Found"
          description={activeTab === 'all' ? 'No orders have been recorded yet.' : `No orders match filter "${activeTab}".`}
        />
      ) : (
        <div className={styles.ordersContainer}>
          {transactions.map((tx) => (
            <div key={tx.id} className={`${styles.orderCard} glass-card`}>
              <div className={styles.orderHeader}>
                <div className={styles.orderTitle}>
                  <span className={styles.orderId}>#{tx.id.substring(0, 8)}</span>
                  <span className={styles.platformBadge}>
                    {tx.buyer_platform === 'telegram' ? '✈️ Telegram' : '📸 Instagram'}
                  </span>
                </div>
                <StatusBadge status={tx.status} />
              </div>

              <div className={styles.orderBody}>
                <div className={styles.bodyRow}>
                  <span className={styles.label}>Buyer ID</span>
                  <code className={styles.value}>{tx.buyer_id}</code>
                </div>
                
                <div className={styles.bodyRow}>
                  <span className={styles.label}>Quantity</span>
                  <span className={styles.value}>{tx.quantity} units</span>
                </div>

                <div className={styles.bodyRow}>
                  <span className={styles.label}>Total Price</span>
                  <span className={styles.totalPrice}>${Number(tx.total_price).toFixed(2)}</span>
                </div>

                <div className={styles.bodyRow}>
                  <span className={styles.label}>Ordered On</span>
                  <span className={styles.value}>
                    {new Date(tx.created_at).toLocaleString()}
                  </span>
                </div>
              </div>

              {/* Status Action Buttons */}
              <div className={styles.orderActions}>
                {tx.status === 'pending' && (
                  <>
                    <button
                      onClick={() => handleStatusChange(tx.id, 'paid')}
                      className={`${styles.btnAction} ${styles.btnPaid}`}
                    >
                      ✓ Mark Paid
                    </button>
                    <button
                      onClick={() => handleStatusChange(tx.id, 'cancelled')}
                      className={`${styles.btnAction} ${styles.btnCancel}`}
                    >
                      ✕ Cancel Order
                    </button>
                  </>
                )}
                {tx.status === 'paid' && (
                  <button
                    onClick={() => handleStatusChange(tx.id, 'cancelled')}
                    className={`${styles.btnAction} ${styles.btnCancel} w-full`}
                  >
                    ✕ Cancel Order & Restock
                  </button>
                )}
                {tx.status === 'cancelled' && (
                  <button
                    onClick={() => handleStatusChange(tx.id, 'pending')}
                    className={`${styles.btnAction} ${styles.btnRestore} w-full`}
                  >
                    ↺ Restore Order
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
