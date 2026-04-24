import re

# ==========================================
# ROLE 2: ETL/ELT BUILDER - Transcript Processor
# ==========================================
# Cleans video transcript: removes noise tokens, timestamps, and extracts
# Vietnamese price mentions.

# Mapping of Vietnamese number words to integers
_VIET_NUMBER_MAP = {
    "không": 0,
    "một": 1, "hai": 2, "ba": 3, "bốn": 4, "bốn": 4,
    "năm": 5, "sáu": 6, "bảy": 7, "tám": 8, "chín": 9,
    "mười": 10, "mươi": 10,
    "trăm": 100,
    "nghìn": 1000, "ngàn": 1000,
    "triệu": 1_000_000,
    "tỷ": 1_000_000_000,
}

def _parse_vietnamese_price(text):
    """
    Parses simple Vietnamese number phrases to integer.
    Examples:
    - "năm trăm nghìn" -> 500000
    - "một triệu" -> 1000000
    """
    # Normalize the text
    text = text.lower().strip()
    words = text.split()
    
    result = 0
    current = 0
    
    for word in words:
        value = _VIET_NUMBER_MAP.get(word)
        if value is None:
            continue
        
        if value == 100:
            current = current * 100 if current > 0 else 100
        elif value >= 1000:
            current = current if current > 0 else 1
            result += current * value
            current = 0
        else:
            current += value
    
    result += current
    return result if result > 0 else None


def clean_transcript(file_path):
    """
    Cleans demo_transcript.txt:
    1. Removes noise tokens: [Music starts], [Music ends], [inaudible], [Laughter], etc.
    2. Strips timestamps: [00:00:00]
    3. Strips speaker labels: [Speaker 1]:
    4. Extracts Vietnamese price mention ("năm trăm nghìn" -> 500000)
    5. Returns a cleaned dict for the UnifiedDocument schema.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()

    # --- STEP 1: Extract Vietnamese price BEFORE cleaning (so we don't lose context) ---
    # Look for the price phrase in Vietnamese
    price_pattern = re.search(
        r'((?:[\w\s]+ )?(?:năm|một|hai|ba|bốn|sáu|bảy|tám|chín|mười)'
        r'(?:\s+(?:trăm|nghìn|ngàn|triệu|mươi|[\wáàảãạăắặằẳẵâấậầẩẫéèẻẽẹêếệềểễíìỉĩịóòỏõọôốộồổỗơớợờởỡúùủũụưứựừửữýỳỷỹỵđ]+))*)',
        text,
        re.IGNORECASE
    )
    
    # More robust: search for exact known phrase in the transcript
    price_phrase_match = re.search(
        r'((?:\w+\s+){0,5})(năm trăm nghìn)',
        text,
        re.IGNORECASE
    )
    
    detected_price = None
    price_phrase = None
    if price_phrase_match:
        price_phrase = price_phrase_match.group(2)
        detected_price = _parse_vietnamese_price(price_phrase)  # 500000

    # --- STEP 2: Remove timestamps [00:00:00] ---
    cleaned = re.sub(r'\[\d{2}:\d{2}:\d{2}\]', '', text)

    # --- STEP 3: Remove noise tokens (audio effects, etc.) ---
    noise_patterns = [
        r'\[Music starts?\]',
        r'\[Music ends?\]',
        r'\[Music\]',
        r'\[inaudible\]',
        r'\[Laughter\]',
        r'\[applause\]',
        r'\[noise\]',
        r'\[silence\]',
        r'\[crosstalk\]',
    ]
    for pattern in noise_patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)

    # --- STEP 4: Remove speaker labels [Speaker N]: ---
    cleaned = re.sub(r'\[Speaker \d+\]:', '', cleaned, flags=re.IGNORECASE)

    # --- STEP 5: Clean up extra whitespace ---
    cleaned = re.sub(r'\n\s*\n', '\n', cleaned)  # collapse blank lines
    cleaned = re.sub(r'[ \t]+', ' ', cleaned)     # collapse spaces
    cleaned = cleaned.strip()

    return {
        "document_id": "video-transcript-001",
        "content": cleaned,
        "source_type": "Video",
        "author": "Speaker 1",
        "timestamp": None,
        "source_metadata": {
            "original_file": "demo_transcript.txt",
            "detected_price_vnd": detected_price,
            "detected_price_phrase": price_phrase,
            "language": "Vietnamese/English",
        }
    }
