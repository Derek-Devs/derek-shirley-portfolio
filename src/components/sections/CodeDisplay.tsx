
"use client"

import React, { useEffect, useState } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { atomDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface CodeDisplayProps {
  filePath: string;
  language: string;
}

const CodeDisplay: React.FC<CodeDisplayProps> = ({ filePath, language }) => {
  const [code, setCode] = useState<string>('Loading code...');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  useEffect(() => {
    const fetchCode = async () => {
      try {
        setIsLoading(true);
        const response = await fetch(filePath);
        
        if (!response.ok) {
          throw new Error(`Failed to load code: ${response.statusText}`);
        }
        
        const text = await response.text();
        setCode(text);
        setError(null);
      } catch (err) {
        console.error('Error loading code file:', err);
        setError('Error loading code. Please try again later.');
        setCode('');
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchCode();
  }, [filePath]);
  
  if (isLoading) {
    return <div className="p-4 text-center">Loading code...</div>;
  }
  
  if (error) {
    return <div className="p-4 text-center text-red-500">{error}</div>;
  }
  
  return (
    <div className="code-container rounded-md overflow-hidden">
      <SyntaxHighlighter 
        language={language} 
        style={atomDark}
        showLineNumbers
        wrapLines
        className="text-sm"
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
};

export default CodeDisplay;