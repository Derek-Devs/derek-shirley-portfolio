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
};

const projectsData: Project[] = [
  {
    id: 1,
    title: 'TTRPG Player Insights',
    description: 'Developed a dashboard to display player sentiments in the TTRPG community.',
    imageUrl: '/images/ttrpg-dash.png',
    tags: ['Data Analysis', 'React', 'Typescript', 'SQL'],
    detailsUrl: '/TTRPGSentiments',
  },
  {
    id: 2,
    title: 'Video Game Sales Dashboard',
    description: 'Built a dashboard to display insights from a video game sales dataset.',
    imageUrl: '/images/video-game-dash.png',
    tags: ['Data Analysis', 'React', 'Typescript', 'SQL'],
    detailsUrl: '/videoGameSales',
  },
  {
    id: 3,
    title: 'Customer Insights Dashboard',
    description: 'Drew insights from customer data to identify trends and opportunities.',
    imageUrl: '/images/customer-insights.png',
    tags: ['Data Analysis', 'React', 'Typescript'],
    detailsUrl: '/customer-dashboard'
  },
  {
    id: 4,
    title: 'Python Data Pipeline',
    description: 'Utilized a variety of python libraries and AI assistance to build a comprehensive, object-oriented data analysis pipeline for professional data scientists and analysts.',
    imageUrl: '/images/data-pipeline.png',
    tags: ['Python', 'Pandas', 'Scikit-learn', 'Data Analysis'], 
    githubUrl: 'https://github.com/Derek-Devs/PythonDataPipeline'
  },
  {
    id: 5,
    title: 'Advanced SQL Examples',
    description: 'A collection of advanced SQL scripts that demonstrate various database design, analysis, and manipulation techniques.',
    imageUrl: '/images/sql-examples.png',
    tags: ['SQL', 'GitHub', 'Data Analysis'], 
    githubUrl: 'https://github.com/Derek-Devs/AdvancedSQLExamples'
  },
  {
    id: 6,
    title: 'Google Maps Distance and Time to Travel Plugin',
    description: 'Two separate scripts meant to aid others in finding the distance between two points within Google Sheets, or finding the time to travel between these points.',
    imageUrl: '/images/google-maps.png',
    tags: ['Javascript', 'Google Sheets', 'API'],
    githubUrl: 'https://github.com/Derek-Devs/google-maps-sheets' 
  },
];

export default function ProjectList() {
  return (
    <section className="py-16 md:py-20 bg-base-200" id="projects">
      <div className="container mx-auto px-4">
        <h2 className="text-3xl md:text-4xl font-bold text-center mb-4">My Projects 🚀</h2>
        <p className="text-center text-lg md:text-xl mb-12 text-base-content/70">
          Here are some of the projects I&apos;ve enjoyed working on.
        </p>

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
                  {project.detailsUrl && project.detailsUrl !== '#' && (
                    <a href={project.detailsUrl} className="btn btn-sm btn-primary">
                      View Details
                    </a>
                  )}
                  {project.githubUrl && project.githubUrl !== '#' && (
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