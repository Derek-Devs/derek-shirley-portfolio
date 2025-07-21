"use client"

// src/app/privacy/page.tsx
import React from "react";
import Header from "../../components/Header";
import Footer from "../../components/Footer";
import Link from "next/link";

const Section = ({ title, children }: { title: string, children: React.ReactNode }) => (
  <section className="mb-8">
    <h2 className="text-2xl font-semibold mb-4">{title}</h2>
    {children}
  </section>
);

const Privacy: React.FC = () => {
  const lastUpdated = new Date().toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });

  return (
    <div className="flex flex-col min-h-screen bg-base-100 text-base-content">
      <Header />
      <main className="flex-grow container mx-auto px-4 py-12">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-4xl font-bold mb-8 text-center">Privacy Policy</h1>
          <div className="text-sm text-center mb-12">
            Last Updated: {lastUpdated}
          </div>

          <div className="prose prose-lg max-w-none">
            
            <Section title="1. Introduction">
              <p>Welcome to Derek Shirley&apos;s portfolio website. I respect your privacy and am committed to protecting your personal data. This privacy policy will inform you about how I look after your personal data when you visit my website and tell you about your privacy rights and how the law protects you.</p>
              <p>This privacy policy applies to all information collected through my website, as well as any related services, sales, marketing, or events.</p>
            </Section>

            <Section title="2. Information I Collect">
              <p>When you use the contact form, I collect your name, email address, and message content. I may also use analytics tools (like Google Analytics) to collect standard usage data, such as your IP address and browser type, to understand how the site is used and to improve the user experience.</p>
            </Section>
            
            <Section title="3. How I Use Your Information">
              <p>I use the information I collect to:</p>
              <ul className="list-disc pl-8">
                <li>Operate and maintain my website.</li>
                <li>Respond to your inquiries and communicate with you.</li>
                <li>Understand and analyze website usage to improve its functionality.</li>
                <li>Prevent fraud and ensure the security of the website.</li>
              </ul>
            </Section>

            <Section title="4. Data Security & Retention">
              <p>The security of your data is important. While no method of transmission over the Internet is 100% secure, I strive to use commercially acceptable means to protect your personal data. I will retain your information only for as long as is necessary for the purposes set out in this policy, such as responding to your messages.</p>
            </Section>
            
            <Section title="5. Your Data Rights (GDPR & CCPA)">
              <p>Depending on your location, you may have rights regarding your personal data, including the right to access, update, or delete the information I hold about you. I do not sell your personal information to any third parties. To exercise any data protection rights, you can contact me at the email address below.</p>
            </Section>
            
            <Section title="6. Third-Party Services">
              <p>My website is built with modern tools and may contain links to other sites (like LinkedIn or GitHub). I have no control over and assume no responsibility for the content or privacy practices of any third-party sites or services. I use Google Analytics to monitor website traffic.</p>
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
      <Footer />
    </div>
  );
};

export default Privacy;