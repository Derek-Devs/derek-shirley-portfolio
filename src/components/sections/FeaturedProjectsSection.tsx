// src/components/sections/FeaturedProjectsSection.tsx
"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { FaExternalLinkAlt, FaGithub } from 'react-icons/fa';

interface Project {
  id: number; 
  title: string;
  description: string;
  imageUrl: string;
  tags: string[]; 
  detailsUrl?: string; 
  githubUrl?: string; 
}


const tagColorMap: { [key: string]: string } = {
  'Data Analysis': 'badge-primary',
  'React': 'badge-secondary',
  'Typescript': 'badge-accent', 
  'TypeScript': 'badge-accent',
  'SQL': 'badge-info',
  'Python': 'badge-success',
  'Pandas': 'badge-success',
  'Scikit-learn': 'badge-warning',
  'GitHub': 'badge-neutral',
  'Javascript': 'badge-warning',
  'Google Sheets': 'badge-success',
  'API': 'badge-error',

  'Next.js': 'badge-primary',
  'Tailwind CSS': 'badge-info',
  'Daisy UI': 'badge-secondary',
  'Framer Motion': 'badge-accent',
  'Power BI': 'badge-primary',
  'DAX': 'badge-info',          
  'Data Modeling': 'badge-accent',
  'Data Visualization': 'badge-secondary', 
};

const featuredProjectsData: Project[] = [
  {
    id: 1,
    title: "Personal Portfolio (DerekDevs.com)",
    description: "This website! A full-stack application showcasing my development journey, built with Next.js, React, TypeScript, and styled with Tailwind CSS & Daisy UI.",
    imageUrl: "/images/portfolio.png",
    tags: ["Next.js", "React", "TypeScript", "Tailwind CSS", "Daisy UI", "Framer Motion"],
    detailsUrl: "/", 
    githubUrl: "https://github.com/Derek-Devs/derekdevs", 
  },
  {
    id: 2, 
    title: 'Python Data Pipeline',
    description: 'Utilized a variety of Python libraries and AI assistance to build a comprehensive, object-oriented data analysis pipeline for data scientists and analysts.',
    imageUrl: '/images/data-pipeline.png',
    tags: ['Python', 'Pandas', 'Scikit-learn', 'Data Analysis'],
    githubUrl: 'https://github.com/Derek-Devs/PythonDataPipeline',
  },
  {
    id: 3, 
    title: 'TTRPG Player Insights Dashboard',
    description: 'Developed an interactive dashboard to display player sentiments and trends within the TTRPG community using React, TypeScript, and Chart.js.',
    imageUrl: '/images/ttrpg-dash.png',
    tags: ['Data Analysis', 'React', 'TypeScript', 'Chart.js'], 
    detailsUrl: '/TTRPGSentiments',
    
  },
];

const containerVariants = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.2,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 50 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.5,
      ease: "easeOut",
    },
  },
};

const FeaturedProjectsSection: React.FC = () => {
  return (
    <section id="featured-projects" className="py-16 md:py-20 bg-base-200"> 
      <div className="container mx-auto px-4">
        <motion.h2
          className="text-3xl md:text-4xl font-bold text-center mb-12 text-base-content"
          initial={{ opacity: 0, y: -20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.5 }}
          transition={{ duration: 0.5 }}
        >
          Featured Projects ✨
        </motion.h2>

        <motion.div
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8" 
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.1 }}
        >
          {featuredProjectsData.map((project) => (
            <motion.div key={project.id} variants={itemVariants} className="flex"> 
              <div className="card bg-base-100 shadow-xl hover:shadow-2xl transition-shadow duration-300 flex flex-col w-full">
                <figure className="h-48 overflow-hidden"> 
                  <img
                    src={project.imageUrl}
                    alt={project.title}
                    className="h-full w-full object-cover transition-transform duration-300 hover:scale-105"
                    onError={(e) => {
                      (e.target as HTMLImageElement).src = `https://placehold.co/600x400/374151/ffffff?text=Image+Not+Found&font=lato`;
                      (e.target as HTMLImageElement).alt = `${project.title} - Image Not Found`;
                    }}
                  />
                </figure>
                <div className="card-body flex flex-col flex-grow">
                  <h3 className="card-title text-xl font-semibold mb-1">{project.title}</h3>
                  <p className="text-sm text-base-content/80 mt-1 mb-4 flex-grow">{project.description}</p>

                  <div className="mb-4"> 
                    {project.tags.map((tag) => {
                      const colorClass = tagColorMap[tag.toLowerCase()] || tagColorMap[tag] || 'badge-ghost'; 
                      return (
                        <span key={tag} className={`badge badge-outline ${colorClass} badge-md mr-2 mb-2 font-medium`}>
                          {tag}
                        </span>
                      );
                    })}
                  </div>

                  <div className="card-actions justify-end mt-auto pt-2"> {/* Matched button section structure, adjusted pt */}
                    {project.detailsUrl && project.detailsUrl !== '#' && (
                      <a
                        href={project.detailsUrl}
                        target={project.detailsUrl.startsWith('/') ? '_self' : '_blank'} // Open internal links in self, external in new tab
                        rel="noopener noreferrer"
                        className="btn btn-primary btn-sm" // Primary button for details/live
                        aria-label={`View details for ${project.title}`}
                      >
                        <FaExternalLinkAlt className="mr-1.5 h-3.5 w-3.5" /> {/* Adjusted icon margin and size */}
                        {project.detailsUrl.startsWith('/') ? 'View Project' : 'Live Demo'}
                      </a>
                    )}
                    {project.githubUrl && project.githubUrl !== '#' && (
                      <a
                        href={project.githubUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn btn-secondary btn-sm btn-outline" // Secondary outline for GitHub
                        aria-label={`View GitHub repository for ${project.title}`}
                      >
                        <FaGithub className="mr-1.5 h-4 w-4" />  {/* Adjusted icon margin and size */}
                        GitHub
                      </a>
                    )}
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
};

export default FeaturedProjectsSection;