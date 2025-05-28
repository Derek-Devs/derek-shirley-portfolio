// src/components/sections/projects/ProjectsIntro.tsx
import React from 'react';

export default function ProjectsIntro() {
  return (
    <section className="py-16 md:py-20">
      <div className="container mx-auto px-4 text-center">
        <h1 className="text-4xl font-bold tracking-tight text-base-content sm:text-5xl lg:text-6xl">
          Data Analysis Projects
        </h1>
        <p className="mt-6 text-lg leading-8 text-base-content/80 max-w-2xl mx-auto">
          Here&apos;s a selection of projects where I&apos;ve applied my analytical skills to extract insights, build models, and visualize data. Explore how I tackle real-world challenges.
        </p>
      </div>
    </section>
  );
}