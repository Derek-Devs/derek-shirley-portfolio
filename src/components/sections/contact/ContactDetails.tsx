"use client";

import React from 'react';
import { FiMail, FiLinkedin, FiMapPin, FiGithub } from 'react-icons/fi';

const contactItems = [
  {
    Icon: FiMail,
    label: 'Email',
    href: 'mailto:derek@derekdevs.com',
    display: 'derek@derekdevs.com',
    breakClass: 'break-all',
  },
  {
    Icon: FiLinkedin,
    label: 'LinkedIn',
    href: 'https://www.linkedin.com/in/derekdevs/',
    display: 'linkedin.com/in/derekdevs',
    isExternal: true,
  },
  {
    Icon: FiGithub,
    label: 'GitHub',
    href: 'https://github.com/Derek-Devs',
    display: 'github.com/Derek-Devs',
    isExternal: true,
  },
  {
    Icon: FiMapPin,
    label: 'Location',
    display: 'Dallas-Fort Worth, TX',
  },
];

export default function ContactDetails() {
  return (
    <div className="w-full">
      <h2 className="text-2xl font-semibold mb-6 text-base-content">Contact Details</h2>
      <div className="space-y-5">
        {contactItems.map((item) => (
          <div key={item.label} className="flex items-start gap-4">
            <item.Icon className="h-5 w-5 text-primary mt-1 flex-shrink-0" aria-hidden="true" />
            <div>
              <h3 className="font-medium text-base-content">{item.label}</h3>
              {item.href ? (
                <a
                  href={item.href}
                  target={item.isExternal ? '_blank' : undefined}
                  rel={item.isExternal ? 'noopener noreferrer' : undefined}
                  className={`link link-hover text-base-content/80 ${item.breakClass || ''}`}
                >
                  {item.display}
                </a>
              ) : (
                <p className={`text-base-content/80 ${item.breakClass || ''}`}>{item.display}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}