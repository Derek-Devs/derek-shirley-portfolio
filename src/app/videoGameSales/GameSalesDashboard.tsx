'use client';

import React, { useState, useEffect, useMemo } from 'react';
import _ from 'lodash';
import Papa from 'papaparse';
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
  Colors,
  type TooltipItem,
  type ChartType,
} from 'chart.js';
import { Bar, Line, Pie } from 'react-chartjs-2';
import { IoInformationCircleOutline, IoCloseCircleOutline, IoWarningOutline, IoCheckmarkCircleOutline } from 'react-icons/io5';

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
  Colors
);

interface GameData {
  Rank: number;
  Name: string;
  Platform: string;
  Year: number;
  Genre: string;
  Publisher: string;
  NA_Sales: number;
  EU_Sales: number;
  JP_Sales: number;
  Other_Sales: number;
  Global_Sales: number;
}

interface PlatformSales {
  Platform: string;
  Global_Sales: number;
}

interface PublisherSales {
  Publisher: string;
  Global_Sales: number;
}

interface GenreSales {
  Genre: string;
  Global_Sales: number;
}

interface YearlySales {
  Year: number;
  Global_Sales: number;
  NA_Sales: number;
  EU_Sales: number;
  JP_Sales: number;
  Other_Sales: number;
}

interface RegionalSales {
  NA_Sales: number;
  EU_Sales: number;
  JP_Sales: number;
  Other_Sales: number;
}

const GameSalesDashboard: React.FC = () => {
  const [data, setData] = useState<GameData[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>('');
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  useEffect(() => {
    if (!isClient) return;

    const csvFilePath = `/vgsales.csv`;

    fetch(csvFilePath)
      .then(response => {
        if (!response.ok) {
          throw new Error(`Failed to fetch CSV: ${response.status} ${response.statusText}`);
        }
        return response.text();
      })
      .then(csvText => {
        Papa.parse<GameData>(csvText, {
          header: true,
          dynamicTyping: true,
          skipEmptyLines: true,
          complete: (results) => { 
            if (results.errors.length) {
              setError("Error parsing CSV file. Check console for details.");
              console.error("CSV Parsing Errors:", results.errors);
            }
            const validData = results.data.filter(
              (row): row is GameData =>
                row &&
                typeof row.Rank === 'number' &&
                typeof row.Name === 'string' &&
                row.Name.trim() !== '' &&
                (typeof row.Year === 'number' || (typeof row.Year === 'string' && !isNaN(parseInt(row.Year, 10)))) &&
                typeof row.Global_Sales === 'number' &&
                !isNaN(row.Global_Sales)
            );
            
            const processedData = validData.map(row => ({
                ...row,
                Year: typeof row.Year === 'string' ? parseInt(row.Year, 10) : row.Year
            })).filter(row => typeof row.Year === 'number' && !isNaN(row.Year));

            setData(processedData);
            setLoading(false);
          },
          error: (parseError: Error) => { 
            setError(`Error parsing CSV: ${parseError.message}`);
            setLoading(false);
          }
        });
      })
      .catch(fetchError => {
        const errorMessage = fetchError instanceof Error ? fetchError.message : String(fetchError);
        setError(`Error loading data: ${errorMessage}. Ensure 'vgsales.csv' is in the 'public' folder.`);
        setLoading(false);
      });
  }, [isClient]);

  const topGames = useMemo((): GameData[] => {
    if (!data || data.length === 0) return [];
    return _.orderBy(data, ['Global_Sales'], ['desc']).slice(0, 10);
  }, [data]);

  const salesByPlatform = useMemo((): PlatformSales[] => {
    if (!data || data.length === 0) return [];
    const platformGroups = _.groupBy(data, 'Platform');
    return Object.keys(platformGroups).map(platform => ({
      Platform: platform,
      Global_Sales: _.sumBy(platformGroups[platform], 'Global_Sales')
    })).sort((a, b) => b.Global_Sales - a.Global_Sales);
  }, [data]);

  const salesByPublisher = useMemo((): PublisherSales[] => {
    if (!data || data.length === 0) return [];
    const publisherGroups = _.groupBy(data, 'Publisher');
    const allSalesByPublisher = Object.keys(publisherGroups).map(publisher => ({
      Publisher: publisher,
      Global_Sales: _.sumBy(publisherGroups[publisher], 'Global_Sales')
    }));
    return _.orderBy(allSalesByPublisher, ['Global_Sales'], ['desc']).slice(0, 10);
  }, [data]);

  const salesByGenre = useMemo((): GenreSales[] => {
    if (!data || data.length === 0) return [];
    const genreGroups = _.groupBy(data, 'Genre');
    return Object.keys(genreGroups).map(genre => ({
      Genre: genre,
      Global_Sales: _.sumBy(genreGroups[genre], 'Global_Sales')
    })).sort((a,b) => b.Global_Sales - a.Global_Sales);
  }, [data]);

  const salesByYear = useMemo((): YearlySales[] => {
    if (!data || data.length === 0) return [];
    const validData = data.filter(game => 
        typeof game.Year === 'number' && 
        !isNaN(game.Year) && 
        game.Year >= 1980 && 
        game.Year <= 2020 
    );
    const yearGroups = _.groupBy(validData, 'Year');
    return Object.keys(yearGroups)
      .map(yearStr => {
        const year = parseInt(yearStr, 10);
        return {
          Year: year,
          Global_Sales: _.sumBy(yearGroups[yearStr], 'Global_Sales'),
          NA_Sales: _.sumBy(yearGroups[yearStr], 'NA_Sales'),
          EU_Sales: _.sumBy(yearGroups[yearStr], 'EU_Sales'),
          JP_Sales: _.sumBy(yearGroups[yearStr], 'JP_Sales'),
          Other_Sales: _.sumBy(yearGroups[yearStr], 'Other_Sales')
        };
      })
      .sort((a, b) => a.Year - b.Year);
  }, [data]);

  const regionalSalesComparison = useMemo((): RegionalSales => {
    if (!data || data.length === 0) return { NA_Sales: 0, EU_Sales: 0, JP_Sales: 0, Other_Sales: 0 };
    return {
      NA_Sales: _.sumBy(data, 'NA_Sales'),
      EU_Sales: _.sumBy(data, 'EU_Sales'),
      JP_Sales: _.sumBy(data, 'JP_Sales'),
      Other_Sales: _.sumBy(data, 'Other_Sales')
    };
  }, [data]);


  const chartOptionsBase = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      tooltip: {
        callbacks: {
          label: function(context: TooltipItem<ChartType>) {
            let tipLabel = context.dataset.label || '';
            if (tipLabel) {
              tipLabel += ': ';
            }
            const parsed = context.parsed;
            if (parsed !== null && typeof parsed === 'object') {
              // If parsed is an object, attempt to access 'y' and check its type
              const yValue = (parsed as { y?: unknown }).y; // Access 'y' via an assertion
              if (typeof yValue === 'number') {
                tipLabel += yValue.toFixed(2) + " million";
              }
              // Note: This might need to be expanded if 'y' isn't always the value
              // or for horizontal bars where 'x' might be the value.
              // For a truly generic base, context.formattedValue could be a fallback.
            } else if (typeof parsed === 'number') {
              tipLabel += parsed.toFixed(2) + " million";
            }
            return tipLabel;
          }
        }
      }
    },
    scales: {
      x: {
        ticks: {
          maxRotation: 45,
          minRotation: 45,
          autoSkip: true,
          maxTicksLimit: 15,
        },
        grid: {
            display: false,
        }
      },
      y: {
        title: {
          display: true,
          text: `Sales (millions)`
        },
        grid: {
            color: 'rgba(200, 200, 200, 0.2)',
        },
        beginAtZero: true,
        ticks: {
            // Other y-axis tick specific options can go here if needed
        }
      }
    }
  };

  const pieChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      tooltip: {
        callbacks: {
          label: function(context: TooltipItem<'pie'>) {
            let label = context.label || '';
            const value = context.parsed;
            
            const datasetData = (context.dataset.data as number[] | undefined) || [];
            const total = datasetData.reduce((a: number, b: number): number => a + b, 0);
            
            const percentage = total > 0 && value !== null && value !== undefined ? ((value / total) * 100).toFixed(1) : "0.0";
            if (label) {
              label += ': ';
            }
            if (value !== null && value !== undefined) {
              label += value.toFixed(2) + ` million (${percentage}%)`;
            }
            return label;
          }
        }
      },
      colors: {
        enabled: true
      },
      title: { 
        display: false,
        text: `Chart Title`
      }
    },
  };


  if (!isClient) {
    return (
      <div className="container mx-auto p-4 flex justify-center items-center min-h-screen">
        <span className="loading loading-lg"></span>
        <p className="ml-2">Loading dashboard...</p>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4">
      <div className="bg-base-100 shadow-xl rounded-box p-6 mb-6">
        <h1 className="text-3xl font-bold mb-6 text-center">Video Game Sales Dashboard</h1>

        {loading && (
          <div role="alert" className="alert alert-info mb-6">
            <IoInformationCircleOutline className="stroke-current flex-shrink-0 w-6 h-6" />
            <span>Loading video game sales data... Please wait.</span>
          </div>
        )}

        {error && (
          <div role="alert" className="alert alert-error mb-6">
            <IoCloseCircleOutline className="stroke-current flex-shrink-0 h-6 h-6" />
            <span>{error}</span>
          </div>
        )}

        {!loading && !error && data.length === 0 && (
          <div role="alert" className="alert alert-warning mb-6">
            <IoWarningOutline className="stroke-current flex-shrink-0 h-6 h-6" />
            <span>No data available. Processed 0 records. Please check if &apos;vgsales.csv&apos; is in the &apos;public&apos; folder and is not empty or corrupted.</span>
          </div>
        )}

        {data.length > 0 && !loading && !error && (
          <>
            <div role="alert" className="alert alert-success mb-6">
              <IoCheckmarkCircleOutline className="stroke-current flex-shrink-0 h-6 h-6" />
              <span>Loaded {data.length} video game sales records successfully!</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-base-200 p-4 rounded-box shadow">
                <h2 className="text-xl font-semibold mb-2">Top 10 Games by Global Sales</h2>
                <div style={{ height: '400px' }}>
                  <Bar
                    options={{...chartOptionsBase, plugins: {...chartOptionsBase.plugins, title: { display: true, text: `Top 10 Games by Global Sales` }}}}
                    data={{
                      labels: topGames.map(game => game.Name),
                      datasets: [
                        {
                          label: 'Global Sales',
                          data: topGames.map(game => game.Global_Sales),
                          backgroundColor: 'rgba(100, 25, 230, 0.6)',
                          borderColor: 'rgba(100, 25, 230, 1)',
                          borderWidth: 1,
                        },
                      ],
                    }}
                  />
                </div>
              </div>

              <div className="bg-base-200 p-4 rounded-box shadow">
                <h2 className="text-xl font-semibold mb-2">Global Sales by Platform (Top 10)</h2>
                  <div style={{ height: '400px' }}>
                  <Bar
                    options={{...chartOptionsBase, plugins: {...chartOptionsBase.plugins, title: { display: true, text: `Global Sales by Platform (Top 10)` }}}}
                    data={{
                      labels: salesByPlatform.slice(0,10).map(item => item.Platform),
                      datasets: [
                        {
                          label: 'Global Sales',
                          data: salesByPlatform.slice(0,10).map(item => item.Global_Sales),
                          backgroundColor: 'rgba(54, 211, 153, 0.6)',
                          borderColor: 'rgba(54, 211, 153, 1)',
                          borderWidth: 1,
                        },
                      ],
                    }}
                  />
                  </div>
              </div>

              <div className="bg-base-200 p-4 rounded-box shadow">
                <h2 className="text-xl font-semibold mb-2">Top 10 Publishers by Global Sales</h2>
                <div style={{ height: '400px' }}>
                  <Bar
                    options={{...chartOptionsBase, plugins: {...chartOptionsBase.plugins, title: { display: true, text: `Top 10 Publishers by Global Sales` }}}}
                    data={{
                      labels: salesByPublisher.map(item => item.Publisher),
                      datasets: [
                        {
                          label: 'Global Sales',
                          data: salesByPublisher.map(item => item.Global_Sales),
                          backgroundColor: 'rgba(248, 114, 114, 0.6)',
                          borderColor: 'rgba(248, 114, 114, 1)',
                          borderWidth: 1,
                        },
                      ],
                    }}
                  />
                </div>
              </div>

              <div className="bg-base-200 p-4 rounded-box shadow">
                <h2 className="text-xl font-semibold mb-2">Sales Distribution by Genre (Top 10)</h2>
                <div style={{ height: '400px' }}>
                  <Pie
                    options={{...pieChartOptions, plugins: {...pieChartOptions.plugins, title: { display: true, text: `Sales Distribution by Genre (Top 10)` }}}}
                    data={{
                      labels: salesByGenre.slice(0,10).map(item => item.Genre),
                      datasets: [
                        {
                          label: 'Global Sales',
                          data: salesByGenre.slice(0,10).map(item => item.Global_Sales),
                        },
                      ],
                    }}
                  />
                </div>
              </div>

              <div className="bg-base-200 p-4 rounded-box shadow md:col-span-2">
                <h2 className="text-xl font-semibold mb-2">Sales Trends Over Time (1980-2020)</h2>
                <div style={{ height: '450px' }}>
                  <Line
                    options={{...chartOptionsBase, plugins: {...chartOptionsBase.plugins, title: { display: true, text: `Sales Trends Over Time (1980-2020)` }, legend: { display: true, position: 'bottom'}}}}
                    data={{
                      labels: salesByYear.map(item => item.Year.toString()),
                      datasets: [
                        {
                          label: 'Global Sales',
                          data: salesByYear.map(item => item.Global_Sales),
                          borderColor: 'rgba(100, 25, 230, 1)',
                          backgroundColor: 'rgba(100, 25, 230, 0.2)',
                          tension: 0.1,
                          fill: true,
                        },
                        {
                          label: 'NA Sales',
                          data: salesByYear.map(item => item.NA_Sales),
                          borderColor: 'rgba(54, 211, 153, 1)',
                          backgroundColor: 'rgba(54, 211, 153, 0.2)',
                          tension: 0.1,
                          fill: true,
                        },
                        {
                          label: 'EU Sales',
                          data: salesByYear.map(item => item.EU_Sales),
                          borderColor: 'rgba(248, 114, 114, 1)',
                          backgroundColor: 'rgba(248, 114, 114, 0.2)',
                          tension: 0.1,
                          fill: true,
                        },
                        {
                          label: 'JP Sales',
                          data: salesByYear.map(item => item.JP_Sales),
                          borderColor: 'rgba(251, 189, 35, 1)',
                          backgroundColor: 'rgba(251, 189, 35, 0.2)',
                          tension: 0.1,
                          fill: true,
                        },
                      ],
                    }}
                  />
                </div>
              </div>

              <div className="bg-base-200 p-4 rounded-box shadow md:col-span-2">
                <h2 className="text-xl font-semibold mb-2">Regional Sales Comparison</h2>
                <div style={{ height: '400px' }}>
                  <Bar
                    options={{...chartOptionsBase, plugins: {...chartOptionsBase.plugins, title: { display: true, text: `Regional Sales Comparison` }}}}
                    data={{
                      labels: ['North America', 'Europe', 'Japan', 'Other Regions'],
                      datasets: [
                        {
                          label: 'Total Sales',
                          data: [
                            regionalSalesComparison.NA_Sales,
                            regionalSalesComparison.EU_Sales,
                            regionalSalesComparison.JP_Sales,
                            regionalSalesComparison.Other_Sales
                          ],
                          backgroundColor: [
                            'rgba(54, 211, 153, 0.6)',
                            'rgba(248, 114, 114, 0.6)',
                            'rgba(251, 189, 35, 0.6)',
                            'rgba(100, 25, 230, 0.6)'
                          ],
                          borderColor: [
                            'rgba(54, 211, 153, 1)',
                            'rgba(248, 114, 114, 1)',
                            'rgba(251, 189, 35, 1)',
                            'rgba(100, 25, 230, 1)'
                          ],
                          borderWidth: 1,
                        },
                      ],
                    }}
                  />
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default GameSalesDashboard;