'use client';

import React, { useEffect, useRef } from 'react';
import Link from 'next/link';
import { useCart } from '@/hooks/useCart';
import { triggerHaptic } from '@/lib/telegram';
import QuantitySelector from './QuantitySelector';
import styles from './CartDrawer.module.css';

interface CartDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function CartDrawer({ isOpen, onClose }: CartDrawerProps) {
  const { items, updateQuantity, removeItem, totalPrice, totalItems } = useCart();
  const drawerRef = useRef<HTMLDivElement>(null);

  // Close on ESC keypress
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };

    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden'; // prevent background scrolling
    }

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleCheckoutClick = () => {
    triggerHaptic('medium');
    onClose();
  };

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div
        className={`${styles.drawer} slide-up`}
        onClick={(e) => e.stopPropagation()}
        ref={drawerRef}
      >
        <div className={styles.header}>
          <div className={styles.handle} onClick={onClose} />
          <div className={styles.headerContent}>
            <h2 className={styles.title}>Your Shopping Cart</h2>
            <span className={styles.itemCount}>{totalItems} items</span>
          </div>
          <button className={styles.closeButton} onClick={onClose}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>

        <div className={styles.body}>
          {items.length === 0 ? (
            <div className={styles.emptyState}>
              <span className={styles.emptyIcon}>🛒</span>
              <h3>Your cart is empty</h3>
              <p>Add some products from the catalogue to get started.</p>
              <button className="btn-primary" onClick={onClose}>
                Browse Products
              </button>
            </div>
          ) : (
            <div className={styles.itemList}>
              {items.map(({ product, quantity }) => (
                <div key={product.id} className={styles.itemRow}>
                  <div className={styles.itemImage}>
                    {product.image_url ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={product.image_url} alt={product.name} />
                    ) : (
                      <span>🛍️</span>
                    )}
                  </div>
                  
                  <div className={styles.itemDetails}>
                    <h4 className={styles.itemName}>{product.name}</h4>
                    <span className={styles.itemPrice}>${Number(product.price).toFixed(2)}</span>
                  </div>

                  <div className={styles.actions}>
                    <QuantitySelector
                      value={quantity}
                      max={product.stock_quantity}
                      onChange={(val) => updateQuantity(product.id, val)}
                    />
                    <button
                      onClick={() => removeItem(product.id)}
                      className={styles.removeButton}
                      aria-label="Remove item"
                    >
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                      </svg>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {items.length > 0 && (
          <div className={styles.footer}>
            <div className={styles.priceSummary}>
              <span>Subtotal</span>
              <span className={styles.totalAmount}>${totalPrice.toFixed(2)}</span>
            </div>
            
            <Link
              href="/checkout"
              onClick={handleCheckoutClick}
              className="btn-primary text-center font-semibold text-lg w-full block"
              style={{ textDecoration: 'none' }}
            >
              Proceed to Checkout
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
