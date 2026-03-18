'use client';

import React from 'react';
import Card from './Card';

interface ChartCardProps {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  loading?: boolean;
  error?: string;
}

export default function ChartCard({
  title,
  subtitle,
  children,
  loading = false,
  error,
}: ChartCardProps) {
  if (loading) {
    return (
      <Card title={title} subtitle={subtitle}>
        <div className="h-64 flex items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card title={title} subtitle={subtitle}>
        <div className="h-64 flex items-center justify-center">
          <div className="text-center">
            <p className="text-red-600 font-semibold">{error}</p>
            <p className="text-gray-600 text-sm mt-2">Unable to load chart data</p>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card title={title} subtitle={subtitle}>
      {children}
    </Card>
  );
}
