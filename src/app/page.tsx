// src/app/page.tsx
"use client"; 
import React from 'react';
import HeroSection from '@/components/sections/HeroSection.tsx'; // Adjust path if needed
import SkillsSection from '@/components/sections/SkillsSection.tsx'; // Adjust path if needed
import FeaturedProjectsSection from '@/components/sections/FeaturedProjectsSection.tsx'; // Adjust path if needed
import CallToActionSection from '@/components/sections/CallToActionSection.tsx'; // Adjust path if needed

// Default export for Next.js App Router page
export default function Page() {
  return (
    <main className="flex-grow"> {/* Use main tag for semantic content */}
      {/* Render the different sections of the homepage */}
      <HeroSection />
      <SkillsSection />
      <FeaturedProjectsSection />
      <CallToActionSection />
      {/* Add more sections here as needed (e.g., Experience Timeline, Blog Posts) */}
    </main>
  );
}