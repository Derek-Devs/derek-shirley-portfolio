import React from 'react';
import DataAnalysisPipelinePortfolio from '../../components/DataPipeline';
import { Metadata } from 'next';
import Header from '../../components/Header';
import Footer from '../../components/Footer';

// Define metadata for SEO
export const metadata: Metadata = {
  title: 'Advanced Data Analysis Pipeline | Portfolio',
  description: 'A comprehensive Python data analysis pipeline showcasing ETL, statistical analysis, visualization and reporting capabilities.',
  keywords: 'data analysis, python, ETL, data visualization, statistical analysis, portfolio',
};

export default function DataAnalysisPage() {
  return (
    <>
      <Header />
      <main className="min-h-screen py-12 bg-gray-900">
        <DataAnalysisPipelinePortfolio />
      </main>
      <Footer />
    </>
  );
}