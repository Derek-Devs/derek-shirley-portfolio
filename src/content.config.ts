import { defineCollection } from "astro:content";
import { glob } from "astro/loaders";
import { z } from "astro/zod";

const work = defineCollection({
  loader: glob({ base: "./src/content/work", pattern: "**/*.{md,yaml,yml}" }),
  schema: z.object({
    title: z.string(),
    organization: z.string(),
    kind: z.enum(["professional", "independent"]),
    summary: z.string(),
    impact: z.string(),
    href: z.string().optional(),
    github: z.string().optional(),
    demo: z.string().optional(),
    featured: z.boolean().optional(),
    status: z.enum(["in-development"]).optional(),
    order: z.number(),
  }),
});

const experience = defineCollection({
  loader: glob({ base: "./src/content/experience", pattern: "**/*.mdx" }),
  schema: z.object({
    organization: z.string(),
    title: z.string(),
    start: z.object({
      iso: z.string(),
      label: z.string(),
    }),
    end: z
      .object({
        iso: z.string(),
        label: z.string(),
      })
      .optional(),
    location: z.string(),
    prominence: z.enum(["primary", "major", "standard", "compact"]),
    order: z.number(),
  }),
});

const cases = defineCollection({
  loader: glob({ base: "./src/content/cases", pattern: "**/*.mdx" }),
  schema: z.object({
    title: z.string(),
    kicker: z.string(),
    organization: z.string(),
    role: z.string(),
    year: z.string().optional(),
    timeframe: z.string().optional(),
    summary: z.string(),
    question: z.string(),
    impact: z.string(),
    methods: z.string(),
    seoTitle: z.string(),
    seoDescription: z.string(),
    featured: z.boolean().optional(),
  }),
});

export const collections = { work, experience, cases };
