// src/components/sections/SkillsSection.tsx
"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { FaUsers } from 'react-icons/fa';
import { SiTableau, SiGooglebigquery, SiDatabricks, SiPython, SiGit } from "react-icons/si";

interface SkillCategory {
  title: string;
  skills: string[];
  icon: React.ReactNode;
}

// Moved outside component: Constant does not need to be redefined on each render
const badgeColors = [
  'badge-primary',
  'badge-secondary',
  'badge-accent',
  'badge-info',
  'badge-success',
  'badge-warning',
  'badge-error',
  'badge-outline badge-primary',
  'badge-outline badge-secondary',
  'badge-outline badge-accent',
];

const skillCategories: SkillCategory[] = [
  {
    title: "Data Analysis & Engineering",
    skills: ["Advanced SQL", "Python", "ETL Architecture", "Data Modeling", "Metrics Development"],
    icon: <SiGooglebigquery className="inline mr-2 h-5 w-5" />
  },
  {
    title: "Visualization & Reporting",
    skills: ["Power BI", "Tableau", "DAX", "Alteryx", "Advanced Excel"],
    icon: <SiTableau className="inline mr-2 h-5 w-5" />
  },
  {
    title: "Programming",
    skills: ["Python", "SQL", "JavaScript", "TypeScript", "HTML/CSS"],
    icon: <SiPython className="inline mr-2 h-5 w-5" />
  },
  {
    title: "Cloud & Databases",
    skills: ["AWS", "Google BigQuery", "MongoDB", "Databricks"],
    icon: <SiDatabricks className="inline mr-2 h-5 w-5" />
  },
  {
    title: "Tools & Methodologies",
    skills: ["Git", "Agile Project Management", "A/B Testing", "Web Scraping", "AI Development Tools"],
    icon: <SiGit className="inline mr-2 h-5 w-5" />
  },
  {
    title: "Professional",
    skills: ["Strategic Problem-Solving", "Cross-functional Collaboration", "Executive Communication", "Team Leadership"],
    icon: <FaUsers className="inline mr-2 h-5 w-5" />
  },
];

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.08 } },
};

const itemVariants = {
  hidden: { opacity: 0, y: 10 },
  visible: { opacity: 1, y: 0 },
};

const SkillsSection: React.FC = () => {
  return (
    <section id="skills" className="py-16 md:py-24 bg-base-200">
      <div className="container mx-auto px-4">
        <motion.h2
          className="text-3xl md:text-4xl font-bold text-center mb-12 text-base-content"
          initial={{ opacity: 0, y: -20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.5 }}
          transition={{ duration: 0.5 }}
        >
          Skills & Technologies
        </motion.h2>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {skillCategories.map((category, index) => {
            const badgeColorClass = badgeColors[index % badgeColors.length];

            return (
              <motion.div
                key={category.title}
                className="p-6 bg-base-100 rounded-lg shadow-md flex flex-col"
                initial={{ opacity: 0, scale: 0.95 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true, amount: 0.2 }}
                transition={{ duration: 0.4, delay: index * 0.1 }}
              >
                <h3 className="text-xl font-semibold mb-4 text-base-content flex items-center">
                  {category.icon}
                  {category.title}
                </h3>
                <motion.div
                  className="flex flex-wrap gap-2 mt-auto"
                  variants={containerVariants}
                  initial="hidden"
                  whileInView="visible"
                  viewport={{ once: true, amount: 0.2 }}
                >
                  {category.skills.map((skill) => (
                    <motion.span
                      key={skill}
                      className={`badge badge-md ${badgeColorClass}`}
                      variants={itemVariants}
                    >
                      {skill}
                    </motion.span>
                  ))}
                </motion.div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
};

export default SkillsSection;