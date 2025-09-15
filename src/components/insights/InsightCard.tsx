'use client';
import React from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import type { Insight } from '@/content/insights';

const categoryColor: Record<string, string> = {
  Product: 'badge-primary',
  Player: 'badge-secondary',
  Marketing: 'badge-accent',
};

export default function InsightCard({ item }: { item: Insight }) {
  return (
    <motion.article
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.4 }}
      className="card bg-base-100 border border-base-300 shadow-sm hover:shadow-md"
    >
      <div className="card-body">
        <div className="flex items-center justify-between gap-3">
          <span className={`badge ${categoryColor[item.category]}`}>{item.category}</span>
          <time className="text-xs opacity-70">{new Date(item.date).toLocaleDateString()}</time>
        </div>
        <h3 className="card-title text-xl leading-tight mt-1">
          <Link href={`/insights/${item.slug}`} className="hover:underline">
            {item.title}
          </Link>
        </h3>
        {item.subtitle && <p className="text-sm opacity-80 -mt-1">{item.subtitle}</p>}
        <p className="mt-2 text-sm opacity-90">{item.summary}</p>
        {item.tags && (
          <div className="mt-3 flex flex-wrap gap-2">
            {item.tags.slice(0, 5).map((t) => (
              <span key={t} className="badge badge-ghost">#{t}</span>
            ))}
          </div>
        )}
        <div className="card-actions justify-end mt-4">
          <Link href={`/insights/${item.slug}`} className="btn btn-sm btn-outline">Read</Link>
        </div>
      </div>
    </motion.article>
  );
}