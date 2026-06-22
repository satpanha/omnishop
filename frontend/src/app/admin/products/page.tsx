'use client';

import React, { useEffect, useState } from 'react';
import { getProducts, createProduct, updateProduct, deleteProduct, type Product } from '@/lib/api';
import { triggerHaptic } from '@/lib/telegram';
import LoadingSkeleton from '@/components/LoadingSkeleton';
import EmptyState from '@/components/EmptyState';
import styles from './page.module.css';

export default function AdminProducts() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    price: '',
    stock_quantity: '',
    image_url: '',
  });
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const fetchProducts = () => {
    setLoading(true);
    getProducts({ limit: 100 })
      .then((res) => {
        setProducts(res.items);
        setError(null);
      })
      .catch((err) => {
        setError(err.message || 'Failed to load products');
      })
      .finally(() => {
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchProducts();
  }, []);

  const openAddModal = () => {
    setEditingProduct(null);
    setFormData({
      name: '',
      description: '',
      price: '',
      stock_quantity: '0',
      image_url: '',
    });
    setSubmitError(null);
    setIsModalOpen(true);
  };

  const openEditModal = (product: Product) => {
    setEditingProduct(product);
    setFormData({
      name: product.name,
      description: product.description || '',
      price: String(product.price),
      stock_quantity: String(product.stock_quantity),
      image_url: product.image_url || '',
    });
    setSubmitError(null);
    setIsModalOpen(true);
  };

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError(null);
    setSubmitting(true);
    triggerHaptic('medium');

    const payload = {
      name: formData.name,
      description: formData.description || undefined,
      price: parseFloat(formData.price),
      stock_quantity: parseInt(formData.stock_quantity, 10),
      image_url: formData.image_url || undefined,
    };

    if (isNaN(payload.price) || payload.price < 0) {
      setSubmitError('Please enter a valid price (e.g. 10.99)');
      setSubmitting(false);
      return;
    }

    if (isNaN(payload.stock_quantity) || payload.stock_quantity < 0) {
      setSubmitError('Please enter a valid stock level (e.g. 0 or higher)');
      setSubmitting(false);
      return;
    }

    try {
      if (editingProduct) {
        // Edit flow
        await updateProduct(editingProduct.id, payload);
      } else {
        // Create flow
        await createProduct(payload);
      }

      triggerHaptic('notification', 'success');
      setIsModalOpen(false);
      fetchProducts();
    } catch (err: any) {
      triggerHaptic('notification', 'error');
      setSubmitError(err.message || 'An error occurred during save.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteProduct = async (id: string) => {
    if (!confirm('Are you sure you want to delete this product? (It will be soft-deleted and hidden)')) {
      return;
    }
    triggerHaptic('heavy');
    try {
      await deleteProduct(id);
      triggerHaptic('notification', 'success');
      fetchProducts();
    } catch (err: any) {
      triggerHaptic('notification', 'error');
      alert(err.message || 'Delete operation failed.');
    }
  };

  return (
    <div className="fade-in">
      <div className={styles.headerRow}>
        <h1 className={styles.heading}>Store Inventory</h1>
        <button className="btn-primary" onClick={openAddModal}>
          + Add Product
        </button>
      </div>

      {loading ? (
        <LoadingSkeleton type="list" count={4} />
      ) : error ? (
        <EmptyState icon="⚠️" title="Error Loading Products" description={error} />
      ) : products.length === 0 ? (
        <EmptyState
          icon="📦"
          title="No Products Yet"
          description="Click '+ Add Product' to start building your catalogue."
        />
      ) : (
        <div className={styles.inventoryList}>
          {products.map((p) => (
            <div key={p.id} className={`${styles.productItem} glass-card ${!p.is_active ? styles.inactive : ''}`}>
              <div className={styles.productImage}>
                {p.image_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={p.image_url} alt={p.name} />
                ) : (
                  <span>📦</span>
                )}
              </div>

              <div className={styles.productDetails}>
                <h3 className={styles.productName}>
                  {p.name} {!p.is_active && <span className={styles.inactiveLabel}>(Hidden)</span>}
                </h3>
                <div className={styles.productMeta}>
                  <span className={styles.productPrice}>${Number(p.price).toFixed(2)}</span>
                  <span className={styles.productStock}>Stock: {p.stock_quantity}</span>
                </div>
              </div>

              <div className={styles.itemActions}>
                <button
                  onClick={() => openEditModal(p)}
                  className={styles.actionButton}
                  aria-label="Edit"
                >
                  ✏️
                </button>
                <button
                  onClick={() => handleDeleteProduct(p.id)}
                  disabled={!p.is_active}
                  className={styles.actionButton}
                  aria-label="Delete"
                >
                  🗑️
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add/Edit Modal overlay */}
      {isModalOpen && (
        <div className={styles.modalOverlay} onClick={() => setIsModalOpen(false)}>
          <div className={`${styles.modal} slide-up`} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <h2>{editingProduct ? 'Edit Product' : 'Add New Product'}</h2>
              <button className={styles.closeBtn} onClick={() => setIsModalOpen(false)}>
                ✕
              </button>
            </div>

            <form onSubmit={handleFormSubmit} className={styles.form}>
              {submitError && (
                <div className={styles.formError}>
                  <span>⚠️ {submitError}</span>
                </div>
              )}

              <div className={styles.formGroup}>
                <label htmlFor="name">Product Name *</label>
                <input
                  type="text"
                  id="name"
                  name="name"
                  value={formData.name}
                  onChange={handleInputChange}
                  required
                  placeholder="e.g. Wireless Headphones"
                />
              </div>

              <div className={styles.formGroup}>
                <label htmlFor="description">Description</label>
                <textarea
                  id="description"
                  name="description"
                  value={formData.description}
                  onChange={handleInputChange}
                  rows={3}
                  placeholder="Details about product..."
                />
              </div>

              <div className={styles.formRow}>
                <div className={styles.formGroup} style={{ flex: 1 }}>
                  <label htmlFor="price">Price ($) *</label>
                  <input
                    type="number"
                    step="0.01"
                    id="price"
                    name="price"
                    value={formData.price}
                    onChange={handleInputChange}
                    required
                    placeholder="29.99"
                  />
                </div>

                <div className={styles.formGroup} style={{ flex: 1 }}>
                  <label htmlFor="stock_quantity">Stock Level *</label>
                  <input
                    type="number"
                    id="stock_quantity"
                    name="stock_quantity"
                    value={formData.stock_quantity}
                    onChange={handleInputChange}
                    required
                    placeholder="50"
                  />
                </div>
              </div>

              <div className={styles.formGroup}>
                <label htmlFor="image_url">Image URL</label>
                <input
                  type="url"
                  id="image_url"
                  name="image_url"
                  value={formData.image_url}
                  onChange={handleInputChange}
                  placeholder="https://example.com/image.jpg"
                />
              </div>

              <button
                type="submit"
                disabled={submitting}
                className="btn-primary w-full mt-4"
                style={{ height: '44px', fontWeight: 'bold' }}
              >
                {submitting ? 'Saving...' : editingProduct ? 'Save Changes' : 'Create Product'}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
