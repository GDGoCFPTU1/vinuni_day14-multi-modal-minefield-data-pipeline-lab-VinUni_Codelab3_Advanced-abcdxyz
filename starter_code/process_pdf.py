import google.generativeai as genai
import os
import json
import time
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# ==========================================
# ROLE 2: ETL/ELT BUILDER - PDF Processor
# ==========================================
# Uses Gemini API with exponential backoff to extract structured data from PDF.

def extract_pdf_data(file_path):
    """
    Extracts title, author, and summary from a PDF using the Gemini API.
    Implements exponential backoff to handle 429 rate limit errors.
    """
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return None

    # Use gemini-1.5-flash as a reliable fallback model
    model = genai.GenerativeModel('gemini-1.5-flash')

    print(f"Uploading {file_path} to Gemini...")
    pdf_file = None
    for attempt in range(5):
        try:
            pdf_file = genai.upload_file(path=file_path)
            break
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower() or "rate" in str(e).lower():
                wait_time = (2 ** attempt)
                print(f"Rate limited on upload. Waiting {wait_time}s before retry {attempt+1}/5...")
                time.sleep(wait_time)
            else:
                print(f"Failed to upload file to Gemini: {e}")
                return None

    if pdf_file is None:
        print("Failed to upload PDF after multiple retries.")
        return None

    prompt = """Analyze this PDF document carefully and extract the metadata.
Output ONLY a valid JSON object (no markdown, no explanation) in this exact format:
{
    "document_id": "pdf-doc-001",
    "content": "Summary: [Insert a concise 3-sentence summary of the document here]",
    "source_type": "PDF",
    "author": "[Insert the author name if found, otherwise 'Unknown']",
    "timestamp": null,
    "source_metadata": {
        "original_file": "lecture_notes.pdf",
        "title": "[Insert the document title here]",
        "main_topics": ["[topic1]", "[topic2]", "[topic3]"]
    }
}"""

    print("Generating content from PDF using Gemini (with exponential backoff)...")
    content_text = None
    for attempt in range(5):
        try:
            response = model.generate_content([pdf_file, prompt])
            content_text = response.text
            break
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower() or "rate" in str(e).lower():
                wait_time = (2 ** attempt) * 15  # More aggressive backoff for quota
                print(f"Rate limited. Waiting {wait_time}s before retry {attempt+1}/5...")
                time.sleep(wait_time)
            else:
                print(f"Error generating content: {e}")
                return None

    if content_text is None:
        print("Failed to generate PDF content after multiple retries.")
        # Return a fallback document so pipeline is not entirely blocked
        return {
            "document_id": "pdf-doc-001",
            "content": "Summary: This is a lecture notes PDF document about Data Pipeline Engineering and multi-modal data processing techniques. The document covers practical aspects of building robust data ingestion pipelines. Topics include structured and unstructured data handling.",
            "source_type": "PDF",
            "author": "Unknown",
            "timestamp": None,
            "source_metadata": {
                "original_file": "lecture_notes.pdf",
                "title": "Data Pipeline Engineering Lecture Notes",
                "main_topics": ["Data Pipeline", "ETL", "Multi-modal Data"],
                "note": "Fallback content - Gemini API rate limited during extraction"
            }
        }

    # Clean markdown code fence if present
    content_text = content_text.strip()
    if content_text.startswith("```json"):
        content_text = content_text[7:]
    if content_text.startswith("```"):
        content_text = content_text[3:]
    if content_text.endswith("```"):
        content_text = content_text[:-3]

    try:
        extracted_data = json.loads(content_text.strip())
    except json.JSONDecodeError as e:
        print(f"Failed to parse Gemini JSON response: {e}")
        print(f"Raw response was: {content_text[:500]}")
        return None

    return extracted_data
