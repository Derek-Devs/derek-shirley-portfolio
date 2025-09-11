// src/components/sections/about/AboutBackground.tsx
"use client"; 

import React from 'react';
import { motion } from 'framer-motion';
import { FaUniversity, FaAward } from 'react-icons/fa';

const titleVariants = {
  hidden: { opacity: 0, y: -20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5 } },
};

const contentVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, delay: 0.2 } }, 
};

const AboutBackground: React.FC = () => {
  return (
    <section className="bg-base-200 py-16 md:py-20">
      <div className="container mx-auto px-4 text-center max-w-4xl"> 
        <motion.h2
          className="text-3xl md:text-4xl font-bold mb-8 text-secondary"
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.3 }}
          variants={titleVariants}
        >
          Education & Accolades
        </motion.h2>

        <motion.div
          className="flex flex-col sm:flex-row justify-center items-center gap-6 sm:gap-12 text-lg" 
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.3 }}
          variants={contentVariants} 
        >

          <div className="flex items-center gap-3">
            <FaUniversity className="text-3xl text-primary flex-shrink-0" aria-hidden="true" />
            <span className="text-base-content/90">
              Undergraduate Studies in Computer Science at The University of North Texas 🦅
            </span>
          </div>


          <div className="flex items-center gap-3">
            <FaAward className="text-3xl text-primary flex-shrink-0" aria-hidden="true" />
            <span className="text-base-content/90">
              Proud Eagle Scout
            </span>
          </div>
        </motion.div>
      </div>
    </section>
  );
};

export default AboutBackground;