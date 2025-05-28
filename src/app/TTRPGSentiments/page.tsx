"use client";

import React, { useState, useEffect, useMemo } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  PointElement,
  LineElement,
  ArcElement,
  Filler,
  Colors,
  TooltipItem,
  ChartType, // Ensured ChartType is imported
} from 'chart.js';
import { Bar, Line, Pie } from 'react-chartjs-2';
import Papa, { ParseError, ParseResult } from 'papaparse'; // Ensured ParseError and ParseResult are imported
import { IoCloseCircleOutline, IoPricetagsOutline, IoGameControllerOutline, IoColorPaletteOutline } from 'react-icons/io5';


ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  PointElement,
  LineElement,
  ArcElement,
  Filler,
  Colors
);

interface RawSurveyRow {
  'Timestamp'?: string;
  'When did you start playing tabletop roleplaying games?'?: string;
  'How often do you play tabletop roleplaying games?'?: string;
  'How long do your sessions typically last?'?: string;
  'Select your current main system.'?: string;
  'How would you rate your satisfaction with your current main system?'?: string;
  'How would you rate the complexity of your current main system?'?: string;
  'What genre do you currently play in?'?: string;
  'Would you describe yourself as a game master, player, both or neither?'?: string;
  'What is the number of players in your current main group?'?: string;
  'Rate the importance of these in your game sessions with 1 being the least important and 5 being the most important. [Combat]'?: string;
  'Rate the importance of these in your game sessions with 1 being the least important and 5 being the most important. [Roleplaying]'?: string;
  'Rate the importance of these in your game sessions with 1 being the least important and 5 being the most important. [Exploration]'?: string;
  'How much have you spent on tabletop roleplaying within the past year?'?: string;
  'What would be the maximum you would pay for a digital book?'?: string;
  'What would be the maximum you would pay for a hardback book?'?: string;
  'What would you be interested in purchasing for tabletop games?'?: string;
  'What would you say is the main issue with your player group(s)?'?: string;
  [key: string]: string | undefined;
}

interface SurveyData {
  timestamp: string;
  experienceLevel: string;
  playFrequency: string;
  sessionLength: string;
  mainSystem: string;
  systemSatisfaction: number;
  systemComplexity: number;
  genre: string;
  role: string;
  groupSize: string;
  combatImportance: number;
  roleplayImportance: number;
  explorationImportance: number;
  spendingAmount: string;
  maxDigitalPrice: number;
  maxHardbackPrice: number;
  purchaseInterests: string[];
  playerIssues: string;
  [key: string]: string | number | string[] | undefined;
}

const transformData = (rawData: Partial<RawSurveyRow>[]): SurveyData[] => {
  return rawData.map(row => ({
    timestamp: row['Timestamp'] || '',
    experienceLevel: row['When did you start playing tabletop roleplaying games?'] || 'N/A',
    playFrequency: row['How often do you play tabletop roleplaying games?'] || 'N/A',
    sessionLength: row['How long do your sessions typically last?'] || 'N/A',
    mainSystem: row['Select your current main system.'] || 'N/A',
    systemSatisfaction: parseInt(row['How would you rate your satisfaction with your current main system?'] || '0'),
    systemComplexity: parseInt(row['How would you rate the complexity of your current main system?'] || '0'),
    genre: row['What genre do you currently play in?'] || 'N/A',
    role: row['Would you describe yourself as a game master, player, both or neither?'] || 'N/A',
    groupSize: row['What is the number of players in your current main group?'] || 'N/A',
    combatImportance: parseInt(row['Rate the importance of these in your game sessions with 1 being the least important and 5 being the most important. [Combat]'] || '0'),
    roleplayImportance: parseInt(row['Rate the importance of these in your game sessions with 1 being the least important and 5 being the most important. [Roleplaying]'] || '0'),
    explorationImportance: parseInt(row['Rate the importance of these in your game sessions with 1 being the least important and 5 being the most important. [Exploration]'] || '0'),
    spendingAmount: row['How much have you spent on tabletop roleplaying within the past year?'] || 'N/A',
    maxDigitalPrice: parseFloat(row['What would be the maximum you would pay for a digital book?']?.replace('$', '') || '0'),
    maxHardbackPrice: parseFloat(row['What would be the maximum you would pay for a hardback book?']?.replace('$', '') || '0'),
    purchaseInterests: row['What would you be interested in purchasing for tabletop games?']?.split(',') || [],
    playerIssues: row['What would you say is the main issue with your player group(s)?'] || 'N/A',
  })).filter(row => row.timestamp !== '');
};

const countOccurrences = (data: SurveyData[], field: keyof SurveyData, sortByValue: boolean = false): { name: string; value: number }[] => {
  if (!data || data.length === 0) return [];
  const counts: Record<string, number> = {};
  data.forEach(item => {
    const value = item[field] as string;
    if (value && value.trim() !== '' && value !== 'N/A') {
      counts[value] = (counts[value] || 0) + 1;
    }
  });
  
  let result = Object.entries(counts).map(([name, value]) => ({ name, value }));
  
  if (sortByValue) {
    result = result.sort((a, b) => b.value - a.value);
  } else {
    result = result.sort((a,b) => a.name.localeCompare(b.name));
  }
  return result;
};

interface AverageRating {
  name: string;
  value: number;
}

const calculateAverageRatings = (data: SurveyData[]): AverageRating[] => {
  if (!data || data.length === 0) return [];
  const metrics: (keyof SurveyData)[] = ['systemSatisfaction', 'systemComplexity', 'combatImportance', 'roleplayImportance', 'explorationImportance'];
  const totals: Record<string, number> = {};
  const counts: Record<string, number> = {};
  
  metrics.forEach(metric => {
    totals[metric as string] = 0;
    counts[metric as string] = 0;
  });
  
  data.forEach(item => {
    metrics.forEach(metric => {
      const value = item[metric];
      if (typeof value === 'number' && value > 0 && !isNaN(value)) {
        totals[metric as string] += value;
        counts[metric as string]++;
      }
    });
  });
  
  return metrics.map(metric => ({
    name: (metric as string).replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase()),
    value: counts[metric as string] > 0 ? parseFloat((totals[metric as string] / counts[metric as string]).toFixed(1)) : 0
  }));
};

interface SpendingGroup {
  name: string;
  value: number;
}
const groupSpendingData = (data: SurveyData[]): SpendingGroup[] => {
  if (!data || data.length === 0) return [];
  const spendingGroups: Record<string, number> = {
    '0-50': 0,
    '51-200': 0,
    '201-500': 0,
    '500+': 0
  };
  
  data.forEach(item => {
    const amount = item.spendingAmount;
    if (amount) {
        if (amount.includes('0-50') || amount.toLowerCase().includes("under $50")) spendingGroups['0-50']++;
        else if (amount.includes('51-200')) spendingGroups['51-200']++;
        else if (amount.includes('201-500')) spendingGroups['201-500']++;
        else if (amount.includes('500') || amount.toLowerCase().includes("over $500")) spendingGroups['500+']++;
    }
  });
  
  return Object.entries(spendingGroups).map(([name, value]) => ({ name, value }));
};

interface SystemPreference {
  name: string;
  value: number;
}
const getSystemPreferencesData = (data: SurveyData[]): SystemPreference[] => {
  if (!data || data.length === 0) return [];
  return countOccurrences(data, 'mainSystem', true)
    .slice(0, 10);
};

interface PriceSensitivityRange {
  range: string;
  digital: number;
  hardback: number;
}
const getPriceSensitivityData = (data: SurveyData[]): PriceSensitivityRange[] => {
    if (!data || data.length === 0) return [];
    const priceRanges: PriceSensitivityRange[] = [
        { range: '$0-$10', digital: 0, hardback: 0 },
        { range: '$11-$25', digital: 0, hardback: 0 },
        { range: '$26-$50', digital: 0, hardback: 0 },
        { range: '$51-$75', digital: 0, hardback: 0 },
        { range: '$76+', digital: 0, hardback: 0 }
    ];

    data.forEach(item => {
        const digitalPrice = item.maxDigitalPrice;
        const hardbackPrice = item.maxHardbackPrice;

        if (digitalPrice <= 10) priceRanges[0].digital++;
        else if (digitalPrice <= 25) priceRanges[1].digital++;
        else if (digitalPrice <= 50) priceRanges[2].digital++;
        else if (digitalPrice <= 75) priceRanges[3].digital++;
        else if (digitalPrice > 75) priceRanges[4].digital++;

        if (hardbackPrice <= 10) priceRanges[0].hardback++;
        else if (hardbackPrice <= 25) priceRanges[1].hardback++;
        else if (hardbackPrice <= 50) priceRanges[2].hardback++;
        else if (hardbackPrice <= 75) priceRanges[3].hardback++;
        else if (hardbackPrice > 75) priceRanges[4].hardback++;
    });
    return priceRanges;
};

interface SystemSatisfactionByGenre {
    name: string;
    satisfaction: number;
}
const calculateSystemSatisfactionByGenre = (data: SurveyData[]): SystemSatisfactionByGenre[] => {
  if (!data || data.length === 0) return [];
  const genreMap: Record<string, { total: number, count: number }> = {};
  
  data.forEach(item => {
    if (item.genre && item.genre !== 'N/A' && typeof item.systemSatisfaction === 'number' && item.systemSatisfaction > 0 && !isNaN(item.systemSatisfaction)) {
      if (!genreMap[item.genre]) {
        genreMap[item.genre] = { total: 0, count: 0 };
      }
      genreMap[item.genre].total += item.systemSatisfaction;
      genreMap[item.genre].count++;
    }
  });
  
  return Object.entries(genreMap)
    .map(([genre, stats]) => ({
      name: genre,
      satisfaction: parseFloat((stats.total / stats.count).toFixed(1))
    }))
    .filter(g => g.satisfaction > 0)
    .sort((a, b) => b.satisfaction - a.satisfaction)
    .slice(0, 10);
};

interface TopSystemInfo {
    system: string;
    count: number;
}
interface SystemDistributionByGenre {
    genre: string;
    topSystems: TopSystemInfo[];
    totalPlayers: number;
}
const getSystemDistributionByGenre = (data: SurveyData[]): SystemDistributionByGenre[] => {
  if (!data || data.length === 0) return [];
  const genreSystemMap: Record<string, Record<string, number>> = {};
  
  data.forEach(item => {
    if (item.genre && item.genre !== 'N/A' && item.mainSystem && item.mainSystem !== 'N/A') {
      if (!genreSystemMap[item.genre]) {
        genreSystemMap[item.genre] = {};
      }
      genreSystemMap[item.genre][item.mainSystem] = (genreSystemMap[item.genre][item.mainSystem] || 0) + 1;
    }
  });
  
  return Object.entries(genreSystemMap).map(([genre, systems]) => {
    const topSystems = Object.entries(systems)
      .sort(([, countA], [, countB]) => countB - countA)
      .slice(0, 3)
      .map(([system, count]) => ({ system, count }));
    
    return {
      genre,
      topSystems,
      totalPlayers: Object.values(systems).reduce((sum, count) => sum + count, 0)
    };
  }).sort((a, b) => b.totalPlayers - a.totalPlayers).slice(0, 5);
};

const CHART_COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d', '#ffc658', '#8dd1e1', '#d0ed57', '#a4de6c'];

const TTRPGDashboard: React.FC = () => {
  const [surveyData, setSurveyData] = useState<SurveyData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState(0);
  
  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const csvFilePath = `/ttrpg.csv`;
        const response = await fetch(csvFilePath);
        if (!response.ok) {
          throw new Error(`Failed to fetch CSV: ${response.status} ${response.statusText}`);
        }
        const text = await response.text();
        
        Papa.parse<Partial<RawSurveyRow>>(text, {
          header: true,
          skipEmptyLines: true,
          complete: (results: ParseResult<Partial<RawSurveyRow>>) => {
            if (results.errors.length > 0) {
              console.warn("CSV Parsing errors:", results.errors.map(err => err.message).join('\n'));
            }
            const transformedData = transformData(results.data);
            setSurveyData(transformedData);
            setIsLoading(false);
          },
          error: (err: ParseError) => {
            setError('Error parsing CSV: ' + err.message);
            setIsLoading(false);
          }
        });
      } catch (e) {
        let message = 'An unknown error occurred';
        if (e instanceof Error) {
          message = e.message;
        } else if (typeof e === 'string') {
          message = e;
        }
        setError('Error loading data: ' + message);
        setIsLoading(false);
      }
    };

    fetchData();
  }, []);

  const playerRolesData = useMemo(() => countOccurrences(surveyData, 'role', true), [surveyData]);
  const playFrequencyData = useMemo(() => countOccurrences(surveyData, 'playFrequency', false), [surveyData]);
  const experienceLevelData = useMemo(() => countOccurrences(surveyData, 'experienceLevel', false), [surveyData]);
  
  const systemPreferencesData = useMemo(() => getSystemPreferencesData(surveyData), [surveyData]);
  const systemSatisfactionByGenreData = useMemo(() => calculateSystemSatisfactionByGenre(surveyData), [surveyData]);
  const genreSystemTableData = useMemo(() => getSystemDistributionByGenre(surveyData), [surveyData]);
  const genrePreferencesData = useMemo(() => countOccurrences(surveyData, 'genre', true).slice(0,10), [surveyData]);

  const averageRatingsData = useMemo(() => calculateAverageRatings(surveyData), [surveyData]);
  
  interface GameplayElementChartItem {
    name: string;
    value: number;
  }
  const gameplayElementImportanceChartData = useMemo((): GameplayElementChartItem[] => {
    if (!averageRatingsData || averageRatingsData.length === 0) return [];
    const combatImportance = averageRatingsData.find(r => r.name === 'Combat Importance')?.value || 0;
    const roleplayImportance = averageRatingsData.find(r => r.name === 'Roleplay Importance')?.value || 0;
    const explorationImportance = averageRatingsData.find(r => r.name === 'Exploration Importance')?.value || 0;
    return [
      { name: "Combat", value: combatImportance },
      { name: "Roleplaying", value: roleplayImportance },
      { name: "Exploration", value: explorationImportance },
    ];
  }, [averageRatingsData]);
  const sessionLengthData = useMemo(() => countOccurrences(surveyData, 'sessionLength', false), [surveyData]);

  const spendingPieData = useMemo(() => groupSpendingData(surveyData), [surveyData]);
  const priceSensitivityChartData = useMemo(() => getPriceSensitivityData(surveyData), [surveyData]);

  const chartOptionsBase = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (context: TooltipItem<ChartType>) => `${context.dataset.label || context.label || ''}: ${context.formattedValue}`,
        },
      },
       colors: { enabled: true }
    },
    scales: {
      x: { 
        grid: { display: false },
        ticks: { color: '#666' }
      },
      y: { 
        grid: { color: 'rgba(200, 200, 200, 0.2)'},
        ticks: { beginAtZero: true, color: '#666' }
      },
    },
  };

  const pieChartOptionsBase = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'bottom' as const, labels: { boxWidth:12, padding:15 } },
      tooltip: {
        callbacks: {
          label: (context: TooltipItem<'pie'>) => {
            const label = context.label || '';
            const value = typeof context.raw === 'number' ? context.raw : 0;
            let total = 0;
            if (context.chart.data.datasets[context.datasetIndex] && context.chart.data.datasets[context.datasetIndex].data) {
                total = context.chart.data.datasets[context.datasetIndex].data
                    .reduce((acc: number, val: unknown) => acc + (typeof val === 'number' ? val : 0), 0);
            }
            const percentage = total > 0 ? ((value / total) * 100).toFixed(1) + '%' : '0%';
            return `${label}: ${value} (${percentage})`;
          },
        },
      },
      colors: { enabled: true, forceOverride: true }
    },
  };


  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-[calc(100vh-var(--header-height,0px)-var(--footer-height,0px))]">
        <div className="text-center">
          <span className="loading loading-spinner loading-lg"></span>
          <p className="mt-4">Loading TTRPG dashboard data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex justify-center items-center min-h-[calc(100vh-var(--header-height,0px)-var(--footer-height,0px))]">
        <div className="text-center p-4">
          <div role="alert" className="alert alert-error">
            <IoCloseCircleOutline className="stroke-current shrink-0 h-6 w-6" />
            <span>{error}</span>
          </div>
          <button 
            className="btn btn-primary mt-6"
            onClick={() => window.location.reload()}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }
  
  const renderTabs = () => {
    const tabs = ["Player Profile", "System & Genre", "Gameplay", "Spending"];
    return (
      <div role="tablist" className="tabs tabs-boxed mb-8 bg-base-200">
        {tabs.map((tab, index) => (
          <a 
            key={index}
            role="tab"
            className={`tab ${activeTab === index ? 'tab-active !bg-primary text-primary-content' : ''}`}
            onClick={() => setActiveTab(index)}
          >
            {tab}
          </a>
        ))}
      </div>
    );
  };
  
  const renderPlayerProfileTab = () => (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card bg-base-100 shadow-xl">
          <div className="card-body">
            <h2 className="card-title">Player Roles</h2>
            <div className="h-72">
              <Pie 
                data={{
                  labels: playerRolesData.map(d => d.name),
                  datasets: [{ 
                    label: 'Player Roles', 
                    data: playerRolesData.map(d => d.value),
                    backgroundColor: CHART_COLORS,
                  }]
                }} 
                options={pieChartOptionsBase} 
              />
            </div>
          </div>
        </div>
        <div className="card bg-base-100 shadow-xl">
          <div className="card-body">
            <h2 className="card-title">Gaming Frequency</h2>
            <div className="h-72">
              <Bar 
                data={{
                  labels: playFrequencyData.map(d => d.name),
                  datasets: [{
                    label: 'Respondents',
                    data: playFrequencyData.map(d => d.value),
                    backgroundColor: CHART_COLORS[0],
                  }]
                }}
                options={{...chartOptionsBase, scales: {...chartOptionsBase.scales, x: {...chartOptionsBase.scales.x, ticks: { autoSkip: false, maxRotation: 45, minRotation: 45 } }}}}
              />
            </div>
          </div>
        </div>
      </div>
      <div className="card bg-base-100 shadow-xl">
        <div className="card-body">
          <h2 className="card-title">Experience Level</h2>
          <div className="h-80">
             <Bar 
                data={{
                  labels: experienceLevelData.map(d => d.name),
                  datasets: [{
                    label: 'Respondents',
                    data: experienceLevelData.map(d => d.value),
                    backgroundColor: CHART_COLORS[1],
                  }]
                }}
                options={{...chartOptionsBase, scales: {...chartOptionsBase.scales, x: {...chartOptionsBase.scales.x, ticks: { autoSkip: false, maxRotation: 45, minRotation: 45 } }}}}
              />
          </div>
        </div>
      </div>
    </div>
  );

  const renderSystemGenreTab = () => (
    <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="card bg-base-100 shadow-xl">
                <div className="card-body">
                    <h2 className="card-title">Top 10 Systems</h2>
                    <div className="h-96">
                        <Bar 
                            data={{
                                labels: systemPreferencesData.map(d => d.name),
                                datasets: [{
                                    label: 'Players',
                                    data: systemPreferencesData.map(d => d.value),
                                    backgroundColor: CHART_COLORS[2],
                                }]
                            }}
                            options={{...chartOptionsBase, scales: {...chartOptionsBase.scales, x: {...chartOptionsBase.scales.x, ticks: { autoSkip: false, maxRotation: 45, minRotation: 45, font: {size: 10} }}}}}
                        />
                    </div>
                </div>
            </div>
            <div className="card bg-base-100 shadow-xl">
                <div className="card-body">
                    <h2 className="card-title">Top 10 Genre Preferences</h2>
                    <div className="h-96">
                        <Pie 
                            data={{
                                labels: genrePreferencesData.map(d => d.name),
                                datasets: [{
                                    label: 'Genre Preferences',
                                    data: genrePreferencesData.map(d => d.value),
                                    backgroundColor: CHART_COLORS,
                                }]
                            }}
                            options={pieChartOptionsBase}
                        />
                    </div>
                </div>
            </div>
        </div>
         <div className="card bg-base-100 shadow-xl">
            <div className="card-body">
                <h2 className="card-title">Average System Satisfaction by Genre (Top 10)</h2>
                 <div className="h-80">
                    <Bar 
                        data={{
                            labels: systemSatisfactionByGenreData.map(d => d.name),
                            datasets: [{
                                label: 'Avg. Satisfaction (out of 5)',
                                data: systemSatisfactionByGenreData.map(d => d.satisfaction),
                                backgroundColor: CHART_COLORS,
                            }]
                        }}
                        options={{...chartOptionsBase, scales: {...chartOptionsBase.scales, x: {...chartOptionsBase.scales.x, ticks: { autoSkip: false, maxRotation: 45, minRotation: 45 }}, y: {...chartOptionsBase.scales.y, max: 5, title: {display: true, text: 'Avg. Satisfaction (1-5)'}}}}}
                    />
                </div>
            </div>
        </div>
        <div className="card bg-base-100 shadow-xl">
            <div className="card-body">
                <h2 className="card-title">Top Systems by Popular Genre (Top 5 Genres)</h2>
                <div className="overflow-x-auto mt-4">
                    <table className="table table-zebra w-full">
                        <thead>
                            <tr>
                                <th>Genre</th>
                                <th>Top System (Players)</th>
                                <th>2nd System (Players)</th>
                                <th>3rd System (Players)</th>
                                <th>Total Genre Players</th>
                            </tr>
                        </thead>
                        <tbody>
                            {genreSystemTableData.map((item, index) => (
                                <tr key={index}>
                                    <td>{item.genre}</td>
                                    <td>{item.topSystems[0]?.system || 'N/A'} ({item.topSystems[0]?.count || 0})</td>
                                    <td>{item.topSystems[1]?.system || 'N/A'} ({item.topSystems[1]?.count || 0})</td>
                                    <td>{item.topSystems[2]?.system || 'N/A'} ({item.topSystems[2]?.count || 0})</td>
                                    <td>{item.totalPlayers}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
  );

  const renderGameplayTab = () => (
    <div className="space-y-6">
        <div className="card bg-base-100 shadow-xl">
            <div className="card-body">
                <h2 className="card-title">Gameplay Element Importance</h2>
                <div className="h-80">
                    <Bar 
                        data={{
                            labels: gameplayElementImportanceChartData.map(d => d.name),
                            datasets: [{
                                label: 'Average Rating (out of 5)',
                                data: gameplayElementImportanceChartData.map(d => d.value),
                                backgroundColor: [CHART_COLORS[0], CHART_COLORS[1], CHART_COLORS[2]],
                            }]
                        }}
                        options={{...chartOptionsBase, scales: {...chartOptionsBase.scales, y: {...chartOptionsBase.scales.y, max: 5, title: {display: true, text: 'Average Rating (1-5)'}}}}}
                    />
                </div>
            </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {averageRatingsData?.filter(r => ['Combat Importance', 'Roleplay Importance', 'Exploration Importance'].includes(r.name)).map((item, index) => (
                <div key={item.name} className="card bg-base-100 shadow-xl">
                    <div className="card-body">
                        <h2 className="card-title">{item.name}</h2>
                        <p className="text-xl font-semibold">{item.value}/5</p>
                        <progress 
                            className={`progress w-full mt-2 ${index === 0 ? 'progress-error' : index === 1 ? 'progress-accent' : 'progress-info'}`} 
                            value={item.value * 20}
                            max="100"
                        ></progress>
                    </div>
                </div>
            ))}
        </div>
        <div className="card bg-base-100 shadow-xl">
            <div className="card-body">
                <h2 className="card-title">Typical Session Length</h2>
                <div className="h-80">
                    <Bar 
                        data={{
                            labels: sessionLengthData.map(d => d.name),
                            datasets: [{
                                label: 'Respondents',
                                data: sessionLengthData.map(d => d.value),
                                backgroundColor: CHART_COLORS[3],
                            }]
                        }}
                         options={{...chartOptionsBase, scales: {...chartOptionsBase.scales, x: {...chartOptionsBase.scales.x, ticks: { autoSkip: false, maxRotation: 45, minRotation: 45 } }}}}
                    />
                </div>
            </div>
        </div>
    </div>
  );

  const renderSpendingTab = () => (
    <>
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="card bg-base-100 shadow-xl">
                <div className="card-body">
                    <h2 className="card-title">Annual Spending</h2>
                    <div className="h-80">
                        <Pie 
                            data={{
                                labels: spendingPieData.map(d => d.name),
                                datasets: [{
                                    label: 'Annual Spending',
                                    data: spendingPieData.map(d => d.value),
                                    backgroundColor: CHART_COLORS,
                                }]
                            }}
                            options={pieChartOptionsBase}
                        />
                    </div>
                </div>
            </div>
             <div className="card bg-base-100 shadow-xl">
                <div className="card-body">
                    <h2 className="card-title">Price Sensitivity (Max Willing to Pay)</h2>
                    <div className="h-80">
                        <Line 
                            data={{
                                labels: priceSensitivityChartData.map(d => d.range),
                                datasets: [
                                    {
                                        label: 'Digital Book ($)',
                                        data: priceSensitivityChartData.map(d => d.digital),
                                        borderColor: CHART_COLORS[0],
                                        backgroundColor: `${CHART_COLORS[0]}60`,
                                        fill: true,
                                        tension: 0.3,
                                    },
                                    {
                                        label: 'Hardback Book ($)',
                                        data: priceSensitivityChartData.map(d => d.hardback),
                                        borderColor: CHART_COLORS[1],
                                        backgroundColor: `${CHART_COLORS[1]}60`,
                                        fill: true,
                                        tension: 0.3,
                                    }
                                ]
                            }}
                            options={{...chartOptionsBase, plugins: {...chartOptionsBase.plugins, legend: {display: true, position: 'top'}}}}
                        />
                    </div>
                </div>
            </div>
        </div>
    </div>
    </>
  );
  
  const renderActiveTab = () => {
    switch(activeTab) {
      case 0: return renderPlayerProfileTab();
      case 1: return renderSystemGenreTab();
      case 2: return renderGameplayTab();
      case 3: return renderSpendingTab();
      default: return renderPlayerProfileTab();
    }
  };
  

  return (
    <div className="container mx-auto px-4 py-8"> 
      <div className="text-center mb-10">
        <h1 className="text-4xl font-bold tracking-tight">TTRPG Consumer Sentiments</h1>
        <p className="text-xl mt-3 text-base-content/70">Insights from player surveys (November 2023)</p>
      </div>
      
      <div className="stats shadow w-full mb-10 bg-base-200">
        <div className="stat">
          <div className="stat-figure text-primary text-3xl"><IoPricetagsOutline /></div>
          <div className="stat-title">Total Responses</div>
          <div className="stat-value text-primary">{surveyData.length}</div>
          <div className="stat-desc">Participants in the survey</div>
        </div>
        
        <div className="stat">
          <div className="stat-figure text-secondary text-3xl"><IoGameControllerOutline/></div>
          <div className="stat-title">Most Popular System</div>
          <div className="stat-value text-secondary truncate">
            {systemPreferencesData[0]?.name || 'N/A'}
          </div>
          <div className="stat-desc">{systemPreferencesData[0]?.value || 0} players</div>
        </div>
        
        <div className="stat">
          <div className="stat-figure text-accent text-3xl"><IoColorPaletteOutline /></div>
          <div className="stat-title">Top Genre</div>
          <div className="stat-value text-accent truncate">{genrePreferencesData[0]?.name || 'N/A'}</div>
          <div className="stat-desc">{genrePreferencesData[0]?.value || 0} players</div>
        </div>
      </div>
      
      {renderTabs()}
      <div className="mt-6">
          {renderActiveTab()}
      </div>
    </div>
  );
};

export default TTRPGDashboard;