// src/components/CustomerDashboard/StatCard.tsx
import React from 'react';

interface StatCardProps {
  title: string;
  value: string | number;
  description?: string;
  IconComponent?: React.ElementType; 
  iconClassName?: string; 
  className?: string;
}

const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  description,
  IconComponent, 
  iconClassName = "h-8 w-8", 
  className,
}) => {
  return (
    <div className={`stat bg-base-100 shadow-lg rounded-box ${className || ''}`}>
      {IconComponent && (
        <div className="stat-figure text-primary">
          <IconComponent className={iconClassName} />
        </div>
      )}
      <div className="stat-title text-base-content/70">{title}</div>
      <div className="stat-value text-2xl font-bold text-primary-focus">{value}</div>
      {description && <div className="stat-desc text-base-content/50">{description}</div>}
    </div>
  );
};

export default StatCard;