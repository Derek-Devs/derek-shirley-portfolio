// src/components/sections/projects/ProjectList.tsx
import React from 'react';
import Image from 'next/image'; 

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
  'Data Architecture': 'badge-primary',
  'Leadership': 'badge-primary',
  'Power BI': 'badge-primary',
  'Databricks': 'badge-accent',
  'React': 'badge-secondary',
  'Typescript': 'badge-accent',
  'SQL': 'badge-info',
  'Python': 'badge-success',
  'Pandas': 'badge-success',
  'Scikit-learn': 'badge-warning',
  'GitHub': 'badge-neutral',
  'Javascript': 'badge-warning',
  'Google Sheets': 'badge-success',
  'API': 'badge-error',
  'ETL': 'badge-warning',
  'Automation': 'badge-accent',
};

const projectsData: Project[] = [
  {
    id: 0,
    title: "Enterprise Marketing Data Ecosystem (Dave & Buster's)",
    description: "Architected a new, centralized marketing data platform from scratch in Databricks, unifying 5+ disparate sources to create a single source of truth for all marketing KPIs and executive reporting.",
    imageUrl: "/images/dnb-project.png",
    tags: ["Data Architecture", "Leadership", "Databricks", "Power BI", "Python", "ETL"],
    detailsUrl: "/projects/dnb-marketing-ecosystem",
  },
  {
    id: 1,
    title: 'Market Sentiment Analysis Platform',
    description: 'Architected an interactive dashboard to analyze and visualize player sentiment data from the TTRPG community, providing strategic insights into market trends and player preferences.',
    imageUrl: '/images/ttrpg-dash.png',
    tags: ['Data Analysis', 'React', 'Typescript', 'SQL'],
    detailsUrl: '/TTRPGSentiments',
  },
  {
    id: 2,
    title: 'Global Video Game Sales Analysis',
    description: 'Developed a comprehensive analytics dashboard to dissect global video game sales data, identifying key drivers of commercial success across different genres, platforms, and regions.',
    imageUrl: '/images/video-game-dash.png',
    tags: ['Data Analysis', 'React', 'Typescript', 'SQL'],
    detailsUrl: '/videoGameSales',
  },
  {
    id: 3,
    title: 'Customer Segmentation & LTV Analysis',
    description: 'Built a dynamic dashboard to perform customer segmentation and analyze purchasing behavior, uncovering key trends for targeted marketing and customer retention strategies.',
    imageUrl: '/images/customer-insights.png',
    tags: ['Data Analysis', 'React', 'Typescript'],
    detailsUrl: '/customer-dashboard'
  },
  {
    id: 4,
    title: 'Object-Oriented Python ETL Framework',
    description: 'Engineered a reusable, object-oriented ETL pipeline in Python, designed to provide a robust framework for data ingestion, cleaning, and analysis for data science workflows.',
    imageUrl: '/images/data-pipeline.png',
    tags: ['Python', 'Pandas', 'Scikit-learn', 'ETL'], 
    githubUrl: 'https://github.com/Derek-Devs/PythonDataPipeline'
  },
  {
    id: 5,
    title: 'Advanced SQL for Data Architecture',
    description: 'A curated collection of advanced SQL scripts showcasing complex techniques for data architecture, performance optimization, and in-depth business analysis.',
    imageUrl: '/images/sql-examples.png',
    tags: ['SQL', 'GitHub', 'Data Analysis'], 
    githubUrl: 'https://github.com/Derek-Devs/AdvancedSQLExamples'
  },
  {
    id: 6,
    title: 'Google Sheets API Automation for Logistics',
    description: 'Developed custom JavaScript functions for Google Sheets that leverage the Google Maps API to automate logistics calculations, such as travel time and distance between multiple points.',
    imageUrl: '/images/google-maps.png',
    tags: ['Javascript', 'Google Sheets', 'API', 'Automation'],
    githubUrl: 'https://github.com/Derek-Devs/google-maps-sheets' 
  },
];

export default function ProjectList() {
  return (
    <section className="py-16 md:py-20 bg-base-200" id="projects">
      <div className="container mx-auto px-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
          {projectsData.map((project) => (
            <div key={project.id} className="card bg-base-100 shadow-xl hover:shadow-2xl transition-shadow duration-300 flex flex-col">
              <figure className="h-48 overflow-hidden relative">
                <Image
                  src={project.imageUrl}
                  alt={project.title}
                  fill
                  sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw" 
                  style={{ objectFit: 'cover' }} 
                  className="transition-transform duration-300 hover:scale-105"
                  onError={(e) => {
                    const target = e.currentTarget as HTMLImageElement;
                    target.srcset = ''; 
                    target.src = `https://placehold.co/600x400/374151/ffffff?text=Image+Not+Found&font=lato`;
                  }}
                />
              </figure>
              <div className="card-body flex flex-col flex-grow">
                <h3 className="card-title text-xl font-semibold mb-1">{project.title}</h3>
                <p className="text-sm text-base-content/80 mt-1 mb-4 flex-grow">{project.description}</p>
                <div className="mb-4">
                  {project.tags.map((tag) => {
                    const colorClass = tagColorMap[tag] || 'badge-ghost';
                    return (
                      <span key={tag} className={`badge badge-outline ${colorClass} badge-md mr-2 mb-2 font-medium`}>
                        {tag}
                      </span>
                    );
                  })}
                </div>
                <div className="card-actions justify-end mt-auto">
                  {project.detailsUrl && (
                    <a href={project.detailsUrl} className="btn btn-sm btn-primary">
                      View Case Study
                    </a>
                  )}
                  {project.githubUrl && (
                    <a href={project.githubUrl} target="_blank" rel="noopener noreferrer" className="btn btn-sm btn-outline btn-secondary">
                      GitHub
                    </a>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}