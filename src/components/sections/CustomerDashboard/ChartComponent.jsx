// src/components/sections/CustomerDashboard/ChartComponent.jsx
import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types'; 
import { Bar, Pie, Line, Doughnut } from 'react-chartjs-2';

import { getDaisyUIColor } from '../../../utils/colors';

const ChartComponent = ({ type, data, options: userOptions }) => {
  const [dynamicDefaultOptions, setDynamicDefaultOptions] = useState(null);

  useEffect(() => {
    if (typeof window !== 'undefined') { 
      const baseContentMutedColor = getDaisyUIColor('bc', 0.6);
      const tooltipBackgroundColor = getDaisyUIColor('n');
      const tooltipTextColor = getDaisyUIColor('nc');
      const tooltipBorderColor = getDaisyUIColor('a');
      const gridLineColor = getDaisyUIColor('b2', 0.2);

      const commonPlugins = {
        legend: {
          position: 'top',
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
          titleFont: { weight: 'bold' },
          displayColors: true,
          usePointStyle: true,
        },
      };

      let scalesSettings; 

      if (type === 'bar' || type === 'line' || type === 'scatter' || type === 'bubble') {
        scalesSettings = {
          x: {
            ticks: { color: baseContentMutedColor },
            grid: {
              color: gridLineColor,
              borderColor: gridLineColor,
            },
          },
          y: {
            ticks: { color: baseContentMutedColor },
            grid: {
              color: gridLineColor,
              borderColor: gridLineColor,
            },
          },
        };
      } else if (type === 'radar') {
        scalesSettings = {
          r: {
            angleLines: { display: true, color: gridLineColor },
            grid: {
              color: gridLineColor,
            },
            pointLabels: { color: baseContentMutedColor, font: { size: 10 } },
            ticks: { display: true, backdropColor: 'transparent', color: baseContentMutedColor },
          },
        };
      }

      const baseOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: commonPlugins,
      };

      let newDefaultOptionsObject;

      if (scalesSettings !== undefined) {
        newDefaultOptionsObject = {
          ...baseOptions,
          scales: scalesSettings, 
        };
      } else {
        newDefaultOptionsObject = {
          ...baseOptions, 
        };
      }
      
      setDynamicDefaultOptions(newDefaultOptionsObject);
    }
  }, [type]); 


  const mergedOptions = { ...(dynamicDefaultOptions || {}), ...(userOptions || {}) };

  if (!data || !data.labels || !data.datasets || data.datasets.some(ds => !ds.data)) {
    return <div className="flex items-center justify-center h-full text-warning">Chart data missing or invalid.</div>;
  }

  let ChartTypeComponent;
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


ChartComponent.propTypes = {
  type: PropTypes.oneOf(['bar', 'pie', 'line', 'doughnut', 'scatter', 'bubble', 'radar']).isRequired,
  data: PropTypes.shape({
    labels: PropTypes.arrayOf(PropTypes.any), 
    datasets: PropTypes.arrayOf(
      PropTypes.shape({
        data: PropTypes.arrayOf(PropTypes.any).isRequired,

        label: PropTypes.string,
      })
    ).isRequired,
  }).isRequired,
  options: PropTypes.object, 
};


ChartComponent.defaultProps = {
  options: {},
};

export default ChartComponent;