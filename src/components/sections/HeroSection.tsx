// src/components/sections/HeroSection.tsx
"use client";

import React from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';
import Image from 'next/image';
import { FaProjectDiagram, FaEnvelope, FaDownload, FaArrowDown } from 'react-icons/fa'; 

const HeroSection: React.FC = () => {
  const columnVariants = {
    hidden: { opacity: 0, y: 30 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.7, ease: 'easeOut' }, 
    },
  };

  const textContainerVariants = {
    hidden: {},
    visible: {
      transition: {
        staggerChildren: 0.1, 
        delayChildren: 0.2,  
      },
    },
  };

  const textItemVariants = {
    hidden: { opacity: 0, x: -30 }, 
    visible: {
      opacity: 1,
      x: 0,
      transition: { duration: 0.5, ease: 'easeOut' },
    },
  };

  const buttonVariants = {
    hover: {
      scale: 1.05,
    },
    tap: { scale: 0.95 },
  };


  return (
    <section className="hero min-h-[calc(100vh-4rem)] bg-gradient-to-br from-base-100 via-base-100 to-base-200 py-10 md:py-16 lg:py-20 px-4 relative">
      <div className="hero-content flex flex-col lg:flex-row items-center gap-10 lg:gap-16 max-w-6xl mx-auto">
        <motion.div
          className="w-64 h-64 sm:w-72 sm:h-72 md:w-80 md:h-80 lg:w-96 lg:h-96 flex-shrink-0 order-first lg:order-none mx-auto lg:mx-0"
          variants={columnVariants}
          initial="hidden"
          animate="visible"
          transition={{ delay: 0.1 }}
          whileHover={{ scale: 1.03, transition: { duration: 0.3 } }} 
        >
          <div className="relative w-full h-full rounded-full overflow-hidden shadow-2xl border-4 border-primary"> 
            <Image
              src="/images/derek-shirley-photo.jpg" 
              alt="Photo of Derek Shirley"
              fill
              style={{ objectFit: 'cover' }}
              sizes="(max-width: 640px) 16rem, (max-width: 768px) 18rem, (max-width: 1024px) 20rem, 24rem"
              priority
            />
          </div>
        </motion.div>

        <motion.div
          className="flex-grow text-center lg:text-left"
          variants={textContainerVariants}
          initial="hidden"
          animate="visible"
        >
          <motion.h1
            className="text-4xl sm:text-5xl md:text-6xl font-bold mb-3 bg-gradient-to-r from-primary via-secondary to-accent bg-clip-text text-transparent"
            variants={textItemVariants}
          >
            Derek Shirley
          </motion.h1>

          <motion.h2
            className="text-xl sm:text-2xl md:text-3xl font-semibold mb-5 text-base-content/90" 
            variants={textItemVariants}
          >
            Data & Analytics Leader | Architecting Data-Driven Strategy
          </motion.h2>

          <motion.p
            className="mb-8 text-base sm:text-lg text-base-content/80 max-w-xl mx-auto lg:mx-0"
            variants={textItemVariants}
          >
            I build the data functions that power business growth. With over 8 years of experience, I partner with executive teams to transform complex data into strategic assets—architecting everything from foundational pipelines to the C-suite dashboards that drive key decisions.
          </motion.p>

          <motion.div
            className="flex flex-col sm:flex-row justify-center lg:justify-start gap-4"
            variants={textItemVariants}
          >
            <motion.div variants={buttonVariants} whileHover="hover" whileTap="tap">
              <Link href="/projects" className="btn btn-primary w-full sm:w-auto">
                <FaProjectDiagram className="mr-2" />
                View Projects
              </Link>
            </motion.div>
            <motion.div variants={buttonVariants} whileHover="hover" whileTap="tap">
              <Link href="/contact" className="btn btn-secondary w-full sm:w-auto">
                <FaEnvelope className="mr-2" />
                Contact Me
              </Link>
            </motion.div>
            <motion.div variants={buttonVariants} whileHover="hover" whileTap="tap">
              <a
                href="/Derek_Shirley_Resume_2025.pdf"
                download
                className="btn btn-outline w-full sm:w-auto"
              >
                <FaDownload className="mr-2" />
                Download Resume
              </a>
            </motion.div>
          </motion.div>
        </motion.div>
      </div>
      
      <motion.div
        className="absolute bottom-8 left-1/2 -translate-x-1/2"
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 1.5, duration: 0.5 }}
      >
        <motion.div
          animate={{ y: [0, 8, 0] }}
          transition={{
            duration: 1.5,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        >
          <FaArrowDown className="text-2xl text-base-content/50" />
        </motion.div>
      </motion.div>
    </section>
  );
};

export default HeroSection;