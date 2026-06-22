import React from 'react';
import Link from 'next/link';
import styles from './EmptyState.module.css';

interface EmptyStateProps {
  icon?: string;
  title: string;
  description?: string;
  action?: {
    label: string;
    href: string;
  };
}

export default function EmptyState({
  icon = '📦',
  title,
  description,
  action,
}: EmptyStateProps) {
  return (
    <div className={`${styles.container} fade-in`}>
      <span className={styles.icon}>{icon}</span>
      <h3 className={styles.title}>{title}</h3>
      {description && <p className={styles.description}>{description}</p>}
      {action && (
        <Link href={action.href} className="btn-primary" style={{ textDecoration: 'none' }}>
          {action.label}
        </Link>
      )}
    </div>
  );
}
