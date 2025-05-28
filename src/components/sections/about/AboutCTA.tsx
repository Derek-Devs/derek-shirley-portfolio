// src/components/sections/about/AboutCTA.tsx
"use client"; 

import React from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';

const sectionVariants = {
  hidden: { opacity: 0, y: 30 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.6, ease: "easeOut" },
  },
};

const AboutCTA: React.FC = () => {
  return (
    <section className="bg-gradient-to-r from-primary to-secondary text-primary-content py-16 md:py-20">
      <div className="container mx-auto px-4 text-center">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.3 }} 
          variants={sectionVariants}
        >
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            Let&apos;s Connect!
          </h2>
          <p className="text-lg md:text-xl mb-8 max-w-2xl mx-auto opacity-90"> 
            I&apos;m always interested in discussing new challenges, data strategies, or potential opportunities (and I&apos;m open to relocation!). Feel free to explore my projects or get in touch.
          </p>
          <div className="flex flex-col sm:flex-row justify-center items-center gap-4">
            <Link href="/projects" className="btn btn-accent shadow-md"> 
              View Projects
            </Link>
            <Link href="/contact" className="btn btn-ghost shadow-md hover:bg-white/20"> 
              Contact Me
            </Link>
            <a
              href="/derek_shirley_resume.pdf" 
              download
              className="btn btn-outline border-primary-content text-primary-content hover:bg-primary-content hover:text-primary shadow-md"
            >
              Download Resume
            </a>
          </div>
        </motion.div>
      </div>
    </section>
  );
};

export default AboutCTA;