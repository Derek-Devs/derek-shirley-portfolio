// src/app/projects/dnb-marketing-ecosystem/page.tsx
"use client";

import React from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
// Corrected and added new icon imports
import { FaArrowRight, FaBullseye, FaChartBar, FaCheckCircle, FaDatabase, FaLayerGroup, FaLink, FaStar } from 'react-icons/fa';
import { SiDatabricks, SiSalesforce, SiAdobe, SiGoogleads, SiMeta, SiPython } from 'react-icons/si';
import { TbLayoutDashboard } from 'react-icons/tb'; // Guaranteed replacement for Power BI
import { VscDatabase } from 'react-icons/vsc'; // Guaranteed replacement for SQL Server

const StatCard = ({ icon, value, label }: { icon: React.ReactNode, value: string, label: string }) => (
  <motion.div
    className="bg-base-100 p-6 rounded-lg shadow-xl text-center border border-base-300"
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.5 }}
  >
    <div className="text-4xl text-primary mx-auto mb-3">{icon}</div>
    <div className="text-3xl font-bold text-base-content">{value}</div>
    <div className="text-md text-base-content/70 mt-1">{label}</div>
  </motion.div>
);

const DnbEcosystemPage: React.FC = () => {
  return (
    <main className="flex-grow bg-base-100 text-base-content">
      
      {/* Hero Section */}
      <section className="bg-base-200 pt-20 pb-32 md:pt-28 md:pb-40 text-center">
        <motion.div 
          className="container mx-auto px-4"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7 }}
        >
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight">Enterprise Marketing Data Ecosystem</h1>
          <p className="mt-4 text-lg md:text-xl text-base-content/80 max-w-3xl mx-auto">
            Architecting a single source of truth to power strategic decisions at Dave & Buster&apos;s.
          </p>
        </motion.div>
      </section>

      {/* Stats Section */}
      <section className="-mt-20 md:-mt-24 relative z-10">
        <div className="container mx-auto px-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8 max-w-5xl mx-auto">
            <StatCard icon={<FaCheckCircle />} value="35%+" label="Reduction in Manual Reporting" />
            <StatCard icon={<FaLink />} value="5+" label="Disparate Data Sources Unified" />
            <StatCard icon={<FaStar />} value="1st Ever" label="True Cross-Channel ROI Analysis" />
          </div>
        </div>
      </section>

      <div className="container mx-auto px-4 py-16 md:py-24">
        <div className="max-w-4xl mx-auto space-y-16">

          {/* The Challenge Section */}
          <motion.section
            initial={{ opacity: 0, x: -50 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, amount: 0.3 }}
            transition={{ duration: 0.6 }}
          >
            <h2 className="text-3xl font-bold mb-4 text-secondary">The Challenge</h2>
            <div className="prose prose-lg max-w-none">
              <p>
                When I joined Dave & Buster&apos;s, the marketing analytics function was operating with fragmented data across five major siloed platforms. This made it impossible to get a clear, trustworthy view of the marketing funnel, measure cross-channel ROI, and resulted in over 35% of analyst time being spent on manual data wrangling rather than strategic analysis. Key business initiatives like the Leaderboard program and Summer Season Pass lacked a unified performance measurement framework.
              </p>
            </div>
          </motion.section>

          {/* The Solution & Architecture Section */}
          <motion.section
            initial={{ opacity: 0, x: 50 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, amount: 0.3 }}
            transition={{ duration: 0.6 }}
          >
            <h2 className="text-3xl font-bold mb-6 text-secondary">The Solution & Architecture</h2>
            <div className="prose prose-lg max-w-none mb-8">
              <p>
                As the lead, my objective was to architect and build a new, centralized data ecosystem from the ground up. I designed a modern ELT architecture using Databricks as the central hub to unify all marketing data, create a single source of truth, and enable self-service analytics through Power BI.
              </p>
            </div>

            {/* Visual Architecture Diagram */}
            <div className="mt-10 p-6 md:p-8 bg-base-200 rounded-lg shadow-inner">
              <div className="flex flex-col md:flex-row items-center justify-between gap-8">
                
                <div className="w-full md:w-1/4">
                  <h3 className="font-bold text-center mb-4 text-lg">Data Sources</h3>
                  <div className="space-y-3">
                    <div className="card bg-base-100 shadow-sm p-3 flex-row items-center gap-3"><SiSalesforce className="text-xl text-blue-500 flex-shrink-0" /> <span className="text-sm font-medium">SFMC</span></div>
                    <div className="card bg-base-100 shadow-sm p-3 flex-row items-center gap-3"><SiAdobe className="text-xl text-red-500 flex-shrink-0" /> <span className="text-sm font-medium">Adobe Analytics</span></div>
                    <div className="card bg-base-100 shadow-sm p-3 flex-row items-center gap-3"><SiGoogleads className="text-xl text-green-500 flex-shrink-0" /> <span className="text-sm font-medium">Google Ads / GA4</span></div>
                    <div className="card bg-base-100 shadow-sm p-3 flex-row items-center gap-3"><SiMeta className="text-xl text-blue-600 flex-shrink-0" /> <span className="text-sm font-medium">Meta Ads</span></div>
                    <div className="card bg-base-100 shadow-sm p-3 flex-row items-center gap-3"><FaDatabase className="text-xl text-gray-500 flex-shrink-0" /> <span className="text-sm font-medium">Sprout Social</span></div>
                  </div>
                </div>

                <div className="w-full md:w-1/2 flex flex-col items-center">
                  <FaArrowRight className="text-3xl text-primary hidden md:block" />
                  <FaArrowRight className="text-3xl text-primary rotate-90 md:hidden" />
                  <div className="card bg-primary text-primary-content shadow-lg p-4 text-center my-4">
                    <h4 className="font-bold mb-2 flex items-center justify-center gap-2"><SiDatabricks /> Databricks Platform</h4>
                    <div className="space-y-1 text-xs">
                      <p className="badge badge-neutral badge-outline">ETL/ELT Pipelines (Python/SQL)</p>
                      <p className="badge badge-neutral badge-outline">Data Modeling & Unification</p>
                      <p className="badge badge-neutral badge-outline">Single Source of Truth</p>
                    </div>
                  </div>
                  <FaArrowRight className="text-3xl text-primary hidden md:block" />
                  <FaArrowRight className="text-3xl text-primary rotate-90 md:hidden" />
                </div>

                <div className="w-full md:w-1/4">
                  <h3 className="font-bold text-center mb-4 text-lg">Business Impact</h3>
                  <div className="space-y-3">
                     <div className="card bg-base-100 shadow-sm p-3 flex-row items-center gap-3"><TbLayoutDashboard className="text-xl text-yellow-500 flex-shrink-0" /> <span className="text-sm font-medium">Executive Dashboards</span></div>
                     <div className="card bg-base-100 shadow-sm p-3 flex-row items-center gap-3"><FaChartBar className="text-xl text-secondary flex-shrink-0" /> <span className="text-sm font-medium">Leaderboard Analytics</span></div>
                     <div className="card bg-base-100 shadow-sm p-3 flex-row items-center gap-3"><FaBullseye className="text-xl text-secondary flex-shrink-0" /> <span className="text-sm font-medium">Campaign ROI Analysis</span></div>
                     <div className="card bg-base-100 shadow-sm p-3 flex-row items-center gap-3"><FaLayerGroup className="text-xl text-secondary flex-shrink-0" /> <span className="text-sm font-medium">Self-Service Analytics</span></div>
                  </div>
                </div>

              </div>
            </div>
          </motion.section>
          
          {/* The Impact Section */}
          <motion.section
            initial={{ opacity: 0, x: -50 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, amount: 0.3 }}
            transition={{ duration: 0.6 }}
          >
            <h2 className="text-3xl font-bold mb-6 text-secondary">The Results & Impact</h2>
            <div className="prose prose-lg max-w-none mb-4">
              <p>The new platform became the definitive source of truth for the entire marketing organization, delivering significant and measurable value.</p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-base-200 p-4 rounded-lg flex items-start gap-4">
                <FaCheckCircle className="text-success text-2xl mt-1 flex-shrink-0" />
                <div>
                  <h4 className="font-bold">Reduced Manual Reporting by 35%+</h4>
                  <p className="text-sm text-base-content/80">Freed up the team to focus on high-value strategic work instead of data wrangling.</p>
                </div>
              </div>
              <div className="bg-base-200 p-4 rounded-lg flex items-start gap-4">
                <FaCheckCircle className="text-success text-2xl mt-1 flex-shrink-0" />
                <div>
                  <h4 className="font-bold">Enabled Cross-Channel ROI Analysis</h4>
                  <p className="text-sm text-base-content/80">Led to more efficient ad spend allocation and a clearer understanding of customer acquisition.</p>
                </div>
              </div>
              <div className="bg-base-200 p-4 rounded-lg flex items-start gap-4">
                <FaCheckCircle className="text-success text-2xl mt-1 flex-shrink-0" />
                <div>
                  <h4 className="font-bold">Unified Measurement Framework</h4>
                  <p className="text-sm text-base-content/80">Provided consistent metrics for key initiatives like the Leaderboard and Summer Season Pass programs.</p>
                </div>
              </div>
              <div className="bg-base-200 p-4 rounded-lg flex items-start gap-4">
                <FaCheckCircle className="text-success text-2xl mt-1 flex-shrink-0" />
                <div>
                  <h4 className="font-bold">Increased Data Trust & Adoption</h4>
                  <p className="text-sm text-base-content/80">Empowered the marketing team with reliable, self-service dashboards in Power BI.</p>
                </div>
              </div>
            </div>
          </motion.section>

          {/* Technologies Used */}
          <motion.section
            initial={{ opacity: 0, y: 50 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.3 }}
            transition={{ duration: 0.6 }}
          >
            <h2 className="text-3xl font-bold mb-6 text-secondary">Technologies Used</h2>
            <div className="flex flex-wrap gap-4">
              <span className="badge badge-primary badge-lg p-4"><SiDatabricks className="mr-2"/>Databricks</span>
              <span className="badge badge-primary badge-lg p-4"><TbLayoutDashboard className="mr-2"/>Power BI</span>
              <span className="badge badge-secondary badge-lg p-4"><SiPython className="mr-2"/>Python (Pandas)</span>
              <span className="badge badge-secondary badge-lg p-4"><VscDatabase className="mr-2"/>Advanced SQL</span>
              <span className="badge badge-accent badge-lg p-4"><SiSalesforce className="mr-2"/>SFMC</span>
              <span className="badge badge-accent badge-lg p-4"><SiAdobe className="mr-2"/>Adobe Analytics</span>
            </div>
          </motion.section>

          <div className="text-center pt-12">
            <Link href="/projects" className="btn btn-outline btn-secondary">
              Back to All Projects
            </Link>
          </div>

        </div>
      </div>
    </main>
  );
};

export default DnbEcosystemPage;