'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useCart } from '@/hooks/useCart';
import { createTransaction } from '@/lib/api';
import { triggerHaptic } from '@/lib/telegram';
import Header from '@/components/Header';
import EmptyState from '@/components/EmptyState';
import styles from './page.module.css';

export default function CheckoutPage() {
  const { items, totalPrice, clearCart } = useCart();
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createdOrderIds, setCreatedOrderIds] = useState<string[]>([]);

  if (success) {
    return (
      <div className="page-container">
        <Header />
        <main className={styles.main}>
          <div className={`${styles.successCard} glass-card fade-in`}>
            <div className={styles.successIconWrapper}>
              <div className={styles.successIcon}>
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                  <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
              </div>
            </div>
            
            <h1 className={styles.successTitle}>Order Placed!</h1>
            <p className={styles.successDesc}>
              Your order has been recorded successfully. The seller has been notified and will verify the details.
            </p>

            <div className={styles.orderSummaryBox}>
              <h3>Order ID(s)</h3>
              {createdOrderIds.map((id) => (
                <code key={id} className={styles.orderId}>{id.substring(0, 8)}...</code>
              ))}
            </div>

            <Link href="/" className="btn-primary w-full text-center block mt-6" style={{ textDecoration: 'none' }}>
              Continue Shopping
            </Link>
          </div>
        </main>
      </div>
    );
  }

  if (items.length === 0) {
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

  const handleConfirmOrder = async () => {
    setSubmitting(true);
    setError(null);
    triggerHaptic('heavy');

    try {
      const orderIds: string[] = [];
      // Call backend API sequentially or concurrently to place orders
      for (const item of items) {
        const transaction = await createTransaction(item.product.id, item.quantity);
        orderIds.push(transaction.id);
      }
      
      setCreatedOrderIds(orderIds);
      triggerHaptic('notification', 'success');
      setSuccess(true);
      clearCart();
    } catch (err: any) {
      triggerHaptic('notification', 'error');
      setError(err.message || 'An error occurred while placing your order. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="page-container" style={{ paddingBottom: '80px' }}>
      <Header />
      
      <main className={styles.main}>
        <div className={styles.backButtonRow}>
          <Link href="/" className={styles.backButton}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="19" y1="12" x2="5" y2="12"></line>
              <polyline points="12 19 5 12 12 5"></polyline>
            </svg>
          </Link>
          <span className={styles.categoryLabel}>Checkout Summary</span>
        </div>

        {error && (
          <div className={styles.errorAlert}>
            <span>⚠️ {error}</span>
          </div>
        )}

        {/* Order Items Summary */}
        <div className={`${styles.orderCard} glass-card`}>
          <h2 className={styles.sectionTitle}>Items Details</h2>
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
            <span>Total amount to pay</span>
            <span className={styles.totalPrice}>${totalPrice.toFixed(2)}</span>
          </div>
        </div>

        {/* Payment instructions */}
        <div className={`${styles.paymentCard} glass-card`}>
          <h2 className={styles.sectionTitle}>Payment Details</h2>
          <p className={styles.paymentDesc}>
            OmniShop uses <b>Manual Payment Verification</b>. Once you place the order, you can complete the payment in the chat window, or the seller will message you with the transfer information.
          </p>
        </div>

        {/* Submit button */}
        <button
          onClick={handleConfirmOrder}
          disabled={submitting}
          className={`btn-primary ${styles.submitBtn} ${submitting ? styles.disabled : ''}`}
        >
          {submitting ? 'Creating Order...' : 'Confirm Order'}
        </button>
      </main>
    </div>
  );
}
