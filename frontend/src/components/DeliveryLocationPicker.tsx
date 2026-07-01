/**
 * DeliveryLocationPicker
 *
 * Lets the buyer provide a delivery address/location.  Two modes:
 *   1. GPS — requests browser geolocation and reverse-geocodes to a human
 *      address via the free Nominatim API (no API key needed, public-domain).
 *   2. Manual — a text input for the buyer to type their address.
 *
 * The component calls `onChange` with a DeliveryLocation object whenever
 * either the coordinates or the address changes, and calls it with `null`
 * when the buyer has not yet provided a location.
 */
'use client';

import React, { useCallback, useEffect, useState } from 'react';
import type { DeliveryLocation } from '@/lib/api';
import styles from './DeliveryLocationPicker.module.css';

interface Props {
  onChange: (location: DeliveryLocation | null) => void;
}

type Mode = 'idle' | 'gps' | 'manual';

async function reverseGeocode(lat: number, lng: number): Promise<string> {
  try {
    const res = await fetch(
      `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}`,
      { headers: { 'Accept-Language': 'en' } }
    );
    if (!res.ok) throw new Error('Nominatim error');
    const data = await res.json();
    return data.display_name || `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
  } catch {
    return `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
  }
}

export default function DeliveryLocationPicker({ onChange }: Props) {
  const [mode, setMode] = useState<Mode>('idle');
  const [gpsLoading, setGpsLoading] = useState(false);
  const [gpsError, setGpsError] = useState<string | null>(null);
  const [manualAddress, setManualAddress] = useState('');
  const [resolved, setResolved] = useState<DeliveryLocation | null>(null);

  // Notify parent whenever resolved location changes.
  useEffect(() => {
    onChange(resolved);
  }, [resolved, onChange]);

  const handleGps = useCallback(async () => {
    if (!navigator.geolocation) {
      setGpsError('Geolocation is not supported by your browser.');
      return;
    }
    setMode('gps');
    setGpsLoading(true);
    setGpsError(null);

    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const { latitude: lat, longitude: lng } = pos.coords;
        const address = await reverseGeocode(lat, lng);
        setResolved({ lat, lng, address });
        setGpsLoading(false);
      },
      (err) => {
        setGpsError(err.message || 'Could not get your location.');
        setGpsLoading(false);
        setMode('idle');
      },
      { timeout: 10000, enableHighAccuracy: true }
    );
  }, []);

  const handleManualMode = () => {
    setMode('manual');
    setResolved(null);
  };

  const handleManualChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setManualAddress(val);
    // No coords for manual — backend allows a text-only address.
    setResolved(val.trim() ? { lat: 0, lng: 0, address: val.trim() } : null);
  };

  const handleClear = () => {
    setMode('idle');
    setResolved(null);
    setManualAddress('');
    setGpsError(null);
  };

  if (mode === 'idle') {
    return (
      <div className={styles.idle}>
        <p className={styles.hint}>Add a delivery location (optional)</p>
        <div className={styles.idleButtons}>
          <button
            type="button"
            id="delivery-gps-btn"
            className={`${styles.modeBtn} ${styles.gpsBtn}`}
            onClick={handleGps}
          >
            📍 Use My Location
          </button>
          <button
            type="button"
            id="delivery-manual-btn"
            className={`${styles.modeBtn} ${styles.manualBtn}`}
            onClick={handleManualMode}
          >
            ✏️ Enter Address
          </button>
        </div>
        {gpsError && <p className={styles.error}>{gpsError}</p>}
      </div>
    );
  }

  if (mode === 'gps') {
    if (gpsLoading) {
      return (
        <div className={styles.resolving}>
          <span className={styles.spinner} aria-label="Locating…" />
          <span>Detecting your location…</span>
        </div>
      );
    }
    if (resolved) {
      return (
        <div className={styles.resolved}>
          <span className={styles.pin}>📍</span>
          <span className={styles.address}>{resolved.address}</span>
          <button type="button" className={styles.clearBtn} onClick={handleClear} title="Remove location">
            ✕
          </button>
        </div>
      );
    }
  }

  if (mode === 'manual') {
    return (
      <div className={styles.manual}>
        <input
          id="delivery-address-input"
          type="text"
          className={styles.addressInput}
          placeholder="Street, district, city…"
          value={manualAddress}
          onChange={handleManualChange}
          autoFocus
        />
        <button type="button" className={styles.clearBtn} onClick={handleClear} title="Cancel">
          ✕
        </button>
      </div>
    );
  }

  return null;
}
