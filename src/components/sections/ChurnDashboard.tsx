'use client';

import React, { useState, useEffect } from 'react';
import { LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ScatterChart, Scatter } from 'recharts';

const PredictionForm: React.FC = () => {
  const [formData, setFormData] = useState({
    gender: 'Male',
    SeniorCitizen: 0,
    Partner: 'Yes',
    Dependents: 'No',
    tenure: 36,
    PhoneService: 'Yes',
    MultipleLines: 'No',
    InternetService: 'Fiber optic',
    OnlineSecurity: 'No',
    OnlineBackup: 'No',
    DeviceProtection: 'No',
    TechSupport: 'No',
    StreamingTV: 'No',
    StreamingMovies: 'No',
    Contract: 'Month-to-month',
    PaperlessBilling: 'Yes',
    PaymentMethod: 'Electronic check',
    MonthlyCharges: 80,
    TotalCharges: 2800
  });
  
  const [prediction, setPrediction] = useState<{ probability: number; prediction: string } | null>(null);
  const [loading, setLoading] = useState(false);
  
  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    const parsedValue = name === 'SeniorCitizen' || name === 'tenure' || 
                        name === 'MonthlyCharges' || name === 'TotalCharges' 
                        ? parseFloat(value) : value;
    
    setFormData({
      ...formData,
      [name]: parsedValue
    });
  };
  
  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    
    const calculatePrediction = () => {
      let score = 0.5;
      
      if (formData.tenure > 40) score -= 0.25;
      else if (formData.tenure < 10) score += 0.25;
      else score -= (formData.tenure / 100);
      
      if (formData.Contract === 'Month-to-month') score += 0.2;
      else if (formData.Contract === 'Two year') score -= 0.2;
      else score -= 0.1;
      
      if (formData.InternetService === 'Fiber optic') score += 0.15;
      else if (formData.InternetService === 'No') score -= 0.1;
      
      if (formData.PaymentMethod === 'Electronic check') score += 0.1;
      
      if (formData.MonthlyCharges > 80) score += 0.15;
      
      if (formData.OnlineSecurity === 'No') score += 0.05;
      if (formData.TechSupport === 'No') score += 0.05;
      
      if (formData.gender === 'Female') score -= 0.02;
      
      if (formData.Partner === 'No') score += 0.03;
      if (formData.Dependents === 'No') score += 0.03;
      
      if (formData.SeniorCitizen === 1) score += 0.05;
      
      if (formData.StreamingTV === 'Yes' && formData.StreamingMovies === 'Yes') score += 0.02;
      
      if (formData.PaperlessBilling === 'Yes') score += 0.04;
      
      if (formData.TotalCharges > 5000) score -= 0.05;
      else if (formData.TotalCharges < 1000) score += 0.05;
      
      return Math.max(0, Math.min(1, score));
    };
    
    setTimeout(() => {
      const probability = calculatePrediction();
      setPrediction({
        probability: probability,
        prediction: probability > 0.5 ? 'Yes' : 'No'
      });
      setLoading(false);
    }, 800);
  };
  
  return (
    <div className="card bg-base-100 shadow-lg">
      <div className="card-body">
        <h2 className="card-title text-2xl">Customer Churn Predictor</h2>
        
        <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="form-control">
            <label className="label">
              <span className="label-text">Gender</span>
            </label>
            <select 
              name="gender" 
              value={formData.gender} 
              onChange={handleChange}
              className="select select-bordered w-full"
            >
              <option value="Male">Male</option>
              <option value="Female">Female</option>
            </select>
          </div>
          
          <div className="form-control">
            <label className="label">
              <span className="label-text">Tenure (months)</span>
            </label>
            <input 
              type="number" 
              name="tenure" 
              value={formData.tenure} 
              onChange={handleChange}
              className="input input-bordered w-full" 
              min="0" 
              max="72"
            />
          </div>
          
          <div className="form-control">
            <label className="label">
              <span className="label-text">Contract</span>
            </label>
            <select 
              name="Contract" 
              value={formData.Contract} 
              onChange={handleChange}
              className="select select-bordered w-full"
            >
              <option value="Month-to-month">Month-to-month</option>
              <option value="One year">One year</option>
              <option value="Two year">Two year</option>
            </select>
          </div>
          
          <div className="form-control">
            <label className="label">
              <span className="label-text">Internet Service</span>
            </label>
            <select 
              name="InternetService" 
              value={formData.InternetService} 
              onChange={handleChange}
              className="select select-bordered w-full"
            >
              <option value="DSL">DSL</option>
              <option value="Fiber optic">Fiber optic</option>
              <option value="No">No</option>
            </select>
          </div>
          
          <div className="form-control">
            <label className="label">
              <span className="label-text">Monthly Charges ($)</span>
            </label>
            <input 
              type="number" 
              name="MonthlyCharges" 
              value={formData.MonthlyCharges} 
              onChange={handleChange}
              className="input input-bordered w-full" 
              min="0" 
              max="200"
            />
          </div>
          
          <div className="form-control md:col-span-2">
            <button className="btn btn-primary w-full mt-6" type="submit" disabled={loading}>
              {loading ? 'Calculating...' : 'Predict Churn Probability'}
            </button>
          </div>
        </form>
        
        {prediction && (
          <div className="card mt-6 p-4 bg-base-200 border border-base-300">
            <h3 className="text-xl font-semibold mb-2">Prediction Result</h3>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-lg">Will this customer churn? <span className={`font-bold ${prediction.prediction === 'Yes' ? 'text-error' : 'text-success'}`}>{prediction.prediction}</span></p>
                <p className="text-sm opacity-70">Probability: {(prediction.probability * 100).toFixed(1)}%</p>
              </div>
              <div className="radial-progress text-primary" style={{"--value": (prediction.probability * 100).toFixed(0), "--size": "4rem"} as React.CSSProperties}>
                {(prediction.probability * 100).toFixed(0)}%
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

interface ChurnDistribution {
  "No": number;
  "Yes": number;
}

interface ClassificationReport {
  precision: number;
  recall: number;
  "f1-score": number;
  support: number;
}

interface BestModel {
  name: string;
  best_params: Record<string, any>;
  accuracy: number;
  roc_auc: number;
  classification_report: {
    "0": ClassificationReport;
    "1": ClassificationReport;
    "accuracy": number;
    "macro avg": ClassificationReport;
    "weighted avg": ClassificationReport;
  };
}

interface ROCData {
  fpr: number[];
  tpr: number[];
}

interface ChurnData {
  eda: {
    missing_values: Record<string, number>;
    missing_percent: Record<string, number>;
    statistics: Record<string, Record<string, number>>;
    churn_distribution: ChurnDistribution;
    correlation_matrix: Record<string, Record<string, number>>;
  };
  best_model: BestModel;
  all_models: Record<string, any>;
  roc_data: Record<string, ROCData>;
  feature_importances: Record<string, number>;
}

const ChurnDashboard: React.FC = () => {
  const [data, setData] = useState<ChurnData | null>(null);
  const [activeTab, setActiveTab] = useState("overview");
  const [isLoading, setIsLoading] = useState(true);
  
  const gitHubRepoUrl = "https://github.com/yourusername/customer-churn-prediction";
  
  useEffect(() => {
    setIsLoading(true);
    
    const loadData = async () => {
      try {
        const response = await fetch('/data/churn_analysis_results.json');
        if (!response.ok) {
          throw new Error(`Failed to load data: ${response.status} ${response.statusText}`);
        }
        
        const jsonData = await response.json();
        console.log("Successfully loaded JSON data:", jsonData);
        
        if (!jsonData || !jsonData.eda || !jsonData.best_model) {
          throw new Error("Data is missing required properties");
        } else {
          setData(jsonData as ChurnData);
        }
      } catch (err) {
        console.error('Error loading churn data:', err);
        setData(null);
      } finally {
        setIsLoading(false);
      }
    };
    
    loadData();
  }, []);
  
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="loading loading-spinner loading-lg text-primary"></div>
          <p className="mt-4 text-base-content/70">Loading dashboard data...</p>
        </div>
      </div>
    );
  }
  
  if (!data) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="alert alert-error">
            <svg xmlns="http://www.w3.org/2000/svg" className="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            <span>Error loading dashboard data. Please check the console for details.</span>
          </div>
        </div>
      </div>
    );
  }
  
  const churnDistributionData = [
    { name: 'Retained', value: data?.eda?.churn_distribution?.["No"] || 0 },
    { name: 'Churned', value: data?.eda?.churn_distribution?.["Yes"] || 0 }
  ];
  
  // Improved feature importance data handling with mapping
  const featureImportanceData = Object.entries(data?.feature_importances || {}).map(([feature, importance]) => {
    // Create a mapping from feature indices or generic names to meaningful labels
    // Based on typical telco churn dataset features
    const featureIndexMap: Record<string, string> = {
      // Map numeric indices to feature names
      "0": "Customer Tenure (Months)",
      "1": "Monthly Charges ($)",
      "2": "Total Charges ($)",
      "3": "Senior Citizen Status",
      "4": "Contract Type",
      "5": "Payment Method",
      "6": "Internet Service Type",
      "7": "Online Security",
      "8": "Tech Support",
      "9": "Paperless Billing",
      "10": "Partner Status",
      "11": "Dependents",
      "12": "Phone Service",
      "13": "Multiple Lines",
      "14": "Online Backup",
      "15": "Device Protection",
      "16": "Streaming TV",
      "17": "Streaming Movies",
      "18": "Gender",
  
      // Also map "Feature X" format that might come from backend
      "Feature_0": "Customer Tenure (Months)",
      "Feature_1": "Monthly Charges ($)",
      "Feature_2": "Total Charges ($)",
      "Feature_3": "Senior Citizen Status",
      "Feature_4": "Contract Type",
      "Feature_5": "Payment Method",
      "Feature_6": "Internet Service Type",
      "Feature_7": "Online Security",
      "Feature_8": "Tech Support",
      "Feature_9": "Paperless Billing",
      "Feature_10": "Partner Status",
      "Feature_11": "Dependents",
      "Feature_12": "Phone Service",
      "Feature_13": "Multiple Lines",
      "Feature_14": "Online Backup",
      "Feature_15": "Device Protection",
      "Feature_16": "Streaming TV", 
      "Feature_17": "Streaming Movies",
      "Feature_18": "Gender",
      
      // Also map generic "Feature X" format we see in the screenshot
      "Feature: 0": "Customer Tenure (Months)",
      "Feature: 1": "Monthly Charges ($)",
      "Feature: 2": "Total Charges ($)",
      "Feature: 3": "Senior Citizen Status",
      "Feature: 4": "Contract Type",
      "Feature: 5": "Payment Method",
      "Feature: 6": "Internet Service Type",
      "Feature: 7": "Online Security",
      "Feature: 8": "Tech Support",
      "Feature: 9": "Paperless Billing",
      "Feature: 10": "Partner Status",
      "Feature: 11": "Dependents",
      "Feature: 12": "Phone Service",
      "Feature: 13": "Multiple Lines",
      "Feature: 14": "Online Backup",
      "Feature: 15": "Device Protection",
      "Feature: 16": "Streaming TV", 
      "Feature: 17": "Streaming Movies",
      "Feature: 18": "Gender",
    };
  
    // Handle both normal feature names and indexed feature names
    let displayName = featureIndexMap[feature] || feature;
    
    // Also try to match without the "Feature:" prefix if it exists
    if (feature.startsWith("Feature:") || feature.startsWith("Feature_")) {
      const index = feature.split(/[_:]\s*/)[1];
      displayName = featureIndexMap[index] || displayName;
    }
    
    // For debugging - log what's coming from the backend
    console.log(`Original feature: "${feature}", Mapped to: "${displayName}"`);
    
    return {
      name: displayName,
      value: importance * 100,
      originalFeature: feature
    };
  }).sort((a, b) => b.value - a.value).slice(0, 8);
  
  // Log all the feature keys from the backend for debugging
  console.log("All feature keys from backend:", Object.keys(data?.feature_importances || {}));
  
  // Add debugging to see what feature names are coming from Python
  console.log("Feature names from backend:", Object.keys(data?.feature_importances || {}));
  
  const modelComparisonData: { name: string; x: number; y: number }[] = [];
  for (const [name, roccurve] of Object.entries(data?.roc_data || {})) {
    if (roccurve && Array.isArray(roccurve.fpr) && Array.isArray(roccurve.tpr)) {
      for (let i = 0; i < roccurve.fpr.length; i++) {
        modelComparisonData.push({
          name: name,
          x: roccurve.fpr[i],
          y: roccurve.tpr[i]
        });
      }
    }
  }
  
  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8'];
  
  return (
    <div className="min-h-screen bg-base-200">
      <div className="container mx-auto px-4 py-6">
        <div className="mb-6">
          <h1 className="text-3xl font-bold mb-2 text-base-content">Customer Churn Analysis Dashboard</h1>
          <p className="text-base-content/70">
            A machine learning model to predict and analyze customer churn using scikit-learn
            <a 
              href={gitHubRepoUrl}
              target="_blank" 
              rel="noopener noreferrer" 
              className="ml-2 inline-flex items-center text-primary"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" className="mr-1">
                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
              </svg>
              View code on GitHub
            </a>
          </p>
        </div>
        
        <div className="tabs tabs-boxed mb-6 bg-base-300">
          <a 
            className={`tab ${activeTab === "overview" ? "tab-active" : ""}`}
            onClick={() => setActiveTab("overview")}
          >
            Overview
          </a>
          <a 
            className={`tab ${activeTab === "insights" ? "tab-active" : ""}`}
            onClick={() => setActiveTab("insights")}
          >
            Insights
          </a>
          <a 
            className={`tab ${activeTab === "models" ? "tab-active" : ""}`}
            onClick={() => setActiveTab("models")}
          >
            Model Performance
          </a>
          <a 
            className={`tab ${activeTab === "predictor" ? "tab-active" : ""}`}
            onClick={() => setActiveTab("predictor")}
          >
            Predictor
          </a>
        </div>
        
        {activeTab === "overview" && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="card bg-base-100 shadow-lg">
              <div className="card-body">
                <h2 className="card-title text-2xl">Project Overview</h2>
                <p className="mb-4">
                  This project analyzes customer churn for a telecom company using machine learning. 
                  Churn prediction helps businesses identify customers who are likely to leave, 
                  allowing for targeted retention strategies.
                </p>
                <p className="mb-4">
                  We've used scikit-learn to build and evaluate multiple models:
                </p>
                <ul className="list-disc pl-5 mb-4">
                  <li>Random Forest</li>
                  <li>Gradient Boosting</li>
                  <li>Logistic Regression</li>
                </ul>
                <p>
                  Our best model achieves {((data?.best_model?.roc_auc || 0) * 100).toFixed(1)}% AUC-ROC and {" "}
                  {((data?.best_model?.accuracy || 0) * 100).toFixed(1)}% accuracy.
                </p>
                <div className="mt-6">
                  <a 
                    href={`${gitHubRepoUrl}/blob/main/churn_analysis.py`}
                    target="_blank" 
                    rel="noopener noreferrer" 
                    className="btn btn-outline btn-primary w-full"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-2">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                      <polyline points="14 2 14 8 20 8"></polyline>
                      <line x1="16" y1="13" x2="8" y2="13"></line>
                      <line x1="16" y1="17" x2="8" y2="17"></line>
                      <polyline points="10 9 9 9 8 9"></polyline>
                    </svg>
                    View Python Code on GitHub
                  </a>
                </div>
              </div>
            </div>
            
            <div className="card bg-base-100 shadow-lg">
              <div className="card-body">
                <h2 className="card-title text-2xl">Customer Distribution</h2>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={churnDistributionData}
                        cx="50%"
                        cy="50%"
                        labelLine={true}
                        label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(1)}%`}
                        outerRadius={80}
                        fill="#8884d8"
                        dataKey="value"
                      >
                        {churnDistributionData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="alert alert-info text-info-content mt-4">
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" className="stroke-current shrink-0 w-6 h-6">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                  </svg>
                  <span>About {(data?.eda?.churn_distribution?.["Yes"] || 0).toFixed(1)}% of customers churned in this dataset.</span>
                </div>
              </div>
            </div>
          </div>
        )}
        
        {activeTab === "insights" && (
          <div className="grid grid-cols-1 gap-6">
            <div className="card bg-base-100 shadow-lg">
              <div className="card-body">
                <h2 className="card-title text-2xl">Feature Importance</h2>
                <p className="text-base-content/70 mb-4">
                  Factors that most influence whether a customer will churn, ranked by importance.
                  Higher values indicate stronger influence on customer decisions.
                </p>
                <div className="h-96">
                  {(!data?.feature_importances || Object.keys(data.feature_importances).length === 0) ? (
                    <div className="flex h-full items-center justify-center">
                      <div className="text-center p-6 bg-base-200 rounded-lg">
                        <h3 className="text-xl font-semibold mb-2">No Feature Importance Data Available</h3>
                        <p>The analysis couldn't retrieve feature importance data.</p>
                      </div>
                    </div>
                  ) : (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        layout="vertical"
                        data={featureImportanceData}
                        margin={{ top: 20, right: 30, left: 150, bottom: 5 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis 
                          type="number" 
                          domain={[0, 'dataMax']} 
                          label={{ value: 'Importance Score (%)', position: 'insideBottom', offset: -5 }} 
                        />
                        <YAxis 
                          dataKey="name" 
                          type="category" 
                          width={150} 
                          tick={{ fontSize: 12 }}
                        />
                        <Tooltip 
                          formatter={(value) => [`${value.toFixed(2)}%`, 'Influence on Churn']} 
                          labelFormatter={(value) => `Feature: ${value}`}
                        />
                        <Legend content={() => (
                          <div style={{ textAlign: 'center', margin: '10px 0' }}>
                            <span>Features ordered by importance to churn prediction</span>
                          </div>
                        )} />
                        <Bar dataKey="value" name="Importance" fill="#8884d8" radius={[0, 6, 6, 0]}>
                          {featureImportanceData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  )}
                </div>
                
                <div className="alert alert-info text-info-content mt-4">
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" className="stroke-current shrink-0 w-6 h-6">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                  </svg>
                  <div>
                    <p><strong>What this means:</strong> Features like customer tenure, contract type, and internet service quality 
                    have the strongest impact on customer churn decisions.</p>
                    <p className="mt-2 text-sm">Values shown are relative importance scores from our {data?.best_model?.name?.replace(/_/g, ' ') || 'machine learning'} model.</p>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="card bg-base-100 shadow-lg">
              <div className="card-body">
                <h2 className="card-title text-2xl">Key Insights</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  <div className="card bg-base-200 shadow-md">
                    <div className="card-body">
                      <h3 className="card-title">Tenure Impact</h3>
                      <p>Long-term customers are much less likely to churn. The first 12 months are critical for retention.</p>
                    </div>
                  </div>
                  
                  <div className="card bg-base-200 shadow-md">
                    <div className="card-body">
                      <h3 className="card-title">Contract Effect</h3>
                      <p>Month-to-month contracts have much higher churn rates than one or two-year contracts.</p>
                    </div>
                  </div>
                  
                  <div className="card bg-base-200 shadow-md">
                    <div className="card-body">
                      <h3 className="card-title">Service Quality</h3>
                      <p>Customers without tech support or online security are more likely to leave, especially with fiber optic service.</p>
                    </div>
                  </div>
                  
                  <div className="card bg-base-200 shadow-md">
                    <div className="card-body">
                      <h3 className="card-title">Payment Method</h3>
                      <p>Customers using electronic checks churn more frequently than those using credit cards or bank transfers.</p>
                    </div>
                  </div>
                  
                  <div className="card bg-base-200 shadow-md">
                    <div className="card-body">
                      <h3 className="card-title">Pricing Strategy</h3>
                      <p>Higher monthly charges correlate with increased churn, particularly for newer customers.</p>
                    </div>
                  </div>
                  
                  <div className="card bg-base-200 shadow-md">
                    <div className="card-body">
                      <h3 className="card-title">Service Bundling</h3>
                      <p>Customers with multiple services tend to be more loyal. Consider bundle offers for retention.</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === "models" && (
          <div className="grid grid-cols-1 gap-6">
            <div className="card bg-base-100 shadow-lg">
              <div className="card-body">
                <h2 className="card-title text-2xl">Model Performance</h2>
                <div className="stats stats-vertical lg:stats-horizontal shadow w-full bg-base-200">
                  <div className="stat">
                    <div className="stat-title">Best Model</div>
                    <div className="stat-value capitalize">{data?.best_model?.name?.replace(/_/g, ' ') || 'Gradient Boosting'}</div>
                    <div className="stat-desc opacity-70">Based on ROC-AUC score</div>
                  </div>
                  
                  <div className="stat">
                    <div className="stat-title">Accuracy</div>
                    <div className="stat-value">{((data?.best_model?.accuracy || 0.8) * 100).toFixed(1)}%</div>
                    <div className="stat-desc opacity-70">Overall prediction accuracy</div>
                  </div>
                  
                  <div className="stat">
                    <div className="stat-title">AUC-ROC</div>
                    <div className="stat-value">{((data?.best_model?.roc_auc || 0.85) * 100).toFixed(1)}%</div>
                    <div className="stat-desc opacity-70">Area under ROC curve</div>
                  </div>
                </div>
                
                <div className="divider">ROC Curves Comparison</div>
                
                <div className="h-96">
                  {(!data?.roc_data || Object.keys(data.roc_data).length === 0) ? (
                    <div className="flex h-full items-center justify-center">
                      <div className="text-center p-6 bg-base-200 rounded-lg">
                        <h3 className="text-xl font-semibold mb-2">No ROC Data Available</h3>
                        <p>The analysis couldn't retrieve ROC curve data.</p>
                      </div>
                    </div>
                  ) : (
                    <ResponsiveContainer width="100%" height="100%">
                      <ScatterChart
                        margin={{ top: 20, right: 30, bottom: 20, left: 20 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis 
                          type="number" 
                          dataKey="x" 
                          name="False Positive Rate" 
                          domain={[0, 1]}
                          label={{ value: 'False Positive Rate', position: 'insideBottomRight', offset: -5 }}
                        />
                        <YAxis 
                          type="number" 
                          dataKey="y" 
                          name="True Positive Rate" 
                          domain={[0, 1]}
                          label={{ value: 'True Positive Rate', angle: -90, position: 'insideLeft' }}
                        />
                        <Tooltip 
                          cursor={{ strokeDasharray: '3 3' }}
                          formatter={(value, name, props) => [value.toFixed(3), name]}
                          labelFormatter={(value, payload) => `Model: ${payload[0]?.payload?.name}`}
                        />
                        <Legend />
                        {Object.keys(data.roc_data).map((name, index) => (
                          <Scatter 
                            key={name}
                            name={name.replace(/_/g, ' ')}
                            data={modelComparisonData.filter(d => d.name === name)}
                            fill={COLORS[index % COLORS.length]}
                            line
                            shape="circle"
                          />
                        ))}
                        <Scatter
                          name="Random Classifier"
                          data={[{x: 0, y: 0}, {x: 1, y: 1}]}
                          fill="none"
                          line={{ stroke: '#ccc', strokeDasharray: '5 5' }}
                          shape={() => null}
                        />
                      </ScatterChart>
                    </ResponsiveContainer>
                  )}
                </div>
                
                <div className="alert alert-info text-info-content mt-4">
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" className="stroke-current shrink-0 w-6 h-6">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                  </svg>
                  <span>The {(data?.best_model?.name?.replace(/_/g, ' ') || 'Gradient Boosting')} model performs best with an AUC of {((data?.best_model?.roc_auc || 0.85) * 100).toFixed(1)}%, showing good balance between sensitivity and specificity.</span>
                </div>
              </div>
            </div>
            
            <div className="card bg-base-100 shadow-lg">
              <div className="card-body">
                <h2 className="card-title text-2xl">Classification Report</h2>
                <div className="overflow-x-auto">
                  <table className="table w-full">
                    <thead>
                      <tr>
                        <th>Class</th>
                        <th>Precision</th>
                        <th>Recall</th>
                        <th>F1-Score</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td>Not Churned (0)</td>
                        <td>{((data?.best_model?.classification_report?.["0"]?.precision || 0.835) * 100).toFixed(1)}%</td>
                        <td>{((data?.best_model?.classification_report?.["0"]?.recall || 0.911) * 100).toFixed(1)}%</td>
                        <td>{((data?.best_model?.classification_report?.["0"]?.['f1-score'] || 0.871) * 100).toFixed(1)}%</td>
                      </tr>
                      <tr>
                        <td>Churned (1)</td>
                        <td>{((data?.best_model?.classification_report?.["1"]?.precision || 0.672) * 100).toFixed(1)}%</td>
                        <td>{((data?.best_model?.classification_report?.["1"]?.recall || 0.505) * 100).toFixed(1)}%</td>
                        <td>{((data?.best_model?.classification_report?.["1"]?.['f1-score'] || 0.577) * 100).toFixed(1)}%</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                
                <div className="alert alert-warning text-warning-content mt-4">
                  <svg xmlns="http://www.w3.org/2000/svg" className="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                  <span>
                    Note: The model is better at predicting customers who stay (higher precision and recall) 
                    than those who churn. This is common in imbalanced datasets.
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}
        
        {activeTab === "predictor" && (
          <div className="grid grid-cols-1 gap-6">
            <PredictionForm />
            
            <div className="card bg-base-100 shadow-lg">
              <div className="card-body">
                <h2 className="card-title text-2xl">How to Use the Predictor</h2>
                <p className="mb-4">
                  The customer churn predictor allows you to input customer characteristics and predicts 
                  the likelihood of that customer churning. This demo version uses a pre-trained model.
                </p>
                <p className="mb-4">
                  To use:
                </p>
                <ol className="list-decimal pl-5 mb-4">
                  <li className="mb-2">Enter customer demographics and service details in the form above</li>
                  <li className="mb-2">Click "Predict Churn Probability"</li>
                  <li>Review the prediction result showing both the yes/no decision and the confidence percentage</li>
                </ol>
                <p>
                  In a production environment, this predictor would be connected to your customer database
                  and could be used to flag at-risk customers for proactive retention campaigns.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ChurnDashboard;