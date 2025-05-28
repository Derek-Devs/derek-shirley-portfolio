// src/app/projects/page.tsx
"use client"
import React from 'react';

import ProjectsIntro from '@/components/sections/projects/ProjectsIntro';
import ProjectList from '@/components/sections/projects/ProjectList';
import ProjectsCTA from '@/components/sections/CallToActionSection'; 

export default function ProjectsPage() {
  return (
    <main className="overflow-x-hidden bg-base-100 text-base-content py-12 md:py-16">
      <ProjectsIntro />
      <ProjectList />
      <ProjectsCTA />
    </main>
  );
}