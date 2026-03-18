'use client';

import React from 'react';

interface StatCardProps {
  title: string;
  value: number | string;
  icon: string;
  trend?: {
    direction: 'up' | 'down';
    value: number;
  };
  color?: 'blue' | 'green' | 'red' | 'orange' | 'purple';
  unit?: string;
}

const colorClasses = {
  blue: {
    bg: 'bg-blue-50',
    text: 'text-blue-600',
    icon: 'bg-blue-100',
  },
  green: {
    bg: 'bg-green-50',
    text: 'text-green-600',
    icon: 'bg-green-100',
  },
  red: {
    bg: 'bg-red-50',
    text: 'text-red-600',
    icon: 'bg-red-100',
  },
  orange: {
    bg: 'bg-orange-50',
    text: 'text-orange-600',
    icon: 'bg-orange-100',
  },
  purple: {
    bg: 'bg-purple-50',
    text: 'text-purple-600',
    icon: 'bg-purple-100',
  },
};

export default function StatCard({
  title,
  value,
  icon,
  trend,
  color = 'blue',
  unit = '',
}: StatCardProps) {
  const colors = colorClasses[color];
  const trendIcon = trend?.direction === 'up' ? '↑' : '↓';
  const trendColor = trend?.direction === 'up' ? 'text-green-600' : 'text-red-600';

  return (
    <div
      className={`rounded-lg p-6 ${colors.bg} border border-gray-200 shadow-sm hover:shadow-md transition-all duration-300`}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <div className="mt-2 flex items-baseline gap-2">
            <p className={`text-3xl font-bold ${colors.text}`}>{value}</p>
            {unit && <span className="text-sm text-gray-600">{unit}</span>}
          </div>
          {trend && (
            <p className={`mt-3 text-sm font-semibold ${trendColor}`}>
              {trendIcon} {Math.abs(trend.value)}% from last period
            </p>
          )}
        </div>
        <div className={`p-3 rounded-lg ${colors.icon} text-2xl`}>{icon}</div>
      </div>
    </div>
  );
}
