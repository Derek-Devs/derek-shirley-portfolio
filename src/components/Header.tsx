"use client";

import React from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { FaChartBar } from 'react-icons/fa';

const navLinks = [
  { href: "/", label: "Home" },
  { href: "/projects", label: "Projects" },
  { href: "/insights", label: "Insights" },
  { href: "/about", label: "About" },
  { href: "/contact", label: "Contact" },
];

const Header: React.FC = () => {
  const navItemVariants = {
    hover: { y: -2, transition: { duration: 0.2 } },
    tap: { y: 1, transition: { duration: 0.1 } },
  };

  return (
    <motion.header
      initial={{ y: -100, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
      className="bg-base-200 shadow-md sticky top-0 z-50"
    >
      <div className="navbar container mx-auto px-4">
        <div className="navbar-start">
          <Link href="/" className="btn btn-ghost h-auto py-2 px-3 normal-case">
            <FaChartBar className="text-2xl text-primary" />
            <div className="flex flex-col items-start ml-2">
              <span className="text-lg font-bold leading-tight">Derek Shirley</span>
              <span className="text-xs font-normal text-base-content/70 -mt-1 leading-tight">
                Growth & Analytics Engineering
              </span>
            </div>
          </Link>
        </div>

        <div className="navbar-end hidden lg:flex">
          <ul className="menu menu-horizontal px-1">
            {navLinks.map(({ href, label }) => (
              <li key={href}>
                <Link href={href} className="btn btn-ghost">
                  <motion.span variants={navItemVariants} whileHover="hover" whileTap="tap">{label}</motion.span>
                </Link>
              </li>
            ))}
          </ul>
        </div>

        <div className="navbar-end lg:hidden">
          <div className="dropdown dropdown-end">
            <label tabIndex={0} className="btn btn-ghost lg:hidden" aria-label="Open navigation menu">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h8m-8 6h16" />
              </svg>
            </label>
            <ul tabIndex={0} className="menu menu-sm dropdown-content mt-3 z-[100] p-2 shadow bg-base-100 rounded-box w-52">
              {navLinks.map(({ href, label }) => (
                <li key={href}><Link href={href}>{label}</Link></li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </motion.header>
  );
};

export default Header;