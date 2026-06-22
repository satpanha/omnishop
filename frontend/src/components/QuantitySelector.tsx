'use client';

import React from 'react';
import { triggerHaptic } from '@/lib/telegram';
import styles from './QuantitySelector.module.css';

interface QuantitySelectorProps {
  value: number;
  onChange: (value: number) => void;
  max?: number;
  min?: number;
}

export default function QuantitySelector({
  value,
  onChange,
  max = 99,
  min = 1,
}: QuantitySelectorProps) {
  const handleDecrement = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (value > min) {
      triggerHaptic('light');
      onChange(value - 1);
    }
  };

  const handleIncrement = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (value < max) {
      triggerHaptic('light');
      onChange(value + 1);
    }
  };

  return (
    <div className={styles.selector}>
      <button
        onClick={handleDecrement}
        disabled={value <= min}
        className={styles.button}
        aria-label="Decrease quantity"
      >
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
      </button>

      <span className={styles.value}>{value}</span>

      <button
        onClick={handleIncrement}
        disabled={value >= max}
        className={styles.button}
        aria-label="Increase quantity"
      >
        <svg
          width="14"
          height="14"
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
      </button>
    </div>
  );
}
