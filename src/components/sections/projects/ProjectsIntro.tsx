// src/components/sections/projects/ProjectsIntro.tsx
import React from 'react';

export default function ProjectsIntro() {
  return (
    <section className="py-16 md:py-20">
      <div className="container mx-auto px-4 text-center">
        <h1 className="text-4xl font-bold tracking-tight text-base-content sm:text-5xl lg:text-6xl">
          From Data to Decisions: A Portfolio of Work
        </h1>
        <p className="mt-6 text-lg leading-8 text-base-content/80 max-w-3xl mx-auto">
          This portfolio showcases my end-to-end approach to transforming raw data into strategic business assets. Each project highlights a different facet of my expertise, from engineering robust data pipelines to developing interactive dashboards that deliver clear, actionable insights and drive data-informed decisions.
        </p>
      </div>
    </section>
  );
}