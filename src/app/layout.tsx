import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Header from "@/components/Header";
import Footer from "@/components/Footer"; 

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  metadataBase: new URL('https://www.derekdevs.com'), 

  title: "Derek Shirley | Data & Analytics Leader", 
  description: "The professional portfolio of Derek Shirley, a strategic data leader with over 8 years of experience building and leading high-impact analytics functions, architecting enterprise data strategy, and driving business growth.",
  
  openGraph: {
    title: "Derek Shirley | Data & Analytics Leader",
    description: "Explore the portfolio of a data leader focused on building data functions, architecting strategy, and driving business impact.",
    url: 'https://www.derekdevs.com',
    siteName: 'Derek Shirley | Portfolio',
    images: [
      {
        url: '/images/og-image.png', 
        width: 1200,
        height: 630,
        alt: 'Derek Shirley - Data & Analytics Leader',
      },
    ],
    locale: 'en_US',
    type: 'website',
  },

  twitter: {
    card: 'summary_large_image', 
    title: "Derek Shirley | Data & Analytics Leader",
    description: "Explore the portfolio of a data leader focused on building data functions, architecting strategy, and driving business impact.",
    images: ['/images/og-image.png'],
  },
  
  keywords: ['Data Strategy', 'Data Leadership', 'Analytics Leader', 'Head of Data', 'Director of Analytics', 'Derek Shirley', 'Power BI', 'Databricks', 'BigQuery', 'Python', 'SQL', 'Data Governance'],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" data-theme="dracula">
      <body className={`${inter.className} flex flex-col min-h-screen bg-base-100 text-base-content`}>
        <Header /> 
        <main className="flex-grow">
           {children} 
        </main>
        <Footer /> 
      </body>
    </html>
  );
}