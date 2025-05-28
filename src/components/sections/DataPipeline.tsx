// src/components/DataPipeline.tsx
"use client"
import React, { useState } from 'react';
import { FiGithub, FiDownload, FiInfo, FiCode, FiExternalLink } from 'react-icons/fi';

const DataPipeline = () => {
  const [activeTab, setActiveTab] = useState('overview');

  const features = [
    { name: "Data Extraction", description: "Pull data from multiple sources including APIs, CSV files, JSON, and databases" },
    { name: "Data Cleaning", description: "Comprehensive tools for preprocessing, filtering, and transforming data" },
    { name: "EDA", description: "Automated exploratory data analysis with statistical summaries" },
    { name: "Statistical Analysis", description: "Support for t-tests, ANOVA, chi-square, correlation, and regression" },
    { name: "Visualization", description: "Generate various plot types with customization options" },
    { name: "Reporting", description: "Create HTML reports with the analysis results and visualizations" },
    { name: "Export", description: "Export data and results to various formats (CSV, Excel, JSON, HTML)" }
  ];

  const useCases = [
    "Sales performance analysis across regions and time periods",
    "Customer segmentation and behavior analysis",
    "Marketing campaign effectiveness evaluation",
    "Product performance and comparison analysis",
    "Operational efficiency analysis and reporting",
    "A/B testing analysis with statistical significance",
    "Financial trend analysis and forecasting"
  ];

  return (
    <div className="w-full max-w-6xl mx-auto p-4 space-y-8 text-gray-200">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-100">Advanced Data Analysis Pipeline</h1>
          <p className="text-lg text-gray-300 mt-2">
            A comprehensive Python toolkit for end-to-end data analysis workflows
          </p>
        </div>
        <div className="flex gap-2">
          <button 
            className="btn btn-primary flex items-center gap-2"
            onClick={() => window.open('https://github.com/yourusername/data-analysis-pipeline', '_blank')}
          >
            <FiGithub size={18} />
            <span>View on GitHub</span>
          </button>
          <button 
            className="btn btn-outline btn-secondary flex items-center gap-2"
            onClick={() => {
              // Create a link to download the file
              const link = document.createElement('a');
              link.href = '/code/DataAnalysisPipeline.py';
              link.download = 'DataAnalysisPipeline.py';
              document.body.appendChild(link);
              link.click();
              document.body.removeChild(link);
            }}
          >
            <FiDownload size={18} />
            <span>Download</span>
          </button>
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card col-span-1 md:col-span-4 bg-gray-800 shadow-xl border border-gray-700">
          <div className="card-body">
            <div className="flex flex-wrap gap-2 mb-2">
              <span className="badge badge-primary">Python</span>
              <span className="badge badge-success">Data Analysis</span>
              <span className="badge badge-secondary">Statistics</span>
              <span className="badge badge-accent">Visualization</span>
              <span className="badge badge-info">ETL</span>
              <span className="badge badge-warning">Reporting</span>
            </div>
            <h2 className="card-title text-gray-100">About This Project</h2>
            <p className="text-sm text-gray-300">
              This modular data analysis pipeline showcases advanced Python programming and data analysis skills.
            </p>
            
            {/* DaisyUI Tabs */}
            <div className="tabs tabs-boxed mt-4 bg-gray-700">
              <a 
                className={`tab ${activeTab === 'overview' ? 'tab-active' : ''} text-gray-200`}
                onClick={() => setActiveTab('overview')}
              >
                Overview
              </a>
              <a 
                className={`tab ${activeTab === 'features' ? 'tab-active' : ''} text-gray-200`}
                onClick={() => setActiveTab('features')}
              >
                Features
              </a>
              <a 
                className={`tab ${activeTab === 'usecases' ? 'tab-active' : ''} text-gray-200`}
                onClick={() => setActiveTab('usecases')}
              >
                Use Cases
              </a>
              <a 
                className={`tab ${activeTab === 'architecture' ? 'tab-active' : ''} text-gray-200`}
                onClick={() => setActiveTab('architecture')}
              >
                Architecture
              </a>
            </div>
            
            <div className="mt-6 text-gray-300">
              {activeTab === 'overview' && (
                <div className="space-y-4">
                  <p>
                    The Advanced Data Analysis Pipeline is a comprehensive Python toolkit designed for professional data analysts and data scientists. 
                    This project demonstrates my expertise in building modular, maintainable, and extensible data analysis solutions 
                    that can handle real-world analytical challenges.
                  </p>
                  <p>
                    The pipeline implements a full ETL (Extract, Transform, Load) workflow with extensive options for statistical 
                    analysis, visualization, and reporting. It's designed with flexibility in mind, allowing for configuration 
                    through external JSON files and providing detailed logging for monitoring and debugging.
                  </p>
                  <p>
                    Key highlights of this implementation include:
                  </p>
                  <ul className="list-disc pl-6 space-y-2">
                    <li>Object-oriented design with clear separation of concerns</li>
                    <li>Comprehensive error handling and logging</li>
                    <li>Support for multiple data sources and formats</li>
                    <li>Extensive statistical analysis capabilities</li>
                    <li>Customizable data visualization</li>
                    <li>Automated HTML report generation</li>
                    <li>Multiple export options for results and preprocessed data</li>
                  </ul>

                  <div className="bg-gray-700 p-4 rounded-md mt-6 flex items-center gap-3">
                    <FiCode size={24} className="text-primary" />
                    <div>
                      <p className="font-medium text-gray-200">Want to see the full code?</p>
                      <p className="text-sm text-gray-300">Check out the complete implementation on GitHub to explore all the features and capabilities.</p>
                    </div>
                    <button 
                      className="btn btn-primary btn-sm ml-auto"
                      onClick={() => window.open('https://github.com/yourusername/data-analysis-pipeline', '_blank')}
                    >
                      <FiExternalLink size={16} className="mr-1" />
                      GitHub Repo
                    </button>
                  </div>
                </div>
              )}
              
              {activeTab === 'features' && (
                <div className="space-y-6">
                  <p>
                    This pipeline showcases a wide range of data analysis capabilities, packaged in a maintainable and extensible architecture.
                  </p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {features.map((feature, idx) => (
                      <div key={idx} className="card bg-gray-700 shadow-sm border border-gray-600">
                        <div className="card-body p-4">
                          <h3 className="card-title text-gray-100 text-lg">{feature.name}</h3>
                          <p className="text-sm text-gray-300">{feature.description}</p>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="bg-gray-700 p-4 rounded-md mt-6 flex items-center gap-3">
                    <FiGithub size={24} className="text-primary" />
                    <p className="text-sm text-gray-300">
                      Explore all these features in detail by checking out the source code on GitHub.
                    </p>
                    <button 
                      className="btn btn-primary btn-sm ml-auto"
                      onClick={() => window.open('https://github.com/yourusername/data-analysis-pipeline', '_blank')}
                    >
                      View Repository
                    </button>
                  </div>
                </div>
              )}
              
              {activeTab === 'usecases' && (
                <div className="space-y-4">
                  <p>
                    This data analysis pipeline can be applied across various business domains and analytical scenarios:
                  </p>
                  <div className="grid grid-cols-1 gap-2">
                    {useCases.map((useCase, idx) => (
                      <div key={idx} className="flex items-start gap-2 p-3 bg-gray-700 rounded-md">
                        <FiInfo size={20} className="text-info mt-0.5" />
                        <p>{useCase}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {activeTab === 'architecture' && (
                <div className="space-y-4">
                  <p>
                    The pipeline follows a modular design pattern with clearly separated responsibilities:
                  </p>
                  <div className="overflow-hidden rounded-md border border-gray-600">
                    <div className="bg-gray-700 p-3 border-b border-gray-600">
                      <h3 className="font-medium text-gray-100">Architecture Diagram</h3>
                    </div>
                    <div className="p-6 bg-gray-800">
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="space-y-2 border rounded-md p-4 bg-blue-900 border-blue-700">
                          <h4 className="font-semibold text-blue-300">1. Data Extraction</h4>
                          <p className="text-sm text-gray-300">Multiple source adapters for CSV, JSON, API, and databases</p>
                        </div>
                        <div className="space-y-2 border rounded-md p-4 bg-green-900 border-green-700">
                          <h4 className="font-semibold text-green-300">2. Data Cleaning</h4>
                          <p className="text-sm text-gray-300">Preprocessing, filtering, and transformation operations</p>
                        </div>
                        <div className="space-y-2 border rounded-md p-4 bg-yellow-900 border-yellow-700">
                          <h4 className="font-semibold text-yellow-300">3. Analysis</h4>
                          <p className="text-sm text-gray-300">EDA, statistical tests, and correlation analysis</p>
                        </div>
                        <div className="space-y-2 border rounded-md p-4 bg-purple-900 border-purple-700">
                          <h4 className="font-semibold text-purple-300">4. Visualization</h4>
                          <p className="text-sm text-gray-300">Multiple chart types with customization options</p>
                        </div>
                        <div className="space-y-2 border rounded-md p-4 bg-red-900 border-red-700">
                          <h4 className="font-semibold text-red-300">5. Reporting</h4>
                          <p className="text-sm text-gray-300">Interactive HTML report generation with findings</p>
                        </div>
                        <div className="space-y-2 border rounded-md p-4 bg-indigo-900 border-indigo-700">
                          <h4 className="font-semibold text-indigo-300">6. Export</h4>
                          <p className="text-sm text-gray-300">Data and results export to various formats</p>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="alert bg-blue-900 border-blue-700 text-gray-200 mt-6">
                    <FiInfo size={22} />
                    <div>
                      <h3 className="font-bold">Want to understand the implementation?</h3>
                      <div className="text-sm">See the complete code organization and structure on GitHub.</div>
                    </div>
                    <button 
                      className="btn btn-sm btn-info"
                      onClick={() => window.open('https://github.com/yourusername/data-analysis-pipeline', '_blank')}
                    >
                      View Code
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DataPipeline;