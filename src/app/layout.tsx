import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Header from "@/components/Header";
import Footer from "@/components/Footer";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  metadataBase: new URL('https://www.derekdevs.com'),
  
  title: {
    default: "Derek Shirley | Senior Data Analyst & Analytics Lead",
    template: "%s | Derek Shirley",
  },
  description: "The portfolio of Derek Shirley, a data leader with 8+ years of experience in data strategy, analytics engineering, and driving business growth with data.",
  
  openGraph: {
    title: "Derek Shirley | Senior Data Analyst & Analytics Lead Portfolio",
    description: "Explore the portfolio of a data leader focused on building data functions, architecting strategy, and driving business impact.",
    url: 'https://www.derekdevs.com',
    siteName: 'Derek Shirley | Portfolio',
    images: [
      {
        url: '/images/og-image.png',
        width: 1200,
        height: 630,
        alt: 'Derek Shirley - Senior Data Analyst & Analytics Lead',
      },
    ],
    locale: 'en_US',
    type: 'website',
  },

  twitter: {
    card: 'summary_large_image',
    title: "Derek Shirley | Senior Data Analyst & Analytics Lead Portfolio",
    description: "Explore the portfolio of a data leader focused on building data functions, architecting strategy, and driving business impact.",
    images: ['/images/og-image.png'],
  },
  
  keywords: ['Derek Shirley', 'Data Strategy', 'Analytics Engineering', 'Growth Analytics', 'Data Leader', 'Databricks', 'Snowflake', 'dbt', 'BigQuery', 'Python', 'SQL', 'Power BI', 'Data Governance'],
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