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
            Ready to Transform Your Data Strategy?
          </h2>
          <p className="text-lg md:text-xl mb-8 max-w-3xl mx-auto opacity-90"> 
            I am passionate about partnering with forward-thinking leadership teams to build data functions that drive scalable growth and create a competitive advantage. If you are facing a significant challenge in data strategy, architecture, or team leadership, let&apos;s discuss how my experience can benefit your organization.
          </p>
          <div className="flex flex-col sm:flex-row justify-center items-center gap-4">
            <Link href="/projects" className="btn btn-accent shadow-md"> 
              View Projects
            </Link>
            <Link href="/contact" className="btn btn-ghost shadow-md hover:bg-white/20"> 
              Contact Me
            </Link>
            <a
              href="/Derek_Shirley_Resume_2025.pdf" 
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