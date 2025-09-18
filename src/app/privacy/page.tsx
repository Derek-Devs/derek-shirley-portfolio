"use client"

import React from "react";
import Link from "next/link";
import type { Metadata } from 'next';

export function generateMetadata(): Metadata {
  return {
    title: 'Privacy Policy',
    description: 'Privacy Policy for the professional portfolio website of Derek Shirley.',
  };
}

const Section = ({ title, children }: { title: string, children: React.ReactNode }) => (
  <section className="mb-8">
    <h2 className="text-2xl font-semibold mb-4">{title}</h2>
    {children}
  </section>
);

const PrivacyPage: React.FC = () => {
  const lastUpdated = new Date().toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });

  return (
    <main className="flex-grow container mx-auto px-4 py-12">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-4xl font-bold mb-8 text-center">Privacy Policy</h1>
        <div className="text-sm text-center mb-12">
          Last Updated: {lastUpdated}
        </div>

        <div className="prose prose-lg max-w-none">
          
          <Section title="1. Introduction">
            <p>Welcome to Derek Shirley&apos;s portfolio website. I respect your privacy and am committed to protecting your personal data. This privacy policy will inform you about how I look after your personal data when you visit my website and tell you about your privacy rights.</p>
          </Section>

          <Section title="2. Information I Collect">
            <p>When you use the contact form, I collect your name, email address, and message content. I may also use analytics tools (like Google Analytics) to collect standard usage data, such as your IP address and browser type, to understand how the site is used and to improve the user experience.</p>
          </Section>
          
          <Section title="3. How I Use Your Information">
            <p>I use the information I collect to operate and maintain my website, respond to your inquiries, understand website usage to improve its functionality, and ensure the security of the website.</p>
          </Section>

          <Section title="4. Data Security & Retention">
            <p>The security of your data is important. I strive to use commercially acceptable means to protect your personal data. I will retain your information only for as long as is necessary for the purposes set out in this policy.</p>
          </Section>
          
          <Section title="5. Your Data Rights">
            <p>Depending on your location, you may have rights regarding your personal data, including the right to access, update, or delete the information I hold about you. I do not sell your personal information to any third parties. To exercise any data protection rights, you can contact me at the email address below.</p>
          </Section>
          
          <Section title="6. Third-Party Services">
            <p>My website may contain links to other sites (like LinkedIn or GitHub) and may use services like Google Analytics. I have no control over and assume no responsibility for the content or privacy practices of any third-party sites or services.</p>
          </Section>

          <Section title="7. Children's Privacy">
             <p>My website is intended for a professional audience and does not address anyone under the age of 18. I do not knowingly collect personally identifiable information from children.</p>
          </Section>

          <Section title="8. Changes to This Privacy Policy">
            <p>I may update this privacy policy from time to time. Any changes will be posted on this page, and the &quot;Last Updated&quot; date will reflect the most recent revision.</p>
          </Section>
          
          <Section title="9. Contact Me">
            <p>If you have any questions about this privacy policy, please contact me by email at: <a href="mailto:derek@derekdevs.com" className="link link-primary">derek@derekdevs.com</a></p>
          </Section>

        </div>

        <div className="mt-12 text-center">
          <Link href="/" className="btn btn-primary">
            Return to Home
          </Link>
        </div>
      </div>
    </main>
  );
};

export default PrivacyPage;