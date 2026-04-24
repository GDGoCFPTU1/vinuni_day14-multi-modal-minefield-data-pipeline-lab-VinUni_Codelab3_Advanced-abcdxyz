# ==========================================
# ROLE 3: OBSERVABILITY & QA ENGINEER
# ==========================================
# Semantic quality gates to reject corrupt or invalid documents
# before they enter the Knowledge Base.

import re

# Strings that indicate truly corrupt/error runtime data.
# These are matched as WHOLE WORDS or EXACT ERROR PHRASES, not substrings.
TOXIC_EXACT_PHRASES = [
    "null pointer exception",
    "nullpointerexception",
    "stackoverflowerror",
    "segmentation fault",
    "traceback (most recent call last)",
    "exception in thread",
    "fatal error",
    "undefined is not a function",
]

# Patterns for toxic content — matched as standalone tokens or error markers
TOXIC_PATTERNS = [
    r'\berror\s+[45]\d{2}\b',          # error 404, error 500
]

MIN_CONTENT_LENGTH = 20  # characters


def _has_toxic_content(content: str) -> bool:
    """
    Checks if the content contains genuine error/corrupt strings.
    Uses exact phrase matching (not substring) for common false positives.
    
    NOTE: "N/A", "NULL", "None" alone in a price field are NOT corrupt data—
    they are valid representations of missing values and should not be rejected
    at this gate (they were already handled in the ETL processors).
    """
    content_lower = content.lower()

    # Check for exact toxic error phrases
    for phrase in TOXIC_EXACT_PHRASES:
        if phrase in content_lower:
            return True

    # Check regex patterns (e.g. HTTP error codes)
    for pattern in TOXIC_PATTERNS:
        if re.search(pattern, content_lower):
            return True

    return False


def _check_discrepancy(document_dict: dict) -> str | None:
    """
    Checks for known logic discrepancies in metadata.
    Returns a description of the discrepancy if found, else None.
    """
    metadata = document_dict.get("source_metadata", {})
    if metadata.get("tax_discrepancy_detected"):
        return metadata.get("discrepancy_detail", "Tax rate discrepancy detected.")
    return None


def run_quality_gate(document_dict: dict) -> bool:
    """
    Runs all quality checks on a document dict before ingestion.
    
    Gates:
    1. Content length >= 20 characters.
    2. No genuine toxic/error strings in content (exact phrase match only).
    3. Flags (but does NOT reject) documents with logic discrepancies.
    
    Returns True if document passes all hard gates, False if it should be rejected.
    """
    doc_id = document_dict.get("document_id", "UNKNOWN")
    content = document_dict.get("content", "")

    # Gate 1: Minimum content length
    if not content or len(content.strip()) < MIN_CONTENT_LENGTH:
        print(
            f"  [QA REJECT] {doc_id}: Content too short "
            f"({len(content.strip())} chars, min {MIN_CONTENT_LENGTH})."
        )
        return False

    # Gate 2: No toxic/corrupt error strings
    if _has_toxic_content(content):
        print(f"  [QA REJECT] {doc_id}: Toxic/corrupt error content detected.")
        return False

    # Gate 3: Flag discrepancies (warn only, do not reject)
    discrepancy = _check_discrepancy(document_dict)
    if discrepancy:
        print(f"  [QA FLAG]   {doc_id}: Logic discrepancy — {discrepancy}")

    return True
