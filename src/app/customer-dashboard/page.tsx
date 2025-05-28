// src/app/customer-dashboard/page.tsx
"use client";

import React, { useState, useEffect } from 'react';
import Papa from 'papaparse';
import { ShoppingTrendItem } from '../../types/shopping'; 
import { getDaisyUIColor } from '../../utils/colors'; 

import StatCard from '../../components/sections/CustomerDashboard/StatCard';
import ChartComponent from '../../components/sections/CustomerDashboard/ChartComponent'; 
import { FaUsers, FaDollarSign, FaShoppingCart } from 'react-icons/fa';

import {
  Chart as ChartJS,
  CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, ArcElement, PointElement, LineElement, Filler,
  type ChartData, type ChartOptions
} from 'chart.js';

ChartJS.register(
  CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, ArcElement, PointElement, LineElement, Filler
);

type BarChartData = ChartData<'bar', number[], string>;
type PieChartData = ChartData<'pie', number[], string>;
type LineChartData = ChartData<'line', number[], string>;
type DoughnutChartData = ChartData<'doughnut', number[], string>;

export default function CustomerDashboardPage() {
  const [rawData, setRawData] = useState<ShoppingTrendItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [totalRevenue, setTotalRevenue] = useState<number>(0);
  const [totalCustomers, setTotalCustomers] = useState<number>(0);
  const [averagePurchaseAmount, setAveragePurchaseAmount] = useState<number>(0);

  const [genderDistributionData, setGenderDistributionData] = useState<PieChartData | null>(null);
  const [categoryPopularityData, setCategoryPopularityData] = useState<BarChartData | null>(null);
  const [ageDistributionData, setAgeDistributionData] = useState<BarChartData | null>(null);
  const [seasonalSalesData, setSeasonalSalesData] = useState<LineChartData | null>(null);
  const [reviewRatingData, setReviewRatingData] = useState<BarChartData | null>(null);
  const [subscriptionStatusData, setSubscriptionStatusData] = useState<DoughnutChartData | null>(null);
  const [paymentMethodData, setPaymentMethodData] = useState<BarChartData | null>(null);
  const [purchaseFrequencyData, setPurchaseFrequencyData] = useState<BarChartData | null>(null);
  const [discountAppliedData, setDiscountAppliedData] = useState<PieChartData | null>(null);
  const [shippingTypeData, setShippingTypeData] = useState<BarChartData | null>(null);
  const [salesByLocationData, setSalesByLocationData] = useState<BarChartData | null>(null);

  useEffect(() => {
    const parseCSV = async () => {
      try {
        setLoading(true); setError(null);
        const response = await fetch('/shopping_trends.csv');
        if (!response.ok) throw new Error(`Workspace CSV Error: ${response.statusText} (${response.status})`);
        const csvText = await response.text();
        Papa.parse<ShoppingTrendItem>(csvText, {
          header: true, skipEmptyLines: true, dynamicTyping: true,
          complete: (results) => {
            if (results.errors.length > 0) {
              console.error("PapaParse Errors:", results.errors);
              setError(`Parse CSV Error: ${results.errors.map(e => e.message).join(", ")}`);
            }
            setRawData(results.data.filter(item => item && item['Customer ID'] !== undefined));
            setLoading(false);
          },
          error: (err: Error) => { setError(err.message); setLoading(false); console.error("PapaParse Error:", err); }
        });
      } catch (e: any) { setError(e.message || "Unknown fetch/parse error."); setLoading(false); console.error("Fetch/Parse Error:", e); }
    };
    parseCSV();
  }, []);

  useEffect(() => {
    if (rawData.length > 0 && typeof window !== 'undefined') {
      const numCustomers = rawData.length;
      setTotalCustomers(numCustomers);
      const revenue = rawData.reduce((sum, item) => sum + (item['Purchase Amount (USD)'] || 0), 0);
      setTotalRevenue(revenue);
      setAveragePurchaseAmount(numCustomers > 0 ? revenue / numCustomers : 0);

      const genderCounts: Record<string, number> = rawData.reduce((acc, item) => { acc[item.Gender || "Unknown"] = (acc[item.Gender || "Unknown"] || 0) + 1; return acc; }, {} as Record<string, number>);
      setGenderDistributionData({ labels: Object.keys(genderCounts), datasets: [{ label: 'Gender Distribution', data: Object.values(genderCounts), backgroundColor: [getDaisyUIColor('p'), getDaisyUIColor('s'), getDaisyUIColor('a'), getDaisyUIColor('wa')], hoverOffset: 4 }] });

      const categoryCounts = rawData.reduce((acc, item) => { acc[item.Category || "Uncategorized"] = (acc[item.Category || "Uncategorized"] || 0) + 1; return acc; }, {} as Record<string, number>);
      const sortedCategories = Object.entries(categoryCounts).sort(([,a],[,b]) => b-a);
      setCategoryPopularityData({ labels: sortedCategories.map(e => e[0]), datasets: [{ label: 'Purchases by Category', data: sortedCategories.map(e => e[1]), backgroundColor: getDaisyUIColor('su', 0.6), borderColor: getDaisyUIColor('su'), borderWidth: 1 }] });

      const ageBrackets: Record<string, number> = { '18-25': 0, '26-35': 0, '36-45': 0, '46-55': 0, '56-65': 0, '66+': 0, 'Unknown': 0 };
      rawData.forEach(item => { const age = item.Age; if (age >= 18 && age <= 25) ageBrackets['18-25']++; else if (age >= 26 && age <= 35) ageBrackets['26-35']++; else if (age >= 36 && age <= 45) ageBrackets['36-45']++; else if (age >= 46 && age <= 55) ageBrackets['46-55']++; else if (age >= 56 && age <= 65) ageBrackets['56-65']++; else if (age >= 66) ageBrackets['66+']++; else ageBrackets['Unknown']++; });
      setAgeDistributionData({ labels: Object.keys(ageBrackets), datasets: [{ label: 'Customers by Age Group', data: Object.values(ageBrackets), backgroundColor: getDaisyUIColor('wa', 0.6), borderColor: getDaisyUIColor('wa'), borderWidth: 1 }] });

      const seasonalSales = rawData.reduce((acc, item) => { if (item.Season && typeof item['Purchase Amount (USD)'] === 'number') acc[item.Season] = (acc[item.Season] || 0) + item['Purchase Amount (USD)']; return acc; }, {} as Record<string, number>);
      const orderedSeasons = ['Spring', 'Summer', 'Fall', 'Winter'].filter(s => seasonalSales[s] !== undefined);
      setSeasonalSalesData({ labels: orderedSeasons, datasets: [{ label: 'Total Sales (USD) by Season', data: orderedSeasons.map(s => seasonalSales[s]), fill: true, backgroundColor: getDaisyUIColor('in', 0.2), borderColor: getDaisyUIColor('in'), tension: 0.1 }] });

      const ratingCounts = rawData.reduce((acc, item) => { const r = Math.round(item['Review Rating']); if (r >=1 && r <=5) acc[r.toString()] = (acc[r.toString()] || 0) + 1; return acc; }, {} as Record<string, number>);
      setReviewRatingData({ labels: Object.keys(ratingCounts).sort((a,b) => parseInt(a)-parseInt(b)), datasets: [{ label: 'Reviews by Rating', data: Object.keys(ratingCounts).sort((a,b) => parseInt(a)-parseInt(b)).map(k => ratingCounts[k]), backgroundColor: getDaisyUIColor('a', 0.6), borderColor: getDaisyUIColor('a'), borderWidth: 1 }] });
      
      const subscriptionCounts = rawData.reduce((acc, item) => { acc[item['Subscription Status']] = (acc[item['Subscription Status']] || 0) + 1; return acc; }, {} as Record<string, number>);
      setSubscriptionStatusData({ labels: Object.keys(subscriptionCounts), datasets: [{ label: 'Subscription Status', data: Object.values(subscriptionCounts), backgroundColor: [getDaisyUIColor('su'), getDaisyUIColor('er')], hoverOffset: 4 }] });

      const paymentMethodCounts = rawData.reduce((acc, item) => { acc[item['Payment Method'] || "Unknown"] = (acc[item['Payment Method'] || "Unknown"] || 0) + 1; return acc; }, {} as Record<string, number>);
      const sortedPaymentMethods = Object.entries(paymentMethodCounts).sort(([,a],[,b]) => b-a);
      setPaymentMethodData({ labels: sortedPaymentMethods.map(e => e[0]), datasets: [{ label: 'Preferred Payment Methods', data: sortedPaymentMethods.map(e => e[1]), backgroundColor: getDaisyUIColor('p', 0.7), borderColor: getDaisyUIColor('p'), borderWidth: 1 }] });
      
      const frequencyCounts = rawData.reduce((acc,item) => { acc[item['Frequency of Purchases'] || "Unknown"] = (acc[item['Frequency of Purchases'] || "Unknown"] || 0) + 1; return acc; }, {} as Record<string, number>);
      const purchaseOrder = ['Weekly', 'Fortnightly', 'Monthly', 'Bi-Monthly', 'Quarterly', 'Annually', 'Every Few Weeks', "Unknown"];
      const sortedFrequencies = purchaseOrder.filter(freq => frequencyCounts[freq] !== undefined);
      setPurchaseFrequencyData({ labels: sortedFrequencies, datasets: [{ label: 'Purchase Frequency', data: sortedFrequencies.map(f => frequencyCounts[f]), backgroundColor: getDaisyUIColor('s', 0.6), borderColor: getDaisyUIColor('s'), borderWidth: 1 }] });

      const discountAppliedCounts = rawData.reduce((acc, item) => { acc[item['Discount Applied'] || 'Unknown'] = (acc[item['Discount Applied'] || 'Unknown'] || 0) + 1; return acc; }, {} as Record<string, number>);
      setDiscountAppliedData({ labels: Object.keys(discountAppliedCounts), datasets: [{ label: 'Discount Applied', data: Object.values(discountAppliedCounts), backgroundColor: [getDaisyUIColor('su'), getDaisyUIColor('wa'), getDaisyUIColor('er')], hoverOffset: 4 }] });

      const shippingTypeCounts = rawData.reduce((acc, item) => { acc[item['Shipping Type'] || "Unknown"] = (acc[item['Shipping Type'] || "Unknown"] || 0) + 1; return acc; }, {} as Record<string, number>);
      setShippingTypeData({ labels: Object.keys(shippingTypeCounts), datasets: [{ label: 'Shipping Types Used', data: Object.values(shippingTypeCounts), backgroundColor: getDaisyUIColor('in', 0.7), borderColor: getDaisyUIColor('in'), borderWidth: 1 }] });
      
      const locationSales = rawData.reduce((acc, item) => { if (item.Location && typeof item['Purchase Amount (USD)'] === 'number') acc[item.Location] = (acc[item.Location] || 0) + item['Purchase Amount (USD)']; return acc; }, {} as Record<string, number>);
      const sortedLocationSales = Object.entries(locationSales).sort(([,a],[,b]) => b-a).slice(0,10);
      setSalesByLocationData({ labels: sortedLocationSales.map(e => e[0]), datasets: [{ label: 'Top 10 Locations by Sales (USD)', data: sortedLocationSales.map(e => e[1]), backgroundColor: getDaisyUIColor('er', 0.6), borderColor: getDaisyUIColor('er'), borderWidth: 1 }] });
    }
  }, [rawData]);

  if (loading) {
    return ( <div className="flex flex-col justify-center items-center h-screen bg-base-300"> <span className="loading loading-spinner loading-lg text-primary"></span> <p className="mt-4 text-xl text-base-content">Loading ...</p> </div> );
  }
  if (error) {
    return ( <div className="flex justify-center items-center h-screen bg-base-300 p-4"> <div className="alert alert-error shadow-lg max-w-md"> <div> <svg xmlns="http://www.w3.org/2000/svg" className="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 14l2-2m0 0l2-2m-2 2l-2 2m2-2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg> <span>Error: {error}</span> </div> </div> </div> );
  }
  if (rawData.length === 0 && !loading) {
     return <div className="text-center mt-10 text-xl p-5 text-base-content">No data. Check CSV.</div>;
  }

  const commonBarChartOptions: ChartOptions<'bar'> = { scales: { y: { beginAtZero: true } } };
  const commonHorizontalBarChartOptions: ChartOptions<'bar'> = { indexAxis: 'y', scales: { x: { beginAtZero: true } } };

  return (
    <div className="p-4 md:p-6 lg:p-8 bg-base-200 min-h-screen" data-theme="cupcake">
      <header className="mb-8 text-center">
        <h1 className="text-4xl font-bold text-primary tracking-tight">Customer Shopping Trends</h1>
        <p className="text-lg text-base-content/70">Insights Dashboard</p>
      </header>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6 mb-8">
        <StatCard title="Total Revenue" value={`$${totalRevenue.toLocaleString(undefined, {mfd:2,mxfd:2})}`} IconComponent={FaDollarSign} />
        <StatCard title="Total Customers" value={totalCustomers.toLocaleString()} IconComponent={FaUsers} />
        <StatCard title="Avg. Purchase Value" value={`$${averagePurchaseAmount.toLocaleString(undefined, {mfd:2,mxfd:2})}`} IconComponent={FaShoppingCart} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 md:gap-6">
        {genderDistributionData && ( <div className="card bg-base-100 shadow-xl"> <div className="card-body"> <h2 className="card-title text-lg">Gender Distribution</h2> <ChartComponent type="pie" data={genderDistributionData} /> </div> </div> )}
        {categoryPopularityData && ( <div className="card bg-base-100 shadow-xl md:col-span-2 xl:col-span-1"> <div className="card-body"> <h2 className="card-title text-lg">Top Product Categories</h2> <ChartComponent type="bar" data={categoryPopularityData} options={commonHorizontalBarChartOptions} /> </div> </div> )}
        {ageDistributionData && ( <div className="card bg-base-100 shadow-xl"> <div className="card-body"> <h2 className="card-title text-lg">Customer Age Groups</h2> <ChartComponent type="bar" data={ageDistributionData} options={commonBarChartOptions} /> </div> </div> )}
        {seasonalSalesData && ( <div className="card bg-base-100 shadow-xl"> <div className="card-body"> <h2 className="card-title text-lg">Seasonal Sales</h2> <ChartComponent type="line" data={seasonalSalesData} options={commonBarChartOptions} /> </div> </div> )}
        {reviewRatingData && ( <div className="card bg-base-100 shadow-xl"> <div className="card-body"> <h2 className="card-title text-lg">Review Ratings</h2> <ChartComponent type="bar" data={reviewRatingData} options={commonBarChartOptions} /> </div> </div> )}
        {subscriptionStatusData && ( <div className="card bg-base-100 shadow-xl"> <div className="card-body"> <h2 className="card-title text-lg">Subscription Status</h2> <ChartComponent type="doughnut" data={subscriptionStatusData} /> </div> </div> )}
        {paymentMethodData && ( <div className="card bg-base-100 shadow-xl"> <div className="card-body"> <h2 className="card-title text-lg">Payment Methods</h2> <ChartComponent type="bar" data={paymentMethodData} options={commonHorizontalBarChartOptions} /> </div> </div> )}
        {purchaseFrequencyData && ( <div className="card bg-base-100 shadow-xl"> <div className="card-body"> <h2 className="card-title text-lg">Purchase Frequency</h2> <ChartComponent type="bar" data={purchaseFrequencyData} options={commonBarChartOptions}/> </div> </div> )}
        {discountAppliedData && ( <div className="card bg-base-100 shadow-xl"> <div className="card-body"> <h2 className="card-title text-lg">Discount Applied Rate</h2> <ChartComponent type="pie" data={discountAppliedData} /> </div> </div> )}
        {shippingTypeData && ( <div className="card bg-base-100 shadow-xl"> <div className="card-body"> <h2 className="card-title text-lg">Shipping Types</h2> <ChartComponent type="bar" data={shippingTypeData} options={commonBarChartOptions}/> </div> </div> )}
        {salesByLocationData && ( <div className="card bg-base-100 shadow-xl md:col-span-2 xl:col-span-3"> <div className="card-body"> <h2 className="card-title text-lg">Top 10 Sales by Location</h2> <ChartComponent type="bar" data={salesByLocationData} options={commonBarChartOptions}/> </div> </div> )}
      </div>

      <footer className="mt-12 text-center text-sm text-base-content/50">
        <p>Shopping Trends Dashboard &copy; {new Date().getFullYear()}</p>
      </footer>
    </div>
  );
}
const mfd = 'minimumFractionDigits';
const mxfd = 'maximumFractionDigits';
