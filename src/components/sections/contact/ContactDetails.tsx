// src/components/sections/contact/ContactDetails.tsx
"use client";

import React from 'react';
import { FiMail, FiLinkedin, FiMapPin, FiGithub, FiTwitter } from 'react-icons/fi';

export default function ContactDetails() {
  const email = 'derek@derekdevs.com';
  const linkedInUrl = 'https://www.linkedin.com/in/derekdevs/';
  const location = 'Dallas, TX (Open to relocation).';
  const githubUrl = 'https://github.com/Derek-Devs';
  const twitterUrl = 'https://twitter.com/derek_devz'; 

  const contactItems = [
    {
      Icon: FiMail,
      label: 'Email',
      value: email,
      href: `mailto:${email}`,
      display: email,
      breakClass: 'break-all',
    },
    {
      Icon: FiLinkedin,
      label: 'LinkedIn',
      value: linkedInUrl,
      href: linkedInUrl,
      display: 'linkedin.com/in/derekdevs',
    },
    {
      Icon: FiGithub,
      label: 'GitHub',
      value: githubUrl,
      href: githubUrl,
      display: 'github.com/Derek-Devs',
    },
    {
      Icon: FiTwitter,
      label: 'Twitter',
      value: twitterUrl,
      href: twitterUrl,
      display: '@derek_devz', 
    },
    {
      Icon: FiMapPin,
      label: 'Location',
      value: location,
      display: location,
    },
  ];

  return (
    <div className="w-full">
      <h2 className="text-2xl font-semibold mb-6 text-base-content">Contact Details</h2>
      <div className="space-y-5">
        {contactItems.map((item) => (
          item.value && ( 
            <div key={item.label} className="flex items-start gap-4">
              <item.Icon className="h-5 w-5 text-primary mt-1 flex-shrink-0" aria-hidden="true" />
              <div>
                <h3 className="font-medium text-base-content">{item.label}</h3>
                {item.href ? (
                  <a
                    href={item.href}
                    target={item.href.startsWith('mailto:') ? undefined : '_blank'}
                    rel={item.href.startsWith('mailto:') ? undefined : 'noopener noreferrer'}
                    className={`link link-hover text-base-content/80 ${item.breakClass || ''}`}
                  >
                    {item.display}
                  </a>
                ) : (
                  <p className={`text-base-content/80 ${item.breakClass || ''}`}>{item.display}</p>
                )}
              </div>
            </div>
          )
        ))}
      </div>
    </div>
  );
}