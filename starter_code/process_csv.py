import pandas as pd
import re
from datetime import datetime

# ==========================================
# ROLE 2: ETL/ELT BUILDER - CSV Processor
# ==========================================
# Handles: duplicate IDs, messy price formats, mixed date formats.

def _clean_price(value):
    """
    Converts various price formats to a float.
    - "$1200" -> 1200.0
    - "250000" -> 250000.0
    - "five dollars" -> None (unparseable text)
    - "Liên hệ" -> None (contact price)
    - "N/A", "NULL" -> None
    - Negative values -> None (invalid)
    """
    if pd.isna(value):
        return None
    
    val_str = str(value).strip()
    
    # Check for unparseable text strings
    if val_str.upper() in ("N/A", "NULL", "LIÊN HỆ", "LIEN HE", ""):
        return None
    
    # Remove currency symbols and commas
    val_str = val_str.replace("$", "").replace(",", "").strip()
    
    # Try to parse as float directly
    try:
        price = float(val_str)
        # Reject negative prices
        if price < 0:
            return None
        return price
    except ValueError:
        # Unparseable string (e.g., "five dollars")
        return None


def _normalize_date(value):
    """
    Normalizes various date formats to YYYY-MM-DD string.
    Handles: 2026-01-15, 15/01/2026, January 16th 2026, 17-01-2026, 
             2026/01/19, 19 Jan 2026, January 22nd 2026
    """
    if pd.isna(value):
        return None
    
    val_str = str(value).strip()
    
    # Remove ordinal suffixes (1st, 2nd, 3rd, 4th, etc.)
    val_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', val_str)
    
    date_formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%B %d %Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
        "%d %b %Y",
        "%b %d %Y",
    ]
    
    for fmt in date_formats:
        try:
            return datetime.strptime(val_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    
    # Last resort: try pandas
    try:
        return pd.to_datetime(val_str).strftime("%Y-%m-%d")
    except Exception:
        return None


def process_sales_csv(file_path):
    """
    Processes sales_records.csv:
    1. Removes duplicate rows based on 'id'.
    2. Cleans 'price' column (handles $, text, negative, N/A).
    3. Normalizes 'date_of_sale' to YYYY-MM-DD.
    4. Returns a list of dicts formatted for UnifiedDocument schema.
    """
    df = pd.read_csv(file_path)
    
    # Step 1: Remove duplicates based on 'id' (keep first occurrence)
    df = df.drop_duplicates(subset=['id'], keep='first')
    
    # Step 2: Clean the price column
    df['price_cleaned'] = df['price'].apply(_clean_price)
    
    # Step 3: Normalize date column
    df['date_normalized'] = df['date_of_sale'].apply(_normalize_date)
    
    results = []
    for _, row in df.iterrows():
        doc_id = f"csv-record-{int(row['id'])}"
        
        product_name = str(row.get('product_name', 'Unknown Product'))
        category = str(row.get('category', 'Unknown'))
        price = row['price_cleaned']
        currency = str(row.get('currency', 'VND'))
        date_str = row['date_normalized']
        seller_id = str(row.get('seller_id', 'Unknown'))
        stock = row.get('stock_quantity', None)
        
        # Build content string
        price_str = f"{price} {currency}" if price is not None else "Price: Contact/N/A"
        content = (
            f"Product: {product_name} | Category: {category} | "
            f"Price: {price_str} | Date of Sale: {date_str} | "
            f"Seller: {seller_id}"
        )
        
        doc_dict = {
            "document_id": doc_id,
            "content": content,
            "source_type": "CSV",
            "author": seller_id,
            "timestamp": date_str,
            "source_metadata": {
                "original_file": "sales_records.csv",
                "product_name": product_name,
                "category": category,
                "price": price,
                "currency": currency,
                "date_of_sale": date_str,
                "seller_id": seller_id,
                "stock_quantity": None if pd.isna(stock) else int(stock),
            }
        }
        results.append(doc_dict)
    
    return results
