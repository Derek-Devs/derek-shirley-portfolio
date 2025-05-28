// File: src/app/projects/videoGameSales/page.tsx
'use client';

import React from 'react';
import dynamic from 'next/dynamic';

const GameSalesDashboardWithNoSSR = dynamic(
  () => import('./GameSalesDashboard'),
  { ssr: false }
);

export default function VideoGameSalesPage() {
  return (
    <div className="container mx-auto p-4">
      <h1 className="text-3xl font-bold mb-6">Video Game Sales Analysis - Data from 2017</h1>
      <GameSalesDashboardWithNoSSR />
    </div>
  );
}