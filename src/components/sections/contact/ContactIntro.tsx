// src/components/sections/contact/ContactIntro.tsx
import React from 'react';

export default function ContactIntro() {
  return (
    <section className="pt-16 md:pt-20">
      <div className="container mx-auto px-4 text-center">

        <h1 className="text-4xl font-bold tracking-tight text-base-content sm:text-5xl lg:text-6xl">
          Let&apos;s Build Something Together
        </h1>

        <p className="mt-6 text-lg leading-8 text-base-content/80 max-w-3xl mx-auto">
          I am always looking for opportunities to partner with innovative companies on their most significant data challenges. Whether you&apos;re looking to build a data function from the ground up, architect a new data strategy, or find a leader for your analytics team, I would be happy to discuss how my experience can help you achieve your goals.
        </p>

      </div>
    </section>
  );
}