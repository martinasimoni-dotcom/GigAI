'use client';

import React from 'react';
import {
  BarChart as RechartsBar,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from 'recharts';

interface BarChartProps {
  data: any[];
  dataKey: string | string[];
  xAxisKey: string;
  title?: string;
  height?: number;
  colors?: string[];
  stacked?: boolean;
}

const DEFAULT_COLORS = ['#FF6B6B', '#FFA500', '#4ECDC4', '#45B7D1', '#96CEB4'];

export default function BarChart({
  data,
  dataKey,
  xAxisKey,
  title,
  height = 300,
  colors = DEFAULT_COLORS,
  stacked = false,
}: BarChartProps) {
  const dataKeys = Array.isArray(dataKey) ? dataKey : [dataKey];

  return (
    <div className="w-full">
      {title && <h3 className="text-lg font-bold text-gray-900 mb-4">{title}</h3>}
      <ResponsiveContainer width="100%" height={height}>
        <RechartsBar
          data={data}
          layout="vertical"
          margin={{ top: 5, right: 30, left: 200, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis type="number" stroke="#6b7280" />
          <YAxis dataKey={xAxisKey} type="category" width={190} stroke="#6b7280" />
          <Tooltip
            contentStyle={{
              backgroundColor: 'rgba(0, 0, 0, 0.8)',
              border: 'none',
              borderRadius: '8px',
              color: '#fff',
              padding: '8px 12px',
            }}
          />
          <Legend />
          {dataKeys.map((key, index) => (
            <Bar
              key={key}
              dataKey={key}
              fill={colors[index % colors.length]}
              radius={[0, 8, 8, 0]}
              stackId={stacked ? 'stack' : undefined}
            />
          ))}
        </RechartsBar>
      </ResponsiveContainer>
    </div>
  );
}
