import React from 'react';
import styles from './LoadingSkeleton.module.css';

interface LoadingSkeletonProps {
  type?: 'grid' | 'list' | 'detail';
  count?: number;
}

export default function LoadingSkeleton({ type = 'grid', count = 4 }: LoadingSkeletonProps) {
  if (type === 'grid') {
    return (
      <div className={styles.grid}>
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className={`${styles.card} shimmer`}>
            <div className={styles.imagePlaceholder} />
            <div className={styles.textContainer}>
              <div className={styles.titlePlaceholder} />
              <div className={styles.descPlaceholder} />
              <div className={styles.footerPlaceholder}>
                <div className={styles.pricePlaceholder} />
                <div className={styles.buttonPlaceholder} />
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (type === 'list') {
    return (
      <div className={styles.list}>
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className={`${styles.listItem} shimmer`}>
            <div className={styles.thumbnailPlaceholder} />
            <div className={styles.listTextContainer}>
              <div className={styles.lineLong} />
              <div className={styles.lineShort} />
            </div>
            <div className={styles.valuePlaceholder} />
          </div>
        ))}
      </div>
    );
  }

  if (type === 'detail') {
    return (
      <div className={`${styles.detail} shimmer`}>
        <div className={styles.detailImagePlaceholder} />
        <div className={styles.detailContent}>
          <div className={styles.lineLong} style={{ height: '24px', marginBottom: '12px' }} />
          <div className={styles.lineShort} style={{ width: '40%', height: '20px', marginBottom: '24px' }} />
          <div className={styles.lineLong} style={{ height: '14px', marginBottom: '8px' }} />
          <div className={styles.lineLong} style={{ height: '14px', marginBottom: '8px' }} />
          <div className={styles.lineShort} style={{ width: '60%', height: '14px', marginBottom: '32px' }} />
          <div className={styles.detailFooter}>
            <div className={styles.lineShort} style={{ width: '30%', height: '28px' }} />
            <div className={styles.buttonPlaceholder} style={{ width: '120px', height: '40px' }} />
          </div>
        </div>
      </div>
    );
  }

  return null;
}
