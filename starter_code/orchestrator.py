import json
import time
import os
import sys

# Robust path handling: allows running from any directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
RAW_DATA_DIR = os.path.join(ROOT_DIR, "raw_data")

# Ensure the starter_code module can be imported when running from root
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

# Import role-specific modules
from schema import UnifiedDocument
from process_pdf import extract_pdf_data
from process_transcript import clean_transcript
from process_html import parse_html_catalog
from process_csv import process_sales_csv
from process_legacy_code import extract_logic_from_code
from quality_check import run_quality_gate

# ==========================================
# ROLE 4: DEVOPS & INTEGRATION SPECIALIST
# ==========================================
# Orchestrates the full ingestion DAG and saves the final Knowledge Base JSON.

def _safe_ingest_single(doc_dict, final_kb, source_label):
    """
    Runs the quality gate and appends a single doc_dict to final_kb if it passes.
    Handles None inputs gracefully.
    """
    if doc_dict is None:
        print(f"  [SKIP] {source_label}: Processor returned None.")
        return
    
    # Validate and coerce via Pydantic schema (catches missing fields early)
    try:
        validated = UnifiedDocument(**doc_dict)
        # Convert back to dict for JSON serialization (use model_dump for Pydantic v2)
        try:
            doc_out = validated.model_dump()
        except AttributeError:
            doc_out = validated.dict()  # Pydantic v1 fallback
        
        # Serialize datetime objects to string for JSON
        for key, val in doc_out.items():
            if hasattr(val, 'isoformat'):
                doc_out[key] = val.isoformat()
    except Exception as e:
        print(f"  [SCHEMA ERROR] {source_label}: {e}. Using raw dict.")
        doc_out = doc_dict
    
    # Run quality gate
    if run_quality_gate(doc_out):
        final_kb.append(doc_out)
        print(f"  [OK] {source_label}: document_id='{doc_out.get('document_id')}' added.")
    else:
        print(f"  [REJECTED] {source_label}: Failed quality gate.")


def _safe_ingest_list(doc_list, final_kb, source_label):
    """
    Ingest a list of document dicts (e.g., from CSV or HTML processors).
    """
    if not doc_list:
        print(f"  [SKIP] {source_label}: Processor returned empty list.")
        return
    
    passed = 0
    rejected = 0
    for doc_dict in doc_list:
        _safe_ingest_single(doc_dict, final_kb, source_label)
        # Track counts
        if final_kb and final_kb[-1].get('document_id') == doc_dict.get('document_id'):
            passed += 1
        else:
            rejected += 1
    
    print(f"  [SUMMARY] {source_label}: {passed} passed, {rejected} rejected.")


def main():
    """
    Main DAG orchestrator. Runs each processor, applies quality gates,
    and saves the final Knowledge Base to processed_knowledge_base.json.
    Tracks total SLA time.
    """
    start_time = time.time()
    final_kb = []

    # --- File paths (robust, no hardcoding) ---
    pdf_path   = os.path.join(RAW_DATA_DIR, "lecture_notes.pdf")
    trans_path = os.path.join(RAW_DATA_DIR, "demo_transcript.txt")
    html_path  = os.path.join(RAW_DATA_DIR, "product_catalog.html")
    csv_path   = os.path.join(RAW_DATA_DIR, "sales_records.csv")
    code_path  = os.path.join(RAW_DATA_DIR, "legacy_pipeline.py")
    output_path = os.path.join(ROOT_DIR, "processed_knowledge_base.json")

    # ---- STAGE 1: PDF (Gemini API) ----
    print("\n[STAGE 1/5] Processing PDF (Gemini API)...")
    pdf_doc = extract_pdf_data(pdf_path)
    _safe_ingest_single(pdf_doc, final_kb, "PDF")

    # ---- STAGE 2: Video Transcript ----
    print("\n[STAGE 2/5] Processing Video Transcript...")
    transcript_doc = clean_transcript(trans_path)
    _safe_ingest_single(transcript_doc, final_kb, "Transcript")

    # ---- STAGE 3: HTML Product Catalog ----
    print("\n[STAGE 3/5] Processing HTML Product Catalog...")
    html_docs = parse_html_catalog(html_path)
    _safe_ingest_list(html_docs, final_kb, "HTML")

    # ---- STAGE 4: CSV Sales Records ----
    print("\n[STAGE 4/5] Processing CSV Sales Records...")
    csv_docs = process_sales_csv(csv_path)
    _safe_ingest_list(csv_docs, final_kb, "CSV")

    # ---- STAGE 5: Legacy Code ----
    print("\n[STAGE 5/5] Processing Legacy Python Code...")
    code_doc = extract_logic_from_code(code_path)
    _safe_ingest_single(code_doc, final_kb, "LegacyCode")

    # ---- SAVE OUTPUT ----
    print(f"\n[OUTPUT] Saving Knowledge Base to: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(final_kb, f, ensure_ascii=False, indent=2, default=str)
    print(f"[OUTPUT] File saved successfully.")

    end_time = time.time()
    elapsed = end_time - start_time
    print(f"\n{'='*50}")
    print(f"Pipeline finished in {elapsed:.2f} seconds.")
    print(f"Total valid documents stored: {len(final_kb)}")
    
    # SLA check: warn if over 5 minutes
    if elapsed > 300:
        print(f"[SLA WARNING] Pipeline took {elapsed:.0f}s, exceeding 300s SLA!")
    else:
        print(f"[SLA OK] Pipeline completed within SLA.")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
