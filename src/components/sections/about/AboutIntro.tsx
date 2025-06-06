// src/components/sections/about/AboutIntro.tsx
"use client";

import React from 'react';
import Image from 'next/image';
import { motion } from 'framer-motion';

const sectionVariants = {
  hidden: { opacity: 0, y: 30 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.6, ease: 'easeOut' },
  },
};

const AboutIntro: React.FC = () => {
  return (
    <section className="bg-base-100 py-16 md:py-20">
      <div className="container mx-auto px-4">
        <motion.div
          className="flex flex-col md:flex-row items-center gap-8 md:gap-12"
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.2 }}
          variants={sectionVariants}
        >
          <div className="w-48 h-48 sm:w-56 sm:h-56 md:w-64 md:h-64 flex-shrink-0 mx-auto md:mx-0">
            <div className="relative w-full h-full rounded-full overflow-hidden shadow-xl ring-4 ring-primary ring-offset-base-100 ring-offset-4">
              <Image
                src="/images/derek-shirley-photo.jpg"
                alt="Photo of Derek Shirley"
                fill
                style={{ objectFit: 'cover' }}
                sizes="(max-width: 640px) 12rem, (max-width: 768px) 14rem, 16rem"
                priority
              />
            </div>
          </div>

          <div className="text-center md:text-left flex-grow">
            <h2 className="text-3xl md:text-4xl font-bold mb-3 text-primary">
              Hi, I&apos;m Derek Shirley
            </h2>
            <h3 className="text-xl md:text-2xl font-semibold mb-4 text-base-content/90">
              Data Analytics Lead
            </h3>
            <p className="text-lg text-base-content/85 leading-relaxed">
              My mission is to build and lead analytics functions that transform complex data into clear, strategic assets. With over 8 years of experience—from architecting data solutions at startups to leading analytics for major brands like GameStop—I thrive on partnering with executive teams to solve their most challenging problems, drive measurable revenue growth, and build lasting, data-driven cultures.
            </p>
          </div>
        </motion.div>
      </div>
    </section>
  );
};

export default AboutIntro;
