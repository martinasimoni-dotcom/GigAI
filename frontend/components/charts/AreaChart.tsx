'use client';

import React from 'react';
import {
  AreaChart as RechartsArea,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

interface AreaChartProps {
  data: any[];
  dataKey: string;
  xAxisKey: string;
  title?: string;
  height?: number;
  color?: string;
}

export default function AreaChart({
  data,
  dataKey,
  xAxisKey,
  title,
  height = 300,
  color = '#45B7D1',
}: AreaChartProps) {
  return (
    <div className="w-full">
      {title && <h3 className="text-lg font-bold text-gray-900 mb-4">{title}</h3>}
      <ResponsiveContainer width="100%" height={height}>
        <RechartsArea
          data={data}
          margin={{ top: 10, right: 30, left: 0, bottom: 10 }}
        >
          <defs>
            <linearGradient id="colorArea" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.8} />
              <stop offset="95%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey={xAxisKey} stroke="#6b7280" />
          <YAxis stroke="#6b7280" />
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
          <Area
            type="monotone"
            dataKey={dataKey}
            stroke={color}
            fill="url(#colorArea)"
            strokeWidth={2}
            isAnimationActive={true}
            animationDuration={300}
          />
        </RechartsArea>
      </ResponsiveContainer>
    </div>
  );
}
