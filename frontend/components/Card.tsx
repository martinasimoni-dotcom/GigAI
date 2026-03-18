'use client';

import React from 'react';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  title?: string;
  subtitle?: string;
  padding?: 'sm' | 'md' | 'lg';
}

export default function Card({
  children,
  className = '',
  title,
  subtitle,
  padding = 'md',
}: CardProps) {
  const paddingClass = {
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8',
  }[padding];

  return (
    <div
      className={`rounded-lg bg-white border border-gray-200 shadow-sm hover:shadow-md transition-shadow ${paddingClass} ${className}`}
    >
      {(title || subtitle) && (
        <div className="mb-6">
          {title && <h2 className="text-lg font-bold text-gray-900">{title}</h2>}
          {subtitle && <p className="text-sm text-gray-600 mt-1">{subtitle}</p>}
        </div>
      )}
      {children}
    </div>
  );
}
