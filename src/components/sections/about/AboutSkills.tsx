"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { FaBullseye, FaSitemap, FaChartLine, FaPaintBrush, FaPython, FaBriefcase } from 'react-icons/fa';

interface SkillCategory {
  icon: React.ElementType;
  title: string;
  skills: string[];
  color: 'primary' | 'secondary' | 'accent';
}

const skillCategories: SkillCategory[] = [
  { 
    icon: FaBullseye, 
    title: "Strategy & Leadership", 
    skills: ["Data Strategy", "Team Leadership", "C-Suite Communication", "Roadmapping", "Mentorship", "Data Governance"], 
    color: 'primary' 
  },
  { 
    icon: FaSitemap, 
    title: "Data Architecture & Engineering", 
    skills: ["Databricks", "Google BigQuery", "Snowflake", "ETL/ELT Pipelines", "Data Modeling", "dbt"], 
    color: 'secondary' 
  },
  { 
    icon: FaChartLine, 
    title: "Predictive Analytics & Data Science", 
    skills: ["Demand Forecasting", "Experimentation (A/B)", "Marketing Mix Modeling", "Statistical Analysis", "Scikit-learn", "Growth Analytics"], 
    color: 'accent' 
  },
  { 
    icon: FaPaintBrush, 
    title: "BI & Data Storytelling", 
    skills: ["Power BI", "Tableau", "DAX", "Executive Dashboards", "Insight Generation", "Alteryx"], 
    color: 'secondary' 
  },
  { 
    icon: FaPython, 
    title: "Python & Automation", 
    skills: ["Python (Pandas, PySpark)", "Process Automation", "API Integration", "Web Scraping", "Custom Tooling"], 
    color: 'accent' 
  },
  { 
    icon: FaBriefcase, 
    title: "Business Acumen & Domain Expertise", 
    skills: ["Marketing & CRM", "Supply Chain", "Logistics Pricing", "E-commerce", "ROI Optimization", "Stakeholder Management"], 
    color: 'primary' 
  },
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

const badgeColorClasses = {
    primary: 'badge-primary',
    secondary: 'badge-secondary',
    accent: 'badge-accent',
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
          Core Capabilities
        </motion.h2>

        <motion.div
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 md:gap-8"
          variants={gridContainerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.1 }}
        >
          {skillCategories.map((category) => {
            const badgeClass = badgeColorClasses[category.color];
            const iconBgClass = `bg-${category.color}/10`;
            const iconTextClass = `text-${category.color}`;

            return (
              <motion.div
                key={category.title}
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
                      {category.skills.map((skill) => (
                        <span key={skill} className={`badge badge-sm ${badgeClass} badge-outline`}>
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