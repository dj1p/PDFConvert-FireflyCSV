import pdfplumber
import pandas as pd
import re
from pathlib import Path
from datetime import datetime
import sys

class BankStatementConverter:
    def __init__(self, input_path, output_path=None):
        self.input_path = Path(input_path)
        self.output_path = Path(output_path) if output_path else self.input_path.parent / f"{self.input_path.stem}_firefly.csv"
        
    def extract_tables_from_pdf(self):
        """Extract all tables from PDF"""
        all_tables = []
        
        with pdfplumber.open(self.input_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    if table:
                        all_tables.extend(table)
        
        return all_tables
    
    def parse_amount(self, withdrawal_deposit_value):
        """Parse withdrawal/deposit column and return withdrawal, deposit values"""
        if not withdrawal_deposit_value or pd.isna(withdrawal_deposit_value):
            return None, None
        
        # Convert to string and clean
        value = str(withdrawal_deposit_value).strip()
        
        # Remove currency symbols and commas
        value = value.replace('$', '').replace('฿', '').replace(',', '')
        
        # Try to extract number
        amount_match = re.search(r'[\d.]+', value)
        if not amount_match:
            return None, None
        
        amount = float(amount_match.group())
        
        # Determine if withdrawal or deposit based on keywords or signs
        value_lower = value.lower()
        if 'dr' in value_lower or 'withdrawal' in value_lower or value.startswith('-'):
            return amount, None
        elif 'cr' in value_lower or 'deposit' in value_lower or value.startswith('+'):
            return None, amount
        else:
            # If no clear indicator, check if it's in a withdrawal or deposit context
            # Default to deposit if positive, withdrawal if negative
            return None, amount
    
    def clean_and_transform(self, raw_data):
        """Transform raw table data into Firefly-compatible format"""
        
        # Create DataFrame from raw data
        if not raw_data:
            raise ValueError("No data extracted from PDF")
        
        # First row might be headers
        headers = raw_data[0] if raw_data else []
        data_rows = raw_data[1:] if len(raw_data) > 1 else []
        
        # Create DataFrame
        df = pd.DataFrame(data_rows, columns=headers)
        
        # Remove completely empty rows
        df = df.dropna(how='all')
        
        # Process the data
        processed_data = []
        
        for idx, row in df.iterrows():
            # Extract date (combine Date and Time/Eff.Date if needed)
            date_val = row.get('Date', '')
            time_val = row.get('Time/Eff.Date', '')
            
            # Parse date
            date_str = str(date_val).strip() if date_val else ''
            
            # Extract description
            description = str(row.get('Descriptions', '')).strip()
            
            # Parse withdrawal/deposit
            wd_value = row.get('Withdrawal / Deposit', '')
            withdrawal, deposit = self.parse_amount(wd_value)
            
            # Get channel
            channel = str(row.get('Channel', '')).strip()
            
            # Get details
            details = str(row.get('Details', '')).strip()
            
            # Combine description with details if both exist
            full_description = f"{description} - {details}" if description and details else (description or details)
            
            # Skip rows without amounts
            if withdrawal is None and deposit is None:
                continue
            
            processed_data.append({
                'Date': date_str,
                'Description': full_description,
                'Withdrawal': withdrawal if withdrawal else '',
                'Deposit': deposit if deposit else '',
                'Category': channel,
                'Notes': f"Time/Eff.Date: {time_val}" if time_val else ''
            })
        
        # Create final DataFrame
        final_df = pd.DataFrame(processed_data)
        
        return final_df
    
    def convert(self):
        """Main conversion method"""
        print(f"Processing: {self.input_path}")
        
        # Extract tables from PDF
        raw_data = self.extract_tables_from_pdf()
        
        if not raw_data:
            raise ValueError("No tables found in PDF")
        
        print(f"Extracted {len(raw_data)} rows from PDF")
        
        # Transform data
        df = self.clean_and_transform(raw_data)
        
        print(f"Processed {len(df)} transactions")
        
        # Save to CSV
        df.to_csv(self.output_path, index=False)
        
        print(f"Saved to: {self.output_path}")
        
        return self.output_path


def main():
    if len(sys.argv) < 2:
        print("Usage: python converter.py <input_pdf> [output_csv]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    converter = BankStatementConverter(input_file, output_file)
    converter.convert()


if __name__ == "__main__":
    main()
