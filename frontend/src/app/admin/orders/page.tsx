'use client';

/**
 * Admin Orders page.
 *
 * Displays the full OmniBot order list using the new /api/v1/orders endpoint.
 * Each card shows:
 *   • Order ID, platform, buyer, status badge
 *   • Line items with quantities
 *   • Payment info (KHQR / ABA link)
 *   • Delivery address + ETA
 *   • Action buttons that drive the fulfillment state machine
 */

import React, { useEffect, useState } from 'react';
import {
  listOrders,
  updateOrderStatus,
  type Order,
  type OrderStatus,
} from '@/lib/api';
import { triggerHaptic } from '@/lib/telegram';
import StatusBadge from '@/components/StatusBadge';
import LoadingSkeleton from '@/components/LoadingSkeleton';
import EmptyState from '@/components/EmptyState';
import styles from './page.module.css';

// All statuses available as filter tabs.
const TABS: { value: string; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'awaiting_payment', label: '⏳ Awaiting Payment' },
  { value: 'paid', label: '💰 Paid' },
  { value: 'preparing', label: '👨‍🍳 Preparing' },
  { value: 'dispatched', label: '🚴 Dispatched' },
  { value: 'delivered', label: '✅ Delivered' },
  { value: 'cancelled', label: '❌ Cancelled' },
];

// Fulfillment actions available per status.
const ACTIONS: Record<string, { label: string; target: OrderStatus; cls: string }[]> = {
  awaiting_payment: [
    { label: '💰 Mark Paid', target: 'paid', cls: styles.btnPaid },
    { label: '❌ Cancel', target: 'cancelled', cls: styles.btnCancel },
  ],
  paid: [
    { label: '👨‍🍳 Start Preparing', target: 'preparing', cls: styles.btnPrimary },
    { label: '🚴 Dispatch', target: 'dispatched', cls: styles.btnPrimary },
    { label: '❌ Cancel', target: 'cancelled', cls: styles.btnCancel },
  ],
  preparing: [
    { label: '🚴 Dispatch', target: 'dispatched', cls: styles.btnPrimary },
    { label: '❌ Cancel', target: 'cancelled', cls: styles.btnCancel },
  ],
  dispatched: [
    { label: '✅ Mark Delivered', target: 'delivered', cls: styles.btnPaid },
  ],
};

export default function AdminOrders() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('all');

  const fetchOrders = () => {
    setLoading(true);
    const params = activeTab === 'all' ? { limit: 100 } : { status: activeTab, limit: 100 };
    listOrders(params)
      .then((res) => {
        setOrders(res.items);
        setError(null);
      })
      .catch((err) => {
        setError(err.message || 'Failed to load orders');
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchOrders();
  }, [activeTab]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleAction = async (order: Order, target: OrderStatus) => {
    triggerHaptic('medium');
    try {
      await updateOrderStatus(order.id, { status: target });
      triggerHaptic('notification', 'success');
      fetchOrders();
    } catch (err: unknown) {
      triggerHaptic('notification', 'error');
      const msg = err instanceof Error ? err.message : 'Failed to update order';
      alert(msg);
    }
  };

  return (
    <div className="fade-in">
      <h1 className={styles.heading}>Orders</h1>

      {/* Filter tabs */}
      <div className={styles.tabsRow}>
        {TABS.map((tab) => (
          <button
            key={tab.value}
            id={`tab-${tab.value}`}
            onClick={() => setActiveTab(tab.value)}
            className={`${styles.tabBtn} ${activeTab === tab.value ? styles.active : ''}`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {loading ? (
        <LoadingSkeleton type="list" count={4} />
      ) : error ? (
        <EmptyState icon="⚠️" title="Error Loading Orders" description={error} />
      ) : orders.length === 0 ? (
        <EmptyState
          icon="🧾"
          title="No Orders Found"
          description={
            activeTab === 'all'
              ? 'No orders have been placed yet.'
              : `No orders match filter "${activeTab}".`
          }
        />
      ) : (
        <div className={styles.ordersContainer}>
          {orders.map((order) => (
            <div key={order.id} className={`${styles.orderCard} glass-card`}>
              {/* Header row */}
              <div className={styles.orderHeader}>
                <div className={styles.orderTitle}>
                  <span className={styles.orderId}>#{order.id.substring(0, 8)}</span>
                  <span className={styles.platformBadge}>
                    {order.buyer_platform === 'telegram' ? '✈️ TG' : '📸 IG'}
                  </span>
                </div>
                <StatusBadge status={order.status} />
              </div>

              {/* Buyer info */}
              <div className={styles.orderBody}>
                <div className={styles.bodyRow}>
                  <span className={styles.label}>Buyer</span>
                  <code className={styles.value}>{order.buyer_id}</code>
                </div>

                {/* Line items */}
                {order.line_items.length > 0 && (
                  <div className={styles.bodyRow}>
                    <span className={styles.label}>Items</span>
                    <div className={styles.lineItems}>
                      {order.line_items.map((li) => (
                        <span key={li.id} className={styles.lineItem}>
                          ×{li.quantity} — ${Number(li.total_price).toFixed(2)}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Total */}
                <div className={styles.bodyRow}>
                  <span className={styles.label}>Total</span>
                  <span className={styles.totalPrice}>
                    {order.currency} {Number(order.total_amount).toFixed(2)}
                  </span>
                </div>

                {/* Delivery */}
                {order.delivery_address && (
                  <div className={styles.bodyRow}>
                    <span className={styles.label}>Delivery</span>
                    <span className={styles.value}>{order.delivery_address}</span>
                  </div>
                )}
                {order.eta_minutes != null && (
                  <div className={styles.bodyRow}>
                    <span className={styles.label}>ETA</span>
                    <span className={styles.value}>~{order.eta_minutes} min</span>
                  </div>
                )}
                {order.distance_km && (
                  <div className={styles.bodyRow}>
                    <span className={styles.label}>Distance</span>
                    <span className={styles.value}>{Number(order.distance_km).toFixed(1)} km</span>
                  </div>
                )}

                {/* Payment */}
                {order.payment && (
                  <>
                    <div className={styles.bodyRow}>
                      <span className={styles.label}>Payment</span>
                      <StatusBadge status={order.payment.status} />
                    </div>
                    {order.payment.aba_link && (
                      <div className={styles.bodyRow}>
                        <span className={styles.label}>ABA Link</span>
                        <a
                          href={order.payment.aba_link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className={styles.abaLink}
                        >
                          Open →
                        </a>
                      </div>
                    )}
                  </>
                )}

                {/* Ordered at */}
                <div className={styles.bodyRow}>
                  <span className={styles.label}>Ordered</span>
                  <span className={styles.value}>
                    {new Date(order.created_at).toLocaleString()}
                  </span>
                </div>
              </div>

              {/* Action buttons */}
              {ACTIONS[order.status] && (
                <div className={styles.orderActions}>
                  {ACTIONS[order.status].map((act) => (
                    <button
                      key={act.target}
                      id={`order-${order.id.substring(0, 8)}-${act.target}`}
                      onClick={() => handleAction(order, act.target)}
                      className={`${styles.btnAction} ${act.cls}`}
                    >
                      {act.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
