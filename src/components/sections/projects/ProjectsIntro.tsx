// src/components/sections/projects/ProjectsIntro.tsx
import React from 'react';

export default function ProjectsIntro() {
  return (
    <section className="py-16 md:py-20">
      <div className="container mx-auto px-4 text-center">
        <h1 className="text-4xl font-bold tracking-tight text-base-content sm:text-5xl lg:text-6xl">
          End-to-End Analytics Projects
        </h1>
        <p className="mt-6 text-lg leading-8 text-base-content/80 max-w-2xl mx-auto">
          Below is a selection of my work, demonstrating the complete process of transforming raw data into strategic business assets. Each project highlights a different facet of my approach: from engineering robust data pipelines to developing interactive dashboards that deliver clear, actionable insights.
        </p>
      </div>
    </section>
  );
}
