// src/components/sections/about/ExperienceTimeline.tsx
"use client";

import React from 'react';
import { motion } from 'framer-motion';

const experienceTimeline = [
  {
    company: "Dave & Buster’s",
    title: "Marketing Analytics Lead",
    years: "Aug 2024 – Present",
    location: "Grapevine, TX",
    isCurrent: true,
  },
  {
    company: "GameStop Corp.",
    title: "Senior Data Analyst, Supply Chain",
    years: "May 2023 – Aug 2024",
    location: "Grapevine, TX",
  },
  {
    company: "Glitch Breakers",
    title: "Founder / Lead Data Analyst",
    years: "Jan 2023 – May 2023",
    location: "Northlake, TX",
  },
  {
    company: "American Diamond Logistics",
    title: "Founding Lead, Data & Analytics",
    years: "Jun 2020 - Jan 2023",
    location: "Roanoke, TX",
  },
  {
    company: "Park West Galleries",
    title: "Sales Analyst",
    years: "Jan 2017 - Jan 2020",
    location: "Miami, FL",
  },
];

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.3,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, x: -50 },
  visible: { opacity: 1, x: 0, transition: { duration: 0.5, ease: 'easeOut'} },
};

const itemVariantsRight = {
    hidden: { opacity: 0, x: 50 },
    visible: { opacity: 1, x: 0, transition: { duration: 0.5, ease: 'easeOut'} },
};

const ExperienceTimeline: React.FC = () => {
  return (
    <section className="bg-base-200 py-16 md:py-20">
      <div className="container mx-auto px-4">
        <motion.h2
          className="text-3xl md:text-4xl font-bold text-center mb-16 text-secondary"
          initial={{ opacity: 0, y:-20}}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.5 }}
        >
          Career Journey
        </motion.h2>

        <motion.div
          className="relative max-w-3xl mx-auto"
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.1 }}
        >
          <div className="absolute left-4 md:left-1/2 top-0 bottom-0 w-0.5 bg-base-content/20 transform md:-translate-x-1/2"></div>

          {experienceTimeline.map((job, index) => (
            <motion.div
              key={index}
              className="mb-10 md:mb-12 relative pl-10 md:pl-0"
              variants={index % 2 === 0 ? itemVariants : itemVariantsRight}
            >
              <div className={`absolute left-4 top-1 w-4 h-4 rounded-full border-2 border-base-200 z-10 ${job.isCurrent ? 'bg-primary' : 'bg-base-content/50'} transform -translate-x-[9px] md:left-1/2 md:-translate-x-1/2`}></div>
              
              <div className={`md:w-[calc(50%-2rem)] ${index % 2 === 0 ? 'md:ml-[calc(50%+2rem)]' : 'md:mr-[calc(50%+2rem)] md:text-right'}`}>
                <div className={`hidden md:block absolute top-1 w-3 h-3 bg-base-100 transform rotate-45 ${index % 2 === 0 ? 'left-[calc(50%-0.375rem)] -ml-px' : 'right-[calc(50%-0.375rem)] -mr-px'}`}></div>
                <div className="bg-base-100 p-4 rounded-lg shadow-md relative">
                  <h3 className={`font-semibold text-lg ${job.isCurrent ? 'text-primary' : 'text-base-content'}`}>{job.company}</h3>
                  <p className="text-md opacity-90 text-base-content/90">{job.title}</p>
                  <p className="text-sm opacity-70 mt-1 text-base-content/70">
                    {job.years}
                  </p>
                  <p className="text-sm opacity-60 text-base-content/60">{job.location}</p>
                </div>
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
};

export default ExperienceTimeline;