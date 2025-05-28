"use client"; 
import React from 'react';
import HeroSection from '@/components/sections/HeroSection.tsx'; 
import SkillsSection from '@/components/sections/SkillsSection.tsx';
import FeaturedProjectsSection from '@/components/sections/FeaturedProjectsSection.tsx';
import CallToActionSection from '@/components/sections/CallToActionSection.tsx'; 

export default function Page() {
  return (
    <main className="flex-grow"> 
      <HeroSection />
      <SkillsSection />
      <FeaturedProjectsSection />
      <CallToActionSection />
    </main>
  );
}