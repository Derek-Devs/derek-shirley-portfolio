"use client"

// src/app/privacy/page.tsx
import React from "react";
import Header from "../components/Header";
import Footer from "../components/Footer";
import Link from "next/link";

const Privacy: React.FC = () => {
  const lastUpdated = "February 27, 2025";

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
            <section className="mb-8">
              <h2 className="text-2xl font-semibold mb-4">1. Introduction</h2>
              <p>
                Welcome to Derek Shirley's portfolio website. I respect your privacy and am committed to protecting your personal data. This privacy policy will inform you about how I look after your personal data when you visit my website and tell you about your privacy rights and how the law protects you.
              </p>
              <p>
                This privacy policy applies to all information collected through my website, as well as any related services, sales, marketing, or events.
              </p>
              <p>
                Please read this privacy policy carefully as it will help you understand what I do with the information that I collect.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold mb-4">2. Information I Collect</h2>
              <p>
                I collect several different types of information for various purposes to provide and improve my services to you.
              </p>
              
              <h3 className="text-xl font-semibold mt-6 mb-3">Personal Information</h3>
              <p>
                While using my website, I may ask you to provide me with certain personally identifiable information that can be used to contact or identify you. This may include, but is not limited to:
              </p>
              <ul className="list-disc pl-8 mb-4">
                <li>Name</li>
                <li>Email address</li>
                <li>Message content (when you use the contact form)</li>
              </ul>
              
              <h3 className="text-xl font-semibold mt-6 mb-3">Usage Data</h3>
              <p>
                I may also collect information on how the website is accessed and used. This usage data may include information such as your computer's Internet Protocol (IP) address, browser type, browser version, the pages of my website that you visit, the time and date of your visit, the time spent on those pages, and other diagnostic data.
              </p>
              
              <h3 className="text-xl font-semibold mt-6 mb-3">Tracking & Cookies Data</h3>
              <p>
                I use cookies and similar tracking technologies to track the activity on my website and hold certain information.
              </p>
              <p>
                Cookies are files with small amounts of data which may include an anonymous unique identifier. Cookies are sent to your browser from a website and stored on your device. Tracking technologies also used are beacons, tags, and scripts to collect and track information and to improve and analyze my website.
              </p>
              <p>
                You can instruct your browser to refuse all cookies or to indicate when a cookie is being sent. However, if you do not accept cookies, you may not be able to use some portions of my website.
              </p>
              <p>
                Examples of cookies I may use:
              </p>
              <ul className="list-disc pl-8 mb-4">
                <li><strong>Session Cookies:</strong> To operate my website.</li>
                <li><strong>Preference Cookies:</strong> To remember your preferences and various settings.</li>
                <li><strong>Security Cookies:</strong> For security purposes.</li>
                <li><strong>Analytics Cookies:</strong> To understand how visitors interact with the website.</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold mb-4">3. How I Use Your Information</h2>
              <p>
                I use the information I collect in various ways, including to:
              </p>
              <ul className="list-disc pl-8 mb-4">
                <li>Provide, operate, and maintain my website</li>
                <li>Improve, personalize, and expand my website</li>
                <li>Understand and analyze how you use my website</li>
                <li>Develop new products, services, features, and functionality</li>
                <li>Communicate with you, including responding to your comments, questions, and requests</li>
                <li>Send you emails regarding updates or other information related to the website</li>
                <li>Find and prevent fraud</li>
                <li>For any other purpose with your consent</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold mb-4">4. Legal Basis for Processing Personal Data Under GDPR</h2>
              <p>
                If you are from the European Economic Area (EEA), my legal basis for collecting and using the personal information described in this privacy policy depends on the personal information I collect and the specific context in which I collect it.
              </p>
              <p>
                I may process your personal information because:
              </p>
              <ul className="list-disc pl-8 mb-4">
                <li>I need to perform a contract with you</li>
                <li>You have given me permission to do so</li>
                <li>The processing is in my legitimate interests and it's not overridden by your rights</li>
                <li>To comply with the law</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold mb-4">5. Retention of Your Data</h2>
              <p>
                I will retain your personal information only for as long as is necessary for the purposes set out in this privacy policy. I will retain and use your information to the extent necessary to comply with my legal obligations, resolve disputes, and enforce my policies.
              </p>
              <p>
                Usage data is generally retained for a shorter period, except when this data is used to strengthen the security or to improve the functionality of my website, or I am legally obligated to retain this data for longer time periods.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold mb-4">6. Transfer of Your Data</h2>
              <p>
                Your information, including personal data, may be transferred to — and maintained on — computers located outside of your state, province, country, or other governmental jurisdiction where the data protection laws may differ from those of your jurisdiction.
              </p>
              <p>
                If you are located outside the United States and choose to provide information to me, please note that I transfer the data, including personal data, to the United States and process it there.
              </p>
              <p>
                Your consent to this privacy policy followed by your submission of such information represents your agreement to that transfer.
              </p>
              <p>
                I will take all steps reasonably necessary to ensure that your data is treated securely and in accordance with this privacy policy and no transfer of your personal data will take place to an organization or a country unless there are adequate controls in place including the security of your data and other personal information.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold mb-4">7. Disclosure of Your Data</h2>
              <p>
                I may disclose your personal information in the following situations:
              </p>
              <ul className="list-disc pl-8 mb-4">
                <li><strong>Business Transactions:</strong> If I am involved in a merger, acquisition or asset sale, your personal data may be transferred.</li>
                <li><strong>Disclosure for Law Enforcement:</strong> Under certain circumstances, I may be required to disclose your personal data if required to do so by law or in response to valid requests by public authorities.</li>
                <li><strong>Other Legal Requirements:</strong> I may disclose your personal information in the good faith belief that such action is necessary to:
                  <ul className="list-disc pl-8 my-2">
                    <li>Comply with a legal obligation</li>
                    <li>Protect and defend my rights or property</li>
                    <li>Prevent or investigate possible wrongdoing in connection with the website</li>
                    <li>Protect the personal safety of users of the website or the public</li>
                    <li>Protect against legal liability</li>
                  </ul>
                </li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold mb-4">8. Security of Your Data</h2>
              <p>
                The security of your data is important to me, but remember that no method of transmission over the Internet, or method of electronic storage is 100% secure. While I strive to use commercially acceptable means to protect your personal data, I cannot guarantee its absolute security.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold mb-4">9. Your Data Protection Rights Under GDPR</h2>
              <p>
                If you are a resident of the European Economic Area (EEA), you have certain data protection rights. I aim to take reasonable steps to allow you to correct, amend, delete, or limit the use of your personal information.
              </p>
              <p>
                If you wish to be informed what personal information I hold about you and if you want it to be removed from my systems, please contact me.
              </p>
              <p>
                In certain circumstances, you have the following data protection rights:
              </p>
              <ul className="list-disc pl-8 mb-4">
                <li><strong>The right to access, update or delete</strong> the information I have on you.</li>
                <li><strong>The right of rectification.</strong> You have the right to have your information rectified if that information is inaccurate or incomplete.</li>
                <li><strong>The right to object.</strong> You have the right to object to my processing of your personal information.</li>
                <li><strong>The right of restriction.</strong> You have the right to request that I restrict the processing of your personal information.</li>
                <li><strong>The right to data portability.</strong> You have the right to be provided with a copy of the information I have on you in a structured, machine-readable and commonly used format.</li>
                <li><strong>The right to withdraw consent.</strong> You also have the right to withdraw your consent at any time where I relied on your consent to process your personal information.</li>
              </ul>
              <p>
                Please note that I may ask you to verify your identity before responding to such requests.
              </p>
              <p>
                You have the right to complain to a Data Protection Authority about my collection and use of your personal data. For more information, please contact your local data protection authority in the European Economic Area (EEA).
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold mb-4">10. Your Data Protection Rights under the California Consumer Privacy Act (CCPA)</h2>
              <p>
                If you are a California resident, you are entitled to learn what data I collect about you, ask to delete your data and not to sell (share) it. To exercise your data protection rights, you can make certain requests and ask me:
              </p>
              <ul className="list-disc pl-8 mb-4">
                <li><strong>What personal information I have about you.</strong> If you make this request, I will return to you:
                  <ul className="list-disc pl-8 my-2">
                    <li>The categories of personal information I have collected about you.</li>
                    <li>The categories of sources from which I collect your personal information.</li>
                    <li>The business or commercial purpose for collecting your personal information.</li>
                    <li>The categories of third parties with whom I share personal information.</li>
                    <li>The specific pieces of personal information I have collected about you.</li>
                    <li>A list of categories of personal information that I have sold, along with the category of any other company I sold it to. If I have not sold your personal information, I will inform you of that fact.</li>
                    <li>A list of categories of personal information that I have disclosed for a business purpose, along with the category of any other company I shared it with.</li>
                  </ul>
                </li>
                <li><strong>To delete your personal information.</strong> If you make this request, I will delete the personal information I hold about you as of the date of your request from my records and direct any service providers to do the same. In some cases, deletion may be accomplished through de-identification of the information. If you choose to delete your personal information, you may not be able to use certain functions that require your personal information to operate.</li>
                <li><strong>To stop selling your personal information.</strong> I don't sell or rent your personal information to any third parties for any purpose. I do not sell your personal information for monetary consideration. However, under some state laws, sharing your data through third-party cookies for online advertising may be considered a "sale" of information. You can opt out of these cookies through browser settings.</li>
              </ul>
              <p>
                Please note, you are entitled to ask me to provide you with this information up to two times in a rolling twelve-month period. When you make this request, the information provided may be limited to the personal information I collected about you in the previous 12 months.
              </p>
              <p>
                To exercise your California data protection rights described above, please send your request(s) by email to: derek@derekdevs.com.
              </p>
              <p>
                Your data protection rights, described above, are covered by the CCPA, short for the California Consumer Privacy Act. To find out more, visit the official California Legislative Information website.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold mb-4">11. Service Providers</h2>
              <p>
                I may employ third-party companies and individuals to facilitate my website ("Service Providers"), to provide the website on my behalf, to perform website-related services or to assist me in analyzing how my website is used.
              </p>
              <p>
                These third parties have access to your personal data only to perform these tasks on my behalf and are obligated not to disclose or use it for any other purpose.
              </p>
              <h3 className="text-xl font-semibold mt-6 mb-3">Analytics</h3>
              <p>
                I may use third-party Service Providers to monitor and analyze the use of my website.
              </p>
              <ul className="list-disc pl-8 mb-4">
                <li><strong>Google Analytics:</strong> Google Analytics is a web analytics service offered by Google that tracks and reports website traffic. Google uses the data collected to track and monitor the use of my website. This data is shared with other Google services. Google may use the collected data to contextualize and personalize the ads of its own advertising network. For more information on the privacy practices of Google, please visit the Google Privacy & Terms web page: <a href="https://policies.google.com/privacy" className="link link-primary" target="_blank" rel="noopener noreferrer">https://policies.google.com/privacy</a></li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold mb-4">12. Links to Other Websites</h2>
              <p>
                My website may contain links to other websites that are not operated by me. If you click on a third-party link, you will be directed to that third party's site. I strongly advise you to review the Privacy Policy of every site you visit.
              </p>
              <p>
                I have no control over and assume no responsibility for the content, privacy policies or practices of any third-party sites or services.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold mb-4">13. Children's Privacy</h2>
              <p>
                My website does not address anyone under the age of 18 ("Children").
              </p>
              <p>
                I do not knowingly collect personally identifiable information from anyone under the age of 18. If you are a parent or guardian and you are aware that your Children has provided me with personal data, please contact me. If I become aware that I have collected personal data from children without verification of parental consent, I take steps to remove that information from my servers.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold mb-4">14. Changes to This Privacy Policy</h2>
              <p>
                I may update my privacy policy from time to time. I will notify you of any changes by posting the new privacy policy on this page.
              </p>
              <p>
                I will let you know via email and/or a prominent notice on my website, prior to the change becoming effective and update the "Last Updated" date at the top of this privacy policy.
              </p>
              <p>
                You are advised to review this privacy policy periodically for any changes. Changes to this privacy policy are effective when they are posted on this page.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold mb-4">15. Contact Me</h2>
              <p>
                If you have any questions about this privacy policy, please contact me:
              </p>
              <ul className="list-disc pl-8 mb-4">
                <li>By email: derek@derekdevs.com</li>
              </ul>
            </section>
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