// src/components/Footer.tsx
"use client";

import React from 'react';
import Link from 'next/link'; 
import { motion } from 'framer-motion';
import { FaGithub, FaLinkedin, FaEnvelope } from 'react-icons/fa';

const Footer: React.FC = () => {
  const currentYear = new Date().getFullYear();
  const iconVariants = { hover: { scale: 1.2, y: -3, transition: { type: 'spring', stiffness: 300 } }, tap: { scale: 0.9 } };

  return (
    <footer className="footer footer-center p-10 bg-base-300 text-base-content rounded">
      <nav className="grid grid-flow-col gap-4">
        <Link href="/about" className="link link-hover">About</Link>
        <Link href="/contact" className="link link-hover">Contact</Link>
        <Link href="/projects" className="link link-hover">Projects</Link>
        <Link href="/insights" className="link link-hover">Insights</Link>
      </nav>

      {/* Social media and contact icons */}
      <nav>
        <div className="grid grid-flow-col gap-4 text-2xl">
          <motion.a
            href="https://www.linkedin.com/in/derekdevs/" 
            target="_blank" // Open in new tab
            rel="noopener noreferrer" // Security best practice
            variants={iconVariants}
            whileHover="hover"
            whileTap="tap"
            className="link link-hover"
            aria-label="LinkedIn Profile" // Accessibility
          >
            <FaLinkedin />
          </motion.a>

          <motion.a
            href="https://github.com/Derek-Devs" 
            target="_blank"
            rel="noopener noreferrer"
            variants={iconVariants}
            whileHover="hover"
            whileTap="tap"
            className="link link-hover"
            aria-label="GitHub Profile"
          >
            <FaGithub />
          </motion.a>

          {/* Email Link */}
          <motion.a
            href="mailto:derek@derekdevs.com" 
            variants={iconVariants}
            whileHover="hover"
            whileTap="tap"
            className="link link-hover"
            aria-label="Send Email"
          >
            <FaEnvelope />
          </motion.a>
        </div>
      </nav>

      {/* Copyright notice */}
      <aside>
        <p>Copyright © {currentYear} - All right reserved by Derek Shirley</p>
      </aside>
    </footer>
  );
};

export default Footer;