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

const ctaButtons = [
  { href: "/projects", text: "View Projects", className: "btn btn-accent shadow-md" },
  { href: "/contact", text: "Contact Me", className: "btn btn-ghost shadow-md hover:bg-white/20" },
  { href: "/Derek_Shirley_Resume_2025.pdf", text: "Download Resume", className: "btn btn-outline border-primary-content text-primary-content hover:bg-primary-content hover:text-primary shadow-md", download: true },
];

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
            Ready to Solve Your Data Challenges?
          </h2>
          <p className="text-lg md:text-xl mb-8 max-w-3xl mx-auto opacity-90">
            I specialize in transforming complex, multi-source data into a competitive advantage. Whether you&apos;re looking to build a new analytics capability, architect a modern data stack, or extract deeper insights from your existing systems, let&apos;s connect and discuss how my experience can help you achieve your goals.
          </p>
          <div className="flex flex-col sm:flex-row justify-center items-center gap-4">
            {ctaButtons.map(({ href, text, className, download }) => {
              const isExternal = href.startsWith('http') || download;
              const Component = isExternal ? 'a' : Link;
              
              return (
                <Component
                  key={text}
                  href={href}
                  className={className}
                  {...(download && { download: true })}
                  {...(isExternal && !download && { target: '_blank', rel: 'noopener noreferrer' })}
                >
                  {text}
                </Component>
              );
            })}
          </div>
        </motion.div>
      </div>
    </section>
  );
};

export default AboutCTA;