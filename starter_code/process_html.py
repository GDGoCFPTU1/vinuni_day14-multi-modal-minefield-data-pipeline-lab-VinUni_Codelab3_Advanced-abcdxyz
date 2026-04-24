from bs4 import BeautifulSoup
import re

# ==========================================
# ROLE 2: ETL/ELT BUILDER - HTML Processor
# ==========================================
# Extracts product data from the main-catalog table, ignores nav/footer boilerplate.

def _clean_price_html(price_str):
    """
    Cleans price strings from HTML:
    - "28,500,000 VND" -> 28500000.0
    - "N/A" or "Liên hệ" -> None
    - Negative stock -> flag in metadata
    """
    if not price_str or price_str.strip() in ("N/A", "Liên hệ", ""):
        return None
    # Remove currency labels and commas
    cleaned = re.sub(r'[^\d.]', '', price_str.replace(",", ""))
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_html_catalog(file_path):
    """
    Parses product_catalog.html:
    1. Uses BeautifulSoup to find the table with id='main-catalog'.
    2. Extracts all product rows, handling N/A and 'Liên hệ' in price.
    3. Returns a list of dicts for the UnifiedDocument schema.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    # Target only the main catalog table — ignore nav, ads, footer
    table = soup.find('table', id='main-catalog')
    if not table:
        print("Warning: Could not find table with id='main-catalog'")
        return []

    results = []
    rows = table.find('tbody').find_all('tr')

    for i, row in enumerate(rows):
        cells = [td.get_text(strip=True) for td in row.find_all('td')]
        if len(cells) < 6:
            continue  # Skip malformed rows

        product_id, product_name, category, price_raw, stock_raw, rating = cells[:6]

        price = _clean_price_html(price_raw)
        price_note = None if price is not None else price_raw.strip()

        # Parse stock (may be negative — flag as anomaly)
        try:
            stock = int(stock_raw)
        except ValueError:
            stock = None

        content = (
            f"Product: {product_name} | Category: {category} | "
            f"Price: {price_raw} | Stock: {stock_raw} | Rating: {rating}"
        )

        doc_dict = {
            "document_id": f"html-product-{product_id}",
            "content": content,
            "source_type": "HTML",
            "author": "VinShop",
            "timestamp": None,
            "source_metadata": {
                "original_file": "product_catalog.html",
                "product_id": product_id,
                "product_name": product_name,
                "category": category,
                "price_vnd": price,
                "price_note": price_note,
                "stock_quantity": stock,
                "stock_anomaly": stock is not None and stock < 0,
                "rating": rating,
            }
        }
        results.append(doc_dict)

    return results
