'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { getProduct, type Product } from '@/lib/api';
import { useCart } from '@/hooks/useCart';
import { triggerHaptic } from '@/lib/telegram';
import Header from '@/components/Header';
import EmptyState from '@/components/EmptyState';
import LoadingSkeleton from '@/components/LoadingSkeleton';
import QuantitySelector from '@/components/QuantitySelector';
import styles from './page.module.css';

export default function ProductDetailPage() {
  const router = useRouter();
  const { id } = useParams() as { id: string };
  const [product, setProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [quantity, setQuantity] = useState(1);
  const { addItem, getItemQuantity } = useCart();

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getProduct(id)
      .then((data) => {
        setProduct(data);
        setError(null);
      })
      .catch((err) => {
        setError(err.message || 'Product failed to load');
      })
      .finally(() => {
        setLoading(false);
      });
  }, [id]);

  if (loading) {
    return (
      <div className="page-container">
        <Header />
        <LoadingSkeleton type="detail" />
      </div>
    );
  }

  if (error || !product) {
    return (
      <div className="page-container">
        <Header />
        <EmptyState
          icon="⚠️"
          title="Product not found"
          description={error || 'The requested product could not be located.'}
          action={{ label: 'Return to Catalog', href: '/' }}
        />
      </div>
    );
  }

  const existingInCartQty = getItemQuantity(product.id);
  const maxAvailable = product.stock_quantity - existingInCartQty;
  const isOutOfStock = product.stock_quantity <= 0 || maxAvailable <= 0;

  const handleAddToCart = () => {
    if (isOutOfStock) return;
    triggerHaptic('medium');
    addItem(product, quantity);
    
    // Alert or redirect to cart
    triggerHaptic('notification', 'success');
    router.push('/');
  };

  return (
    <div className="page-container" style={{ paddingBottom: '120px' }}>
      <Header />
      
      <main className={styles.main}>
        {/* Floating Back Arrow */}
        <div className={styles.backButtonRow}>
          <Link href="/" className={styles.backButton}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="19" y1="12" x2="5" y2="12"></line>
              <polyline points="12 19 5 12 12 5"></polyline>
            </svg>
          </Link>
          <span className={styles.categoryLabel}>Product Detail</span>
        </div>

        {/* Product Image */}
        <div className={styles.imageWrapper}>
          {product.image_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={product.image_url} alt={product.name} className={styles.image} />
          ) : (
            <div className={styles.placeholder}>
              <span>🛍️</span>
            </div>
          )}
        </div>

        {/* Product Title and Price */}
        <div className={styles.details}>
          <div className={styles.titleRow}>
            <h1 className={styles.title}>{product.name}</h1>
            <span className={styles.price}>${Number(product.price).toFixed(2)}</span>
          </div>

          {/* Stock Tag */}
          <div className={styles.stockRow}>
            <span className={`${styles.stockBadge} ${isOutOfStock ? styles.out : styles.in}`}>
              {product.stock_quantity <= 0
                ? 'Out of Stock'
                : maxAvailable <= 0
                ? 'All in Cart'
                : `${product.stock_quantity} units available`}
            </span>
          </div>

          <hr className={styles.divider} />

          {/* Product Description */}
          <div className={styles.descriptionSection}>
            <h3>Description</h3>
            <p>{product.description || 'No detailed description available for this item.'}</p>
          </div>
        </div>
      </main>

      {/* Fixed Bottom Action Panel */}
      <div className={styles.bottomBar}>
        <div className={styles.bottomBarContainer}>
          {!isOutOfStock && (
            <div className={styles.quantitySection}>
              <span>Quantity:</span>
              <QuantitySelector
                value={quantity}
                max={maxAvailable}
                onChange={setQuantity}
              />
            </div>
          )}

          <button
            onClick={handleAddToCart}
            disabled={isOutOfStock}
            className={`btn-primary ${styles.actionBtn} ${isOutOfStock ? styles.disabled : ''}`}
          >
            {product.stock_quantity <= 0 ? (
              'Sold Out'
            ) : maxAvailable <= 0 ? (
              'Already in Cart'
            ) : (
              `Add to Cart • $${(Number(product.price) * quantity).toFixed(2)}`
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
