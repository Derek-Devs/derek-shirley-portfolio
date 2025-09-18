"use client";

import React from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';

const CallToActionSection: React.FC = () => {
  const contentVariants = {
    hidden: { opacity: 0, y: 30 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.6,
        ease: "easeOut",
      },
    },
  };

  return (
    <section className="py-20 md:py-28 bg-base-300 text-center">
      <div className="container mx-auto px-4">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.3 }}
          variants={contentVariants}
        >
          <h2 className="text-3xl md:text-4xl font-bold mb-4 text-base-content">
            Ready to Solve Your Data Challenges?
          </h2>
          <p className="text-lg md:text-xl mb-8 max-w-2xl mx-auto text-base-content/80">
            My passion is turning complex data into strategic assets. If these projects resonate with you and you are looking for someone to help solve significant data challenges and drive business growth, let us start a conversation.
          </p>
          <div className="flex flex-col sm:flex-row justify-center items-center gap-4">
            <Link
              href="/contact"
              className="btn btn-primary btn-lg"
            >
              Get In Touch
            </Link>
             <a
               href="mailto:derek@derekdevs.com"
               className="btn btn-outline btn-lg"
             >
               derek@derekdevs.com
             </a>
          </div>
        </motion.div>
      </div>
    </section>
  );
};

export default CallToActionSection;