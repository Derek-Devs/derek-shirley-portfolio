export type InsightCategory = 'Product' | 'Player' | 'Marketing';

export type KPI = { label: string; value: string; icon?: string };
export type Assumption = { label: string; value: string };
export type SourceLink = { name: string; url: string };

export interface Insight {
  slug: string;
  title: string;
  subtitle?: string;
  date: string; // ISO string
  category: InsightCategory;
  summary: string;
  tags?: string[];
  hero?: { kicker?: string; imageUrl?: string };
  kpis?: KPI[];
  assumptions?: Assumption[];
  // For charts / calc sections (optional)
  model?: {
    priceUSD?: number; // list price
    aspUSD?: number; // avg selling price
    netPerUnitUSD?: number;
    ccuPeak?: number;
    ownersMultipliers?: number[]; // e.g., [5,8,12]
  };
  sections: Array<{
    heading: string;
    body: string[]; // paragraphs
  }>;
  disclaimer?: string;
  sources?: SourceLink[];
}

// ---- SAMPLE (Mock) — Silksong launch analysis ----
// This is provided as an illustrative example only. Numbers are user-provided estimates.

export const INSIGHTS: Insight[] = [
  {
    slug: 'silksong-day1-analysis',
    title: 'Indie Moment of the Year: Hollow Knight: Silksong — Day‑1 PC Estimates (Mock Example)',
    subtitle: 'A product- and player-first launch breakdown',
    date: '2025-09-11',
    category: 'Player',
    summary:
      'Rapid, skimmable breakdown of a landmark launch: estimated units, day‑1 net revenue (Steam only), ROI snapshot, and why the product decisions drove outsized results.',
    tags: ['HollowKnight', 'Silksong', 'Launch', 'DataAnalysis'],
    hero: { kicker: 'Sample Case Study (Mock Data)' },
    kpis: [
      { label: 'Peak CCU', value: '535,000', icon: 'FaChartBar' },
      { label: 'Est. Day‑1 Units (5×–12×)', value: '2.7M – 6.4M' },
      { label: 'Est. Net Revenue (Steam)', value: '$32M – $76M' },
      { label: 'Break‑Even Units', value: '≈600k – 1.7M' },
    ],
    assumptions: [
      { label: 'Price', value: '$20 (ASP ~ $17)' },
      { label: 'Steam Revenue Share', value: '30% (Net ~$11.90/unit)' },
      { label: 'Peak CCU → Owners Multiplier', value: '5× (cons) to 12× (agg)' },
    ],
    model: {
      priceUSD: 20,
      aspUSD: 17,
      netPerUnitUSD: 11.9,
      ccuPeak: 535000,
      ownersMultipliers: [5, 8, 12],
    },
    sections: [
      {
        heading: 'Ballpark ROI Snapshot',
        body: [
          'Estimated total cost (6.5-year dev cycle): $7M–$23M. This launch almost certainly became profitable on day one, with immediate ROI likely between 1.4× and 10× from PC sales alone (before refunds/taxes and excluding consoles/subscriptions).',
        ],
      },
      {
        heading: 'Why This Worked (Product Analysis)',
        body: [
          'A perfected core loop (Explore → Die → Upgrade → Repeat) creates strong intrinsic motivation and long sessions.',
          'Player‑first design: precise controls and fair challenge; no microtransactions builds trust and goodwill.',
          'Content‑rich value at a $20 price point creates extraordinary perceived value and adoption.',
          'Intrinsic discovery: the world is discovered, not dictated — fostering community evangelism and organic growth.',
        ],
      },
    ],
    disclaimer:
      'All figures are personal estimates based on public pricing and observable Steam‑style data. Not affiliated with the developer/publisher. Example provided for portfolio demonstration only.',
    sources: [{ name: 'steamdb.info', url: 'https://steamdb.info' }],
  },
];