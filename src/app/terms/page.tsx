import React from 'react';
import type { Metadata } from 'next';
import TermsClient from '../../components/legal/TermsClient';

export function generateMetadata(): Metadata {
  return {
    title: 'Terms of Service',
    description: 'Terms of Service for the professional portfolio website of Derek Shirley.',
  };
}

export default function TermsPage() {
  return <TermsClient />;
}