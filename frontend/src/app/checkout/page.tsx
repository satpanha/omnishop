'use client';

/**
 * Checkout page — OmniBot order flow.
 *
 * Phases:
 *   review   → buyer reviews cart + optional delivery location picker
 *   placing  → order creation in flight
 *   paying   → PaymentQRPanel (KHQR + ABA Pay + 3s polling)
 *   success  → order paid / confirmed
 */

import React, { useCallback, useState } from 'react';
import Link from 'next/link';
import { useCart } from '@/hooks/useCart';
import {
  createOrder,
  type CreateOrderPayload,
  type DeliveryLocation,
  type Order,
  type OrderStatus,
} from '@/lib/api';
import { triggerHaptic } from '@/lib/telegram';
import Header from '@/components/Header';
import EmptyState from '@/components/EmptyState';
import DeliveryLocationPicker from '@/components/DeliveryLocationPicker';
import PaymentQRPanel from '@/components/PaymentQRPanel';
import styles from './page.module.css';

type Phase = 'review' | 'placing' | 'paying' | 'success';

export default function CheckoutPage() {
  const { items, totalPrice, clearCart } = useCart();

  const [phase, setPhase] = useState<Phase>('review');
  const [error, setError] = useState<string | null>(null);
  const [delivery, setDelivery] = useState<DeliveryLocation | null>(null);
  const [order, setOrder] = useState<Order | null>(null);
  const [paidStatus, setPaidStatus] = useState<OrderStatus | null>(null);

  // Called by PaymentQRPanel when the order transitions away from awaiting_payment.
  const handlePaymentStatusChange = useCallback((status: OrderStatus) => {
    setPaidStatus(status);
    setPhase('success');
  }, []);

  // ── Empty cart guard ────────────────────────────────────────────────
  if (items.length === 0 && phase === 'review') {
    return (
      <div className="page-container">
        <Header />
        <EmptyState
          icon="🛒"
          title="Checkout is empty"
          description="You don't have any items in your cart to order."
          action={{ label: 'Go to Catalogue', href: '/' }}
        />
      </div>
    );
  }

  // ── Handlers ─────────────────────────────────────────────────────────

  const handleConfirmOrder = async () => {
    setPhase('placing');
    setError(null);
    triggerHaptic('heavy');

    const payload: CreateOrderPayload = {
      items: items.map(({ product, quantity }) => ({
        product_id: product.id,
        quantity,
      })),
      idempotency_key: `cart-${Date.now()}`,
    };

    // Only include delivery if the buyer provided location or address.
    if (delivery && (delivery.address || (delivery.lat !== 0 && delivery.lng !== 0))) {
      payload.delivery = delivery;
    }

    try {
      const created = await createOrder(payload);
      setOrder(created);
      clearCart();
      triggerHaptic('notification', 'success');
      setPhase('paying');
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'An error occurred. Please try again.';
      triggerHaptic('notification', 'error');
      setError(message);
      setPhase('review');
    }
  };

  // ── Success view ─────────────────────────────────────────────────────
  if (phase === 'success' && order) {
    const isPaid = paidStatus === 'paid';
    return (
      <div className="page-container">
        <Header />
        <main className={styles.main}>
          <div className={`${styles.successCard} glass-card fade-in`}>
            <div className={styles.successIconWrapper}>
              <div className={styles.successIcon}>
                {isPaid ? (
                  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                ) : (
                  <span style={{ fontSize: '2.5rem' }}>📦</span>
                )}
              </div>
            </div>

            <h1 className={styles.successTitle}>
              {isPaid ? 'Payment Confirmed!' : 'Order Placed!'}
            </h1>
            <p className={styles.successDesc}>
              {isPaid
                ? 'Your payment has been received. The seller will prepare your order shortly.'
                : 'Your order has been placed. You\'ll receive payment instructions via Telegram.'}
            </p>

            {order.eta_minutes && (
              <p className={styles.etaBadge}>
                🛵 Estimated delivery: ~{order.eta_minutes} min
              </p>
            )}

            <div className={styles.orderSummaryBox}>
              <h3>Order Reference</h3>
              <code className={styles.orderId}>{order.id.substring(0, 8)}…</code>
            </div>

            <Link
              href="/"
              className="btn-primary w-full text-center block mt-6"
              style={{ textDecoration: 'none' }}
            >
              Continue Shopping
            </Link>
          </div>
        </main>
      </div>
    );
  }

  // ── Paying view (QR panel) ────────────────────────────────────────────
  if (phase === 'paying' && order) {
    return (
      <div className="page-container" style={{ paddingBottom: '40px' }}>
        <Header />
        <main className={styles.main}>
          <div className={styles.backButtonRow}>
            <span className={styles.categoryLabel}>Complete Payment</span>
          </div>

          <div className={`${styles.orderCard} glass-card`}>
            <h2 className={styles.sectionTitle}>Your Order</h2>
            <div className={styles.itemsList}>
              {order.line_items.map((li) => (
                <div key={li.id} className={styles.itemRow}>
                  <span className={styles.itemName}>
                    Item ×{li.quantity}
                  </span>
                  <span className={styles.itemPrice}>
                    ${Number(li.total_price).toFixed(2)}
                  </span>
                </div>
              ))}
            </div>
            <hr className={styles.divider} />
            <div className={styles.totalRow}>
              <span>Total</span>
              <span className={styles.totalPrice}>
                ${Number(order.total_amount).toFixed(2)}
              </span>
            </div>
          </div>

          <div className={`${styles.paymentCard} glass-card`}>
            <h2 className={styles.sectionTitle}>Pay Now</h2>
            <PaymentQRPanel
              order={order}
              onStatusChange={handlePaymentStatusChange}
            />
          </div>
        </main>
      </div>
    );
  }

  // ── Review view (default) ─────────────────────────────────────────────
  return (
    <div className="page-container" style={{ paddingBottom: '100px' }}>
      <Header />

      <main className={styles.main}>
        <div className={styles.backButtonRow}>
          <Link href="/" className={styles.backButton}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="19" y1="12" x2="5" y2="12" />
              <polyline points="12 19 5 12 12 5" />
            </svg>
          </Link>
          <span className={styles.categoryLabel}>Checkout Summary</span>
        </div>

        {error && (
          <div className={styles.errorAlert}>
            <span>⚠️ {error}</span>
          </div>
        )}

        {/* Order items */}
        <div className={`${styles.orderCard} glass-card`}>
          <h2 className={styles.sectionTitle}>Items</h2>
          <div className={styles.itemsList}>
            {items.map(({ product, quantity }) => (
              <div key={product.id} className={styles.itemRow}>
                <div className={styles.itemMeta}>
                  <span className={styles.itemName}>{product.name}</span>
                  <span className={styles.itemQty}>Qty: {quantity}</span>
                </div>
                <span className={styles.itemPrice}>
                  ${(Number(product.price) * quantity).toFixed(2)}
                </span>
              </div>
            ))}
          </div>

          <hr className={styles.divider} />

          <div className={styles.totalRow}>
            <span>Total amount</span>
            <span className={styles.totalPrice}>${totalPrice.toFixed(2)}</span>
          </div>
        </div>

        {/* Delivery location picker */}
        <div className={`${styles.orderCard} glass-card`}>
          <h2 className={styles.sectionTitle}>Delivery</h2>
          <DeliveryLocationPicker onChange={setDelivery} />
          {delivery?.address && delivery.lat !== 0 && (
            <p className={styles.etaHint}>📍 Location added — ETA will be estimated at checkout.</p>
          )}
        </div>

        {/* Payment note */}
        <div className={`${styles.paymentCard} glass-card`}>
          <h2 className={styles.sectionTitle}>Payment</h2>
          <p className={styles.paymentDesc}>
            After placing the order you&apos;ll receive a <b>KHQR code</b> and an
            &nbsp;<b>ABA Pay</b> link. Scan with any Cambodian banking app to complete
            payment instantly.
          </p>
        </div>

        {/* Confirm button */}
        <button
          id="confirm-order-btn"
          onClick={handleConfirmOrder}
          disabled={phase === 'placing'}
          className={`btn-primary ${styles.submitBtn} ${phase === 'placing' ? styles.disabled : ''}`}
        >
          {phase === 'placing' ? 'Placing Order…' : 'Place Order & Pay'}
        </button>
      </main>
    </div>
  );
}
