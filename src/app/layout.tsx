import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Header from "@/components/Header"; // Global Header
import Footer from "@/components/Footer"; // Global Footer

const inter = Inter({ subsets: ["latin"] });

// Enhanced Metadata for SEO and Social Sharing
export const metadata: Metadata = {
  metadataBase: new URL('https://www.derekdevs.com'), 

  title: "Derek Shirley - Senior Data Analyst Portfolio", 
  description: "Portfolio showcasing the data analysis, data engineering, and visualization projects of Derek Shirley, a Senior Data Analyst based in Texas but open to relocation.",
  openGraph: {
    title: "Derek Shirley - Senior Data Analyst Portfolio",
    description: "Explore data-driven projects and insights from Derek Shirley.",
    // *** REPLACE with a URL to your preview image (e.g., in /public folder) ***
    // images: ['/og-image.png'], // Example: 1200x630px image
    url: 'https://www.derekdevs.com',
    siteName: 'Derek Shirley Portfolio',
    locale: 'en_US',
    type: 'website',
  },

//update this
  twitter: {
    card: 'summary_large_image', // Use 'summary' if you don't have a large image
    title: "Derek Shirley - Senior Data Analyst Portfolio",
    description: "Explore data-driven projects and insights from Derek Shirley.",
     // *** REPLACE with a URL to your preview image (e.g., in /public folder) ***
    // images: ['/twitter-image.png'], // Example: Image for Twitter card
    // Optional: Add your Twitter handle
    // creator: '@YourTwitterHandle',
  },
  keywords: ['Data Analyst', 'Data Scientist', 'Portfolio', 'Derek Shirley', 'Power BI', 'Tableau', 'Python', 'SQL', 'Data Engineering', 'Texas'],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" data-theme="dracula">
      <body className={`${inter.className} flex flex-col min-h-screen bg-base-100 text-base-content`}>
        <Header /> {/* Renders global header */}

        {/* This div grows to push the footer down on short pages */}
        <main className="flex-grow"> {/* Changed div to main for semantics */}
           {children} {/* Page content is injected here */}
        </main>

        <Footer /> {/* Renders global footer */}
      </body>
    </html>
  );
}