'use client';
import React from 'react';
import type { KPI } from '@/content/insights';
import { FaChartBar, FaStar, FaCheckCircle } from 'react-icons/fa';

const ICONS: Record<string, React.ReactNode> = {
  FaChartBar: <FaChartBar />,
  FaStar: <FaStar />,
  FaCheckCircle: <FaCheckCircle />,
};

export default function KPIGrid({ items }: { items?: KPI[] }) {
  if (!items || items.length === 0) return null;
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {items.map((k) => (
        <div key={k.label} className="bg-base-100 p-5 rounded-lg border border-base-300 shadow-sm">
          <div className="text-2xl text-primary mb-2">{k.icon ? ICONS[k.icon] : <FaStar />}</div>
          <div className="text-2xl font-bold">{k.value}</div>
          <div className="text-sm opacity-80 mt-1">{k.label}</div>
        </div>
      ))}
    </div>
  );
}