'use client';

import React, { useState } from 'react';
import Header from '@/components/Header';
import ProductCard from '@/components/ProductCard';
import CartDrawer from '@/components/CartDrawer';
import EmptyState from '@/components/EmptyState';
import LoadingSkeleton from '@/components/LoadingSkeleton';
import { useProducts } from '@/hooks/useProducts';
import { useCart } from '@/hooks/useCart';
import styles from './page.module.css';

const CATEGORIES = ['All', 'Popular', 'New Arrival', 'Sale'];

export default function StorefrontHome() {
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [isCartOpen, setIsCartOpen] = useState(false);
  
  const { products, loading, error } = useProducts(search);
  const { addItem } = useCart();

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearch(e.target.value);
  };

  return (
    <div className="page-container">
      <Header onCartClick={() => setIsCartOpen(true)} />
      
      <main className={styles.main}>
        {/* Search Bar */}
        <div className={styles.searchSection}>
          <div className={styles.searchWrapper}>
            <svg
              className={styles.searchIcon}
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
            <input
              type="text"
              placeholder="Search products..."
              value={search}
              onChange={handleSearchChange}
              className={styles.searchInput}
            />
          </div>
        </div>

        {/* Categories Scroller */}
        <div className={styles.categoryScroll}>
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`${styles.categoryPill} ${
                selectedCategory === cat ? styles.active : ''
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Catalog Section */}
        <section className={styles.catalog}>
          <h2 className="section-title">Product Catalogue</h2>
          
          {loading ? (
            <LoadingSkeleton type="grid" count={4} />
          ) : error ? (
            <EmptyState
              icon="⚠️"
              title="Failed to load catalog"
              description={error}
            />
          ) : products.length === 0 ? (
            <EmptyState
              icon="🔍"
              title="No products found"
              description={search ? `No matches for "${search}". Try searching something else.` : 'There are currently no products available.'}
            />
          ) : (
            <div className={styles.grid}>
              {products.map((product) => (
                <ProductCard
                  key={product.id}
                  product={product}
                  onAddToCart={(p) => addItem(p, 1)}
                />
              ))}
            </div>
          )}
        </section>
      </main>

      <CartDrawer isOpen={isCartOpen} onClose={() => setIsCartOpen(false)} />
    </div>
  );
}
