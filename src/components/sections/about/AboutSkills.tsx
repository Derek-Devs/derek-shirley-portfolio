// src/components/sections/about/AboutSkills.tsx
"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { FaCode, FaChartLine, FaUsers, FaRocket, FaDatabase, FaPaintBrush } from 'react-icons/fa';

interface SkillCategory {
  icon: React.ElementType;
  title: string;
  skills: string[];
  color?: 'primary' | 'secondary' | 'accent';
}

const skillCategories: SkillCategory[] = [
  { icon: FaChartLine, title: "Analysis & Modeling", skills: ["SQL", "Python", "ETL", "Modeling", "Metrics", "Statistics"], color: 'primary' },
  { icon: FaPaintBrush, title: "Visualization & Reporting", skills: ["Power BI", "Tableau", "DAX", "Alteryx", "Storytelling"], color: 'secondary' },
  { icon: FaCode, title: "Programming & Web", skills: ["JavaScript", "TypeScript", "React", "HTML/CSS", "Next.js"], color: 'accent' },
  { icon: FaDatabase, title: "Databases & Cloud", skills: ["AWS", "GCP BigQuery", "Databricks", "MongoDB", "PostgreSQL"], color: 'primary' },
  { icon: FaUsers, title: "Professional Skills", skills: ["Leadership", "Communication", "Problem-Solving", "Stakeholder Mgt."], color: 'secondary' },
  { icon: FaRocket, title: "Tools & Methods", skills: ["Git", "Agile", "A/B Testing", "Web Scraping", "AI Tools"], color: 'accent' },
];

const titleVariants = {
  hidden: { opacity: 0, y: -20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5 } },
};

const gridContainerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1, delayChildren: 0.2 }
  }
};

const cardVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4 } },
};

// Moved outside component: Constant does not need to be redefined on each render
const badgeColorClasses = {
    primary: 'badge-primary',
    secondary: 'badge-secondary',
    accent: 'badge-accent',
    default: 'badge-neutral',
};

const AboutSkills: React.FC = () => {
  return (
    <section className="bg-base-100 py-16 md:py-20">
      <div className="container mx-auto px-4">
        <motion.h2
          className="text-3xl md:text-4xl font-bold text-center mb-12 text-primary"
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.3 }}
          variants={titleVariants}
        >
          Core Skill Areas
        </motion.h2>

        <motion.div
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 md:gap-8"
          variants={gridContainerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.1 }}
        >
          {skillCategories.map((category, index) => {
            const badgeClass = category.color ? badgeColorClasses[category.color] : badgeColorClasses.default;
            const iconBgClass = category.color ? `bg-${category.color}/10` : 'bg-neutral/10';
            const iconTextClass = category.color ? `text-${category.color}` : 'text-neutral-content';

            return (
              <motion.div
                key={index}
                variants={cardVariants}
                whileHover={{ y: -5, scale: 1.02 }}
                transition={{ type: "spring", stiffness: 300, damping: 15 }}
              >
                <div className="card bg-base-200 shadow-md border border-transparent hover:border-base-300 h-full transition-colors duration-300 overflow-hidden">
                  <div className="card-body items-center text-center p-6">
                    <div className={`rounded-full p-3 mb-4 inline-block ${iconBgClass}`}>
                      <category.icon className={`text-3xl ${iconTextClass}`} />
                    </div>
                    <h3 className="card-title text-lg font-semibold mb-2 text-base-content">{category.title}</h3>
                    <div className="flex flex-wrap justify-center gap-2 mt-2">
                      {category.skills.map((skill, sIndex) => (
                        <span key={sIndex} className={`badge badge-sm ${badgeClass} badge-outline`}>
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </motion.div>
      </div>
    </section>
  );
};

export default AboutSkills;