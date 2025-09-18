import React from 'react';
import type { Metadata } from 'next';
import PrivacyClient from '../../components/legal/PrivacyClient'

export function generateMetadata(): Metadata {
  return {
    title: 'Privacy Policy',
    description: 'Privacy Policy for the professional portfolio website of Derek Shirley.',
  };
}

export default function PrivacyPage() {
  return <PrivacyClient />;
}