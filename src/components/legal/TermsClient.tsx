"use client";

import React from "react";
import Link from "next/link";

export default function TermsClient() {
  const lastUpdated = new Date().toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  return (
    <main className="flex-grow container mx-auto px-4 py-12">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-4xl font-bold mb-8 text-center">Terms of Service</h1>
        <div className="text-sm text-center mb-12">
          Last Updated: {lastUpdated}
        </div>

        <div className="prose prose-lg max-w-none">
          {/* All your original <section> content goes here */}
          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">1. Introduction</h2>
            <p>
              Welcome to Derek Shirley&apos;s portfolio website. These Terms of Service (&quot;Terms&quot;) govern your access to and use of this website, including any content, functionality, and services offered on or through this website (the &quot;Website&quot;).
            </p>
            <p>
              Please read these Terms carefully before using the Website. By using the Website, you accept and agree to be bound by these Terms. If you do not agree to these Terms, you must not access or use the Website.
            </p>
          </section>
          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">2. Changes to the Terms</h2>
            <p>
              I may revise and update these Terms from time to time at my sole discretion. All changes are effective immediately when posted, and apply to all access to and use of the Website thereafter.
            </p>
            <p>
              Your continued use of the Website following the posting of revised Terms means that you accept and agree to the changes. You are expected to check this page from time to time so you are aware of any changes, as they are binding on you.
            </p>
          </section>
          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">3. Intellectual Property Rights</h2>
            <p>
              The Website and its entire contents, features, and functionality are owned by Derek Shirley, his licensors, or other providers of such material and are protected by United States and international copyright, trademark, and other intellectual property or proprietary rights laws.
            </p>
            <p>
              You must not reproduce, distribute, modify, create derivative works of, publicly display, publicly perform, republish, download, store, or transmit any of the material on our Website, except for your own personal, non-commercial use.
            </p>
            <p>
              If you wish to make any use of material on the Website other than that set out in this section, please address your request to: derek@derekdevs.com.
            </p>
          </section>
          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">4. Prohibited Uses</h2>
            <p>
              You may use the Website only for lawful purposes and in accordance with these Terms. You agree not to use the Website in any way that violates any applicable federal, state, local, or international law or regulation, or to engage in any conduct that restricts or inhibits anyone&apos;s use or enjoyment of the Website.
            </p>
          </section>
          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">5. Disclaimer of Warranties</h2>
            <p>
              YOUR USE OF THE WEBSITE IS AT YOUR OWN RISK. THE WEBSITE IS PROVIDED ON AN &quot;AS IS&quot; AND &quot;AS AVAILABLE&quot; BASIS, WITHOUT ANY WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED.
            </p>
          </section>
          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">6. Limitation on Liability</h2>
            <p>
              TO THE FULLEST EXTENT PROVIDED BY LAW, IN NO EVENT WILL I BE LIABLE FOR DAMAGES OF ANY KIND, UNDER ANY LEGAL THEORY, ARISING OUT OF OR IN CONNECTION WITH YOUR USE, OR INABILITY TO USE, THE WEBSITE OR ANY CONTENT ON THE WEBSITE.
            </p>
          </section>
          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">7. Governing Law and Jurisdiction</h2>
            <p>
              All matters relating to the Website and these Terms shall be governed by and construed in accordance with the internal laws of the <strong>State of Texas</strong> without giving effect to any choice or conflict of law provision or rule.
            </p>
            <p>
              Any legal suit, action, or proceeding arising out of, or related to, these Terms or the Website shall be instituted exclusively in the federal courts of the United States or the courts of the <strong>State of Texas, in each case located in Tarrant County</strong>. You waive any and all objections to the exercise of jurisdiction over you by such courts and to venue in such courts.
            </p>
          </section>
          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">8. Contact Information</h2>
            <p>
              All feedback, comments, requests for technical support, and other communications relating to the Website should be directed to: derek@derekdevs.com.
            </p>
          </section>
        </div>

        <div className="mt-12 text-center">
          <Link href="/" className="btn btn-primary">
            Return to Home
          </Link>
        </div>
      </div>
    </main>
  );
}