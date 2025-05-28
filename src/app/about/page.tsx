// src/app/about/page.tsx
import React from 'react';

import AboutIntro from '@/components/sections/about/AboutIntro.tsx'; 
import ExperienceTimeline from '@/components/sections/about/ExperienceTimeline.tsx'; 
import AboutSkills from '@/components/sections/about/AboutSkills.tsx'; 
import AboutBackground from '@/components/sections/about/AboutBackground.tsx';
import AboutCTA from '@/components/sections/about/AboutCTA.tsx'; 
import Divider from '@/components/ui/Divider'; 

export default function AboutPage() {
  return (
    <main className="overflow-x-hidden">
      <AboutIntro />
      <Divider /> 
      <ExperienceTimeline />
      <Divider /> 
      <AboutSkills />
      <Divider /> 
      <AboutBackground />
      <Divider /> 
      <AboutCTA />
    </main>
  );
}