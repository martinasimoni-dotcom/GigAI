'use client';

import React from 'react';
import {
  PieChart as RechartsPie,
  Pie,
  Cell,
  Legend,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

interface PieChartProps {
  data: { name: string; value: number; color?: string }[];
  title?: string;
  height?: number;
  innerRadius?: number;
}

const DEFAULT_COLORS = [
  '#FF6B6B', // Red for HIGH
  '#FFA500', // Orange for MEDIUM
  '#4ECDC4', // Teal for LOW/Completed
  '#45B7D1', // Blue for In Progress
  '#96CEB4', // Green for Completed
];

export default function PieChart({
  data,
  title,
  height = 300,
  innerRadius = 0,
}: PieChartProps) {
  const chartData = data.map((item, index) => ({
    ...item,
    color: item.color || DEFAULT_COLORS[index % DEFAULT_COLORS.length],
  }));

  return (
    <div className="w-full">
      {title && <h3 className="text-lg font-bold text-gray-900 mb-4">{title}</h3>}
      <ResponsiveContainer width="100%" height={height}>
        <RechartsPie
          data={chartData}
          cx="50%"
          cy="50%"
          innerRadius={innerRadius}
          outerRadius={80}
          paddingAngle={2}
          dataKey="value"
        >
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
          <Tooltip
            contentStyle={{
              backgroundColor: 'rgba(0, 0, 0, 0.8)',
              border: 'none',
              borderRadius: '8px',
              color: '#fff',
              padding: '8px 12px',
            }}
            formatter={(value: number) => [`${value}`, 'Count']}
          />
          <Legend
            verticalAlign="bottom"
            height={36}
            wrapperStyle={{
              paddingTop: '20px',
            }}
          />
        </RechartsPie>
      </ResponsiveContainer>
    </div>
  );
}
