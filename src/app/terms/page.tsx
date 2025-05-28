"use client"

// src/app/terms/page.tsx
import React from "react";
import Header from "../components/Header";
import Footer from "../components/Footer";
import Link from "next/link";

const Terms: React.FC = () => {
  const lastUpdated = "February 27, 2025";

  return (
    <div className="flex flex-col min-h-screen bg-base-100 text-base-content">
      <Header />
      <main className="flex-grow container mx-auto px-4 py-12">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-4xl font-bold mb-8 text-center">Terms of Service</h1>
          <div className="text-sm text-center mb-12">
            Last Updated: {lastUpdated}
          </div>

          <div className="prose prose-lg max-w-none">
            <section className="mb-8">
              <h2 className="text-2xl font-semibold mb-4">1. Introduction</h2>
              <p>
                Welcome to Derek Shirley's portfolio website. These Terms of Service ("Terms") govern your access to and use of this website, including any content, functionality, and services offered on or through this website (the "Website").
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
              <h2 className="text-2xl font-semibold mb-4">3. Accessing the Website</h2>
              <p>
                I reserve the right to withdraw or amend this Website, and any service or material provided on the Website, in my sole discretion without notice. I will not be liable if, for any reason, all or any part of the Website is unavailable at any time or for any period.
              </p>
              <p>
                You are responsible for ensuring that all persons who access the Website through your internet connection are aware of these Terms and comply with them.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold mb-4">4. Intellectual Property Rights</h2>
              <p>
                The Website and its entire contents, features, and functionality (including but not limited to all information, software, text, displays, images, video, and audio, and the design, selection, and arrangement thereof) are owned by Derek Shirley, his licensors, or other providers of such material and are protected by United States and international copyright, trademark, patent, trade secret, and other intellectual property or proprietary rights laws.
              </p>
              <p>
                You must not reproduce, distribute, modify, create derivative works of, publicly display, publicly perform, republish, download, store, or transmit any of the material on our Website, except as follows:
              </p>
              <ul className="list-disc pl-8 mb-4">
                <li>Your computer may temporarily store copies of such materials in RAM incidental to your accessing and viewing those materials.</li>
                <li>You may store files that are automatically cached by your Web browser for display enhancement purposes.</li>
                <li>You may print or download one copy of a reasonable number of pages of the Website for your own personal, non-commercial use and not for further reproduction, publication, or distribution.</li>
                <li>If I provide social media features with certain content, you may take such actions as are enabled by such features.</li>
              </ul>
              <p>
                You must not:
              </p>
              <ul className="list-disc pl-8 mb-4">
                <li>Modify copies of any materials from this Website.</li>
                <li>Use any illustrations, photographs, video or audio sequences, or any graphics separately from the accompanying text.</li>
                <li>Delete or alter any copyright, trademark, or other proprietary rights notices from copies of materials from this Website.</li>
              </ul>
              <p>
                If you wish to make any use of material on the Website other than that set out in this section, please address your request to: derek@derekdevs.com.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold mb-4">5. Prohibited Uses</h2>
              <p>
                You may use the Website only for lawful purposes and in accordance with these Terms. You agree not to use the Website:
              </p>
              <ul className="list-disc pl-8 mb-4">
                <li>In any way that violates any applicable federal, state, local, or international law or regulation.</li>
                <li>To transmit, or procure the sending of, any advertising or promotional material, including any "junk mail," "chain letter," "spam," or any other similar solicitation.</li>
                <li>To impersonate or attempt to impersonate me, another user, or any other person or entity.</li>
                <li>To engage in any other conduct that restricts or inhibits anyone's use or enjoyment of the Website, or which may harm me or users of the Website, or expose them to liability.</li>
              </ul>
              <p>
                Additionally, you agree not to:
              </p>
              <ul className="list-disc pl-8 mb-4">
                <li>Use the Website in any manner that could disable, overburden, damage, or impair the site or interfere with any other party's use of the Website.</li>
                <li>Use any robot, spider, or other automatic device, process, or means to access the Website for any purpose, including monitoring or copying any of the material on the Website.</li>
                <li>Use any manual process to monitor or copy any of the material on the Website, or for any other purpose not expressly authorized in these Terms, without our prior written consent.</li>
                <li>Use any device, software, or routine that interferes with the proper working of the Website.</li>
                <li>Introduce any viruses, Trojan horses, worms, logic bombs, or other material that is malicious or technologically harmful.</li>
                <li>Attempt to gain unauthorized access to, interfere with, damage, or disrupt any parts of the Website, the server on which the Website is stored, or any server, computer, or database connected to the Website.</li>
                <li>Attack the Website via a denial-of-service attack or a distributed denial-of-service attack.</li>
                <li>Otherwise attempt to interfere with the proper working of the Website.</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold mb-4">6. Reliance on Information Posted</h2>
              <p>
                The information presented on or through the Website is made available solely for general information purposes. I do not warrant the accuracy, completeness, or usefulness of this information. Any reliance you place on such information is strictly at your own risk. I disclaim all liability and responsibility arising from any reliance placed on such materials by you or any other visitor to the Website, or by anyone who may be informed of any of its contents.
              </p>
              <p>
                This Website may include content provided by third parties. All statements and/or opinions expressed in these materials, and all articles and responses to questions and other content, other than the content provided by me, are solely the opinions and the responsibility of the person or entity providing those materials. These materials do not necessarily reflect my opinion. I am not responsible, or liable to you or any third party, for the content or accuracy of any materials provided by any third parties.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold mb-4">7. Links from the Website</h2>
              <p>
                If the Website contains links to other sites and resources provided by third parties, these links are provided for your convenience only. I have no control over the contents of those sites or resources, and accept no responsibility for them or for any loss or damage that may arise from your use of them. If you decide to access any of the third-party websites linked to this Website, you do so entirely at your own risk and subject to the terms and conditions of use for such websites.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold mb-4">8. Disclaimer of Warranties</h2>
              <p>
                You understand that I cannot and do not guarantee or warrant that files available for downloading from the internet or the Website will be free of viruses or other destructive code. You are responsible for implementing sufficient procedures and checkpoints to satisfy your particular requirements for anti-virus protection and accuracy of data input and output, and for maintaining a means external to our site for any reconstruction of any lost data.
              </p>
              <p className="font-medium">
                TO THE FULLEST EXTENT PROVIDED BY LAW, I WILL NOT BE LIABLE FOR ANY LOSS OR DAMAGE CAUSED BY A DISTRIBUTED DENIAL-OF-SERVICE ATTACK, VIRUSES, OR OTHER TECHNOLOGICALLY HARMFUL MATERIAL THAT MAY INFECT YOUR COMPUTER EQUIPMENT, COMPUTER PROGRAMS, DATA, OR OTHER PROPRIETARY MATERIAL DUE TO YOUR USE OF THE WEBSITE OR ANY SERVICES OR ITEMS OBTAINED THROUGH THE WEBSITE OR TO YOUR DOWNLOADING OF ANY MATERIAL POSTED ON IT, OR ON ANY WEBSITE LINKED TO IT.
              </p>
              <p className="font-medium">
                YOUR USE OF THE WEBSITE, ITS CONTENT, AND ANY SERVICES OR ITEMS OBTAINED THROUGH THE WEBSITE IS AT YOUR OWN RISK. THE WEBSITE, ITS CONTENT, AND ANY SERVICES OR ITEMS OBTAINED THROUGH THE WEBSITE ARE PROVIDED ON AN "AS IS" AND "AS AVAILABLE" BASIS, WITHOUT ANY WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED. NEITHER I NOR ANY PERSON ASSOCIATED WITH ME MAKES ANY WARRANTY OR REPRESENTATION WITH RESPECT TO THE COMPLETENESS, SECURITY, RELIABILITY, QUALITY, ACCURACY, OR AVAILABILITY OF THE WEBSITE.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold mb-4">9. Limitation on Liability</h2>
              <p className="font-medium">
                TO THE FULLEST EXTENT PROVIDED BY LAW, IN NO EVENT WILL I, MY AFFILIATES, OR THEIR LICENSORS, SERVICE PROVIDERS, EMPLOYEES, AGENTS, OFFICERS, OR DIRECTORS BE LIABLE FOR DAMAGES OF ANY KIND, UNDER ANY LEGAL THEORY, ARISING OUT OF OR IN CONNECTION WITH YOUR USE, OR INABILITY TO USE, THE WEBSITE, ANY WEBSITES LINKED TO IT, ANY CONTENT ON THE WEBSITE OR SUCH OTHER WEBSITES, INCLUDING ANY DIRECT, INDIRECT, SPECIAL, INCIDENTAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, INCLUDING BUT NOT LIMITED TO, PERSONAL INJURY, PAIN AND SUFFERING, EMOTIONAL DISTRESS, LOSS OF REVENUE, LOSS OF PROFITS, LOSS OF BUSINESS OR ANTICIPATED SAVINGS, LOSS OF USE, LOSS OF GOODWILL, LOSS OF DATA, AND WHETHER CAUSED BY TORT (INCLUDING NEGLIGENCE), BREACH OF CONTRACT, OR OTHERWISE, EVEN IF FORESEEABLE.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold mb-4">10. Indemnification</h2>
              <p>
                You agree to defend, indemnify, and hold harmless me, my affiliates, licensors, and service providers, and my and their respective officers, directors, employees, contractors, agents, licensors, suppliers, successors, and assigns from and against any claims, liabilities, damages, judgments, awards, losses, costs, expenses, or fees (including reasonable attorneys' fees) arising out of or relating to your violation of these Terms or your use of the Website, including, but not limited to, any use of the Website's content, services, and products other than as expressly authorized in these Terms.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold mb-4">11. Governing Law and Jurisdiction</h2>
              <p>
                All matters relating to the Website and these Terms, and any dispute or claim arising therefrom or related thereto, shall be governed by and construed in accordance with the internal laws of the State of Washington without giving effect to any choice or conflict of law provision or rule.
              </p>
              <p>
                Any legal suit, action, or proceeding arising out of, or related to, these Terms or the Website shall be instituted exclusively in the federal courts of the United States or the courts of the State of Washington, in each case located in Seattle. You waive any and all objections to the exercise of jurisdiction over you by such courts and to venue in such courts.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold mb-4">12. Waiver and Severability</h2>
              <p>
                No waiver by me of any term or condition set out in these Terms shall be deemed a further or continuing waiver of such term or condition or a waiver of any other term or condition, and any failure to assert a right or provision under these Terms shall not constitute a waiver of such right or provision.
              </p>
              <p>
                If any provision of these Terms is held by a court or other tribunal of competent jurisdiction to be invalid, illegal, or unenforceable for any reason, such provision shall be eliminated or limited to the minimum extent such that the remaining provisions of the Terms will continue in full force and effect.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold mb-4">13. Entire Agreement</h2>
              <p>
                The Terms constitute the sole and entire agreement between you and me regarding the Website and supersede all prior and contemporaneous understandings, agreements, representations, and warranties, both written and oral, regarding the Website.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold mb-4">14. Contact Information</h2>
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
      <Footer />
    </div>
  );
};

export default Terms;