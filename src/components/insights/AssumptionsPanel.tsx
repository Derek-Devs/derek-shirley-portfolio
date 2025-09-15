'use client';
import React from 'react';
import type { Assumption } from '@/content/insights';

export default function AssumptionsPanel({ items, title = 'Assumptions' }: { items?: Assumption[]; title?: string }) {
  if (!items || items.length === 0) return null;
  return (
    <div className="rounded-xl border border-base-300 bg-base-200 p-5">
      <h4 className="font-bold mb-3">{title}</h4>
      <ul className="divide-y divide-base-300">
        {items.map((a) => (
          <li key={a.label} className="py-2 flex items-start gap-3">
            <span className="badge badge-ghost mt-0.5">{a.label}</span>
            <span className="text-sm opacity-90">{a.value}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}