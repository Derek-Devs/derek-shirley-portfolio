import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Header from "@/components/Header";
import Footer from "@/components/Footer"; 

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  metadataBase: new URL('https://www.derekdevs.com'), 

  title: "Derek Shirley - Senior Data Analyst Portfolio", 
  description: "Portfolio showcasing the data analysis, data engineering, and visualization projects of Derek Shirley, a Senior Data Analyst based in Texas but open to relocation.",
  openGraph: {
    title: "Derek Shirley - Senior Data Analyst Portfolio",
    description: "Explore data-driven projects and insights from Derek Shirley.",
    url: 'https://www.derekdevs.com',
    siteName: 'Derek Shirley Portfolio',
    locale: 'en_US',
    type: 'website',
  },

  twitter: {
    card: 'summary_large_image', 
    title: "Derek Shirley - Senior Data Analyst Portfolio",
    description: "Explore data-driven projects and insights from Derek Shirley.",

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
        <Header /> 

       
        <main className="flex-grow">
           {children} 
        </main>

        <Footer /> 
      </body>
    </html>
  );
}