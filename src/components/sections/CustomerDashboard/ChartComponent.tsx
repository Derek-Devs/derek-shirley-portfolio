// src/components/sections/CustomerDashboard/ChartComponent.tsx
import React, { useState, useEffect } from 'react';
import { Bar, Pie, Line, Doughnut } from 'react-chartjs-2';
import type { ChartData, ChartOptions, ChartType } from 'chart.js';
import { getDaisyUIColor } from '../../../utils/colors'; 

interface ChartComponentProps<TChartType extends ChartType = ChartType> {
  type: TChartType;
  data: ChartData<TChartType>;
  options?: ChartOptions<TChartType>;
}

const ChartComponent = <TChartType extends ChartType = ChartType>({
  type,
  data,
  options,
}: ChartComponentProps<TChartType>) => {
  const [dynamicDefaultOptions, setDynamicDefaultOptions] = useState<ChartOptions<TChartType>>({});

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const baseContentMutedColor = getDaisyUIColor('bc', 0.6);
      const tooltipBackgroundColor = getDaisyUIColor('n');
      const tooltipTextColor = getDaisyUIColor('nc'); 
      const tooltipBorderColor = getDaisyUIColor('a');
      const gridLineColor = getDaisyUIColor('b2', 0.2);

      setDynamicDefaultOptions({
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'top' as const,
            labels: { color: baseContentMutedColor, font: { size: 12 } },
          },
          tooltip: {
            enabled: true,
            backgroundColor: tooltipBackgroundColor,
            titleColor: tooltipTextColor,
            bodyColor: tooltipTextColor,
            borderColor: tooltipBorderColor,
            borderWidth: 1,
            padding: 10,
            cornerRadius: 6,
            boxPadding: 4,
            titleFont: { weight: 'bold' as const },
            displayColors: true,
            usePointStyle: true,
          },
        },
        scales: {
          x: {
            ticks: { color: baseContentMutedColor },
            grid: { color: gridLineColor, borderColor: gridLineColor },
          },
          y: {
            ticks: { color: baseContentMutedColor },
            grid: { color: gridLineColor, borderColor: gridLineColor },
          },
        },
      } as ChartOptions<TChartType>);
    }
  }, []);

  const mergedOptions = { ...dynamicDefaultOptions, ...options };

  if (!data || !data.labels || !data.datasets) {
    return <div className="flex items-center justify-center h-full text-warning">Chart data missing.</div>;
  }
  data.datasets.forEach(dataset => {
    if (!dataset.data) { (dataset.data as unknown[]) = []; }
  });

  let ChartTypeComponent: React.ElementType;
  switch (type) {
    case 'bar': ChartTypeComponent = Bar; break;
    case 'pie': ChartTypeComponent = Pie; break;
    case 'line': ChartTypeComponent = Line; break;
    case 'doughnut': ChartTypeComponent = Doughnut; break;
    default: return <p className="text-error">Unsupported chart type: {type}</p>;
  }

  return (
    <div style={{ position: 'relative', height: '300px', width: '100%' }}>
      <ChartTypeComponent data={data} options={mergedOptions} />
    </div>
  );
};

export default ChartComponent;