"use client";

import React from 'react';
import Image from 'next/image';
import Link from 'next/link';
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
  'Databricks': 'badge-accent',
  'Growth Analytics': 'badge-primary',
  'Analytics Engineering': 'badge-secondary',
  'Power BI': 'badge-primary',
  'Python': 'badge-success',
  'Data Science': 'badge-accent',
  'Predictive Modeling': 'badge-warning',
  'ETL': 'badge-warning',
  'React': 'badge-secondary',
  'Full-Stack': 'badge-info',
  'SQL': 'badge-info',
};

const featuredProjectsData: Project[] = [
  {
    id: 1,
    title: "Growth Analytics Platform (Dave & Buster's)",
    description: "Architected a scalable data platform in Databricks, unifying 5+ marketing sources into a single source of truth to power executive reporting and drive media efficiency.",
    imageUrl: "/images/dnb-project.png",
    tags: ["Databricks", "Growth Analytics", "Analytics Engineering", "Power BI", "ETL"],
    detailsUrl: "/projects/dnb-marketing-ecosystem",
  },
  {
    id: 2,
    title: 'Predictive Modeling Pipeline',
    description: 'Engineered a reusable Python pipeline for data ingestion, cleaning, and feature engineering, culminating in a predictive model to forecast key business outcomes.',
    imageUrl: '/images/data-pipeline.png',
    tags: ['Python', 'Data Science', 'Predictive Modeling', 'ETL'],
    githubUrl: 'https://github.com/Derek-Devs/PythonDataPipeline',
  },
  {
    id: 3,
    title: 'Full-Stack Insight Platform',
    description: 'Developed an interactive dashboard with a React front-end and a SQL back-end to analyze and visualize player sentiment data from the TTRPG community.',
    imageUrl: '/images/ttrpg-dash.png',
    tags: ['Full-Stack', 'React', 'SQL', 'Data Science'],
    detailsUrl: '/projects/TTRPGSentiments',
  },
];

const containerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.2 } },
};

const itemVariants = {
  hidden: { opacity: 0, y: 50 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" } },
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
              <div className="card bg-base-100 shadow-xl hover:shadow-2xl transition-shadow duration-300 flex flex-col w-full overflow-hidden">
                <figure className="h-48 overflow-hidden relative">
                  <Image
                    src={project.imageUrl}
                    alt={`Screenshot of the ${project.title} project`}
                    fill
                    sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
                    style={{ objectFit: 'cover' }}
                    className="transition-transform duration-300 hover:scale-105"
                    onError={(e) => {
                      (e.target as HTMLImageElement).src = `https://placehold.co/600x400/374151/ffffff?text=Image+Not+Found&font=lato`;
                    }}
                  />
                </figure>
                <div className="card-body flex flex-col flex-grow">
                  <h3 className="card-title text-xl font-semibold mb-1">{project.title}</h3>
                  <p className="text-sm text-base-content/80 mt-1 mb-4 flex-grow">{project.description}</p>

                  <div className="mb-4">
                    {project.tags.map((tag) => (
                      <span key={tag} className={`badge badge-outline ${tagColorMap[tag] || 'badge-ghost'} badge-md mr-2 mb-2 font-medium`}>
                        {tag}
                      </span>
                    ))}
                  </div>

                  <div className="card-actions justify-end mt-auto pt-2">
                    {project.detailsUrl && (
                      <Link href={project.detailsUrl} passHref legacyBehavior>
                        <a className="btn btn-primary btn-sm">
                          <FaExternalLinkAlt className="mr-1.5 h-3.5 w-3.5" />
                          View Case Study
                        </a>
                      </Link>
                    )}
                    {project.githubUrl && (
                      <a
                        href={project.githubUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn btn-secondary btn-sm btn-outline"
                        aria-label={`View GitHub repository for ${project.title}`}
                      >
                        <FaGithub className="mr-1.5 h-4 w-4" />
                        View Code
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