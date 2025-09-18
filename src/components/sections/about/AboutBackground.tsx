"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { FaBullseye, FaLayerGroup, FaTools } from 'react-icons/fa';

const titleVariants = {
  hidden: { opacity: 0, y: -20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5 } },
};

const contentVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, delay: 0.2 } },
};

const approachItems = [
  {
    Icon: FaBullseye,
    text: "Business-First Mindset",
  },
  {
    Icon: FaLayerGroup,
    text: "Full-Stack Perspective",
  },
  {
    Icon: FaTools,
    text: "Modern, Scalable Tooling",
  },
];

const AboutBackground: React.FC = () => {
  return (
    <section className="bg-base-200 py-16 md:py-20">
      <div className="container mx-auto px-4 text-center max-w-5xl">
        <motion.h2
          className="text-3xl md:text-4xl font-bold mb-10 text-secondary"
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.3 }}
          variants={titleVariants}
        >
          My Approach
        </motion.h2>

        <motion.div
          className="grid grid-cols-1 md:grid-cols-3 gap-8 md:gap-12 text-lg"
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.3 }}
          variants={contentVariants}
        >
          {approachItems.map(({ Icon, text }) => (
            <div key={text} className="flex flex-col items-center gap-3 text-center">
              <Icon className="text-4xl text-primary" aria-hidden="true" />
              <span className="text-base-content/90 font-semibold mt-2">
                {text}
              </span>
            </div>
          ))}
        </motion.div>
      </div>
    </section>
  );
};

export default AboutBackground;