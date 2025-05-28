// src/app/contact/page.tsx
"use client"

import React from 'react';

import ContactIntro from '@/components/sections/contact/ContactIntro';
import ContactForm from '@/components/sections/contact/ContactForm';
import ContactDetails from '@/components/sections/contact/ContactDetails';

export default function ContactPage() {
  return (
    <main className="overflow-x-hidden bg-base-100 text-base-content py-12 md:py-16">

      <ContactIntro />

      <div className="container mx-auto px-4 py-12 md:py-16">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-start">
          <ContactForm /> 
          <ContactDetails />
        </div>
      </div>

    </main>
  );
}

