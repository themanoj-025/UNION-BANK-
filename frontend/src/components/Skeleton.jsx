import React from 'react';
import './Skeleton.css';

export function Skeleton({ width, height, borderRadius = '8px', style = {} }) {
  return (
    <div
      className="skeleton-pulse"
      style={{
        width: width || '100%',
        height: height || '20px',
        borderRadius,
        ...style,
      }}
    />
  );
}

// Deterministic widths that cycle through these values (no Math.random)
const CARD_LINE_WIDTHS = ['60%', '75%', '50%', '85%', '40%'];
const TABLE_CELL_WIDTHS = ['65%', '55%', '75%', '60%', '80%', '45%', '70%'];

export function SkeletonCard({ lines = 3 }) {
  return (
    <div className="skeleton-card">
      <Skeleton height="24px" width="60%" style={{ marginBottom: '16px' }} />
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          height="14px"
          width={CARD_LINE_WIDTHS[i % CARD_LINE_WIDTHS.length]}
          style={{ marginBottom: '10px' }}
        />
      ))}
    </div>
  );
}

export function SkeletonTable({ rows = 5, cols = 5 }) {
  return (
    <div className="skeleton-table-wrapper">
      {/* Header */}
      <div className="skeleton-table-row skeleton-table-header">
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={`h-${i}`} height="16px" width="80%" />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, r) => (
        <div key={`r-${r}`} className="skeleton-table-row">
          {Array.from({ length: cols }).map((_, c) => (
            <Skeleton key={`c-${r}-${c}`} height="14px" width={TABLE_CELL_WIDTHS[(r + c) % TABLE_CELL_WIDTHS.length]} />
          ))}
        </div>
      ))}
    </div>
  );
}
