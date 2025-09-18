"use client";

import React from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { FaGithub, FaLinkedin, FaEnvelope } from 'react-icons/fa';
import type { IconType } from 'react-icons';

interface SocialLink {
  href: string;
  Icon: IconType;
  label: string;
  isExternal?: boolean;
}

const socialLinks: SocialLink[] = [
  { href: "https://www.linkedin.com/in/derekdevs/", Icon: FaLinkedin, label: "LinkedIn Profile", isExternal: true },
  { href: "https://github.com/Derek-Devs", Icon: FaGithub, label: "GitHub Profile", isExternal: true },
  { href: "mailto:derek@derekdevs.com", Icon: FaEnvelope, label: "Send Email" },
];

const Footer: React.FC = () => {
  const currentYear = new Date().getFullYear();
  const iconVariants = {
    hover: { scale: 1.2, y: -3, transition: { type: 'spring', stiffness: 300 } },
    tap: { scale: 0.9 }
  };

  return (
    <footer className="footer footer-center p-10 bg-base-300 text-base-content rounded">
      <nav className="grid grid-flow-col gap-4">
        <Link href="/about" className="link link-hover">About</Link>
        <Link href="/contact" className="link link-hover">Contact</Link>
        <Link href="/projects" className="link link-hover">Projects</Link>
        <Link href="/insights" className="link link-hover">Insights</Link>
      </nav>

      <nav>
        <div className="grid grid-flow-col gap-4 text-2xl">
          {socialLinks.map(({ href, Icon, label, isExternal }) => (
            <motion.a
              key={label}
              href={href}
              target={isExternal ? "_blank" : undefined}
              rel={isExternal ? "noopener noreferrer" : undefined}
              variants={iconVariants}
              whileHover="hover"
              whileTap="tap"
              className="link link-hover"
              aria-label={label}
            >
              <Icon />
            </motion.a>
          ))}
        </div>
      </nav>

      <aside>
        <p>Copyright © {currentYear} - All rights reserved by Derek Shirley</p>
      </aside>
    </footer>
  );
};

export default Footer;