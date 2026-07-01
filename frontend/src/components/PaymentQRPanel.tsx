/**
 * PaymentQRPanel
 *
 * Shows the KHQR QR code and ABA Pay button for an awaiting_payment order.
 * Polls `getOrder` every POLL_INTERVAL_MS until the order transitions to a
 * non-awaiting_payment state, then calls `onStatusChange` so the parent page
 * can react (show success, redirect, etc.).
 *
 * Design:
 *   • KHQR string is rendered as a QR code via the qrcode.react library
 *     (installed as a lightweight peer dep).
 *   • ABA Pay deep-link opens in a new tab / the native ABA app.
 *   • A subtle pulse animation on the QR box signals that the page is
 *     "live" waiting for the webhook.
 */
'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import type { Order, OrderStatus } from '@/lib/api';
import { getOrder } from '@/lib/api';
import styles from './PaymentQRPanel.module.css';

const POLL_INTERVAL_MS = 3000; // 3-second polling interval
const MAX_POLLS = 200; // stop after ~10 minutes

interface Props {
  order: Order;
  onStatusChange: (status: OrderStatus) => void;
}


export default function PaymentQRPanel({ order, onStatusChange }: Props) {
  const payment = order.payment;
  const [pollCount, setPollCount] = useState(0);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  // Start polling for payment status.
  useEffect(() => {
    if (order.status !== 'awaiting_payment') return;

    const tick = async () => {
      setPollCount((n) => {
        if (n >= MAX_POLLS) {
          stopPolling();
          return n;
        }
        return n + 1;
      });

      try {
        const refreshed = await getOrder(order.id);
        if (refreshed.status !== 'awaiting_payment') {
          stopPolling();
          onStatusChange(refreshed.status);
        }
      } catch {
        // Network error — keep polling silently.
      }
    };

    pollRef.current = setInterval(tick, POLL_INTERVAL_MS);
    return stopPolling;
  }, [order.id, order.status, onStatusChange, stopPolling]);

  if (!payment) {
    return (
      <div className={styles.noPayment}>
        <p>No payment record found. Please contact support.</p>
      </div>
    );
  }

  return (
    <div className={styles.panel}>
      <div className={styles.waitingRow}>
        <span className={styles.pulseDot} aria-hidden="true" />
        <span className={styles.waitingText}>Waiting for payment…</span>
      </div>

      {payment.khqr_string && (
        <div className={styles.qrWrapper}>
          <QRCodeSVG
            value={payment.khqr_string}
            size={200}
            bgColor="#ffffff"
            fgColor="#000000"
            level="M"
            className={styles.qrCanvas}
          />
          <p className={styles.scanHint}>Scan with any Cambodian banking app</p>
        </div>
      )}

      <div className={styles.amountRow}>
        <span className={styles.amountLabel}>Total due</span>
        <span className={styles.amountValue}>
          {payment.currency} {Number(payment.amount).toFixed(2)}
        </span>
      </div>

      {payment.khqr_string && (
        <details className={styles.khqrDetails}>
          <summary className={styles.khqrSummary}>Show KHQR string</summary>
          <code className={styles.khqrCode}>{payment.khqr_string}</code>
        </details>
      )}

      {payment.aba_link && (
        <a
          id="aba-pay-btn"
          href={payment.aba_link}
          target="_blank"
          rel="noopener noreferrer"
          className={styles.abaBtn}
        >
          💳 Pay with ABA
        </a>
      )}

      <p className={styles.autoNote}>
        This page updates automatically once payment is confirmed.
      </p>
    </div>
  );
}
