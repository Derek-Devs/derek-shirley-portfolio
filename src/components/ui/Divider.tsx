// src/components/ui/Divider.tsx
import React from 'react';

interface DividerProps {
  className?: string; 
}

const Divider: React.FC<DividerProps> = ({ className = '' }) => {

  return <div className={`divider my-0 ${className}`}></div>;
};

export default Divider;