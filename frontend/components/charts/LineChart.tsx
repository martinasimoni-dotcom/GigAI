'use client';

import React from 'react';
import {
  LineChart as RechartsLine,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

interface LineChartProps {
  data: any[];
  dataKeys: { key: string; color: string; name: string }[];
  xAxisKey: string;
  title?: string;
  height?: number;
}

export default function LineChart({
  data,
  dataKeys,
  xAxisKey,
  title,
  height = 300,
}: LineChartProps) {
  return (
    <div className="w-full">
      {title && <h3 className="text-lg font-bold text-gray-900 mb-4">{title}</h3>}
      <ResponsiveContainer width="100%" height={height}>
        <RechartsLine
          data={data}
          margin={{ top: 5, right: 30, left: 0, bottom: 5 }}
        >
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
          {dataKeys.map((item) => (
            <Line
              key={item.key}
              type="monotone"
              dataKey={item.key}
              stroke={item.color}
              name={item.name}
              strokeWidth={2}
              dot={{ fill: item.color, r: 4 }}
              activeDot={{ r: 6 }}
              isAnimationActive={true}
              animationDuration={300}
            />
          ))}
        </RechartsLine>
      </ResponsiveContainer>
    </div>
  );
}
