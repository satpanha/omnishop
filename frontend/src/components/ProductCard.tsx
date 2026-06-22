'use client';

import React from 'react';
import Link from 'next/link';
import type { Product } from '@/lib/api';
import { triggerHaptic } from '@/lib/telegram';
import styles from './ProductCard.module.css';

interface ProductCardProps {
  product: Product;
  onAddToCart: (product: Product, e: React.MouseEvent) => void;
}

export default function ProductCard({ product, onAddToCart }: ProductCardProps) {
  const isOutOfStock = product.stock_quantity <= 0;

  const handleAddClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isOutOfStock) {
      triggerHaptic('light');
      onAddToCart(product, e);
    }
  };

  return (
    <Link href={`/product/${product.id}`} className={`${styles.card} glass-card fade-in`}>
      <div className={styles.imageContainer}>
        {product.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={product.image_url}
            alt={product.name}
            className={styles.image}
            loading="lazy"
          />
        ) : (
          <div className={styles.placeholder}>
            <span>🛍️</span>
          </div>
        )}
        
        <span className={`${styles.stockBadge} ${isOutOfStock ? styles.out : styles.in}`}>
          {isOutOfStock ? 'Sold Out' : `${product.stock_quantity} left`}
        </span>
      </div>

      <div className={styles.content}>
        <h3 className={styles.title}>{product.name}</h3>
        <p className={styles.description}>{product.description || 'No description available.'}</p>
        
        <div className={styles.footer}>
          <span className={styles.price}>${Number(product.price).toFixed(2)}</span>
          
          <button
            onClick={handleAddClick}
            disabled={isOutOfStock}
            className={`${styles.addButton} ${isOutOfStock ? styles.disabled : ''}`}
            aria-label="Add to cart"
          >
            {isOutOfStock ? (
              'Sold Out'
            ) : (
              <>
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <line x1="12" y1="5" x2="12" y2="19" />
                  <line x1="5" y1="12" x2="19" y2="12" />
                </svg>
                <span>Add</span>
              </>
            )}
          </button>
        </div>
      </div>
    </Link>
  );
}
