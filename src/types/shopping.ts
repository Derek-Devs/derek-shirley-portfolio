export interface ShoppingTrendItem {
    'Customer ID': string; 
    Age: number;
    Gender: 'Male' | 'Female' | string; 
    'Item Purchased': string;
    Category: string;
    'Purchase Amount (USD)': number;
    Location: string;
    Size: string;
    Color: string;
    Season: 'Spring' | 'Summer' | 'Fall' | 'Winter' | string;
    'Review Rating': number;
    'Subscription Status': 'Yes' | 'No';
    'Shipping Type': string;
    'Discount Applied': 'Yes' | 'No'; 
    'Promo Code Used': 'Yes' | 'No'; 
    'Previous Purchases': number;
    'Payment Method': string;
    'Frequency of Purchases': string;
  }