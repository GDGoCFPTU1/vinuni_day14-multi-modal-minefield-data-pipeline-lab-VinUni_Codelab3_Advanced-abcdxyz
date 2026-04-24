import ast
import re

# ==========================================
# ROLE 2: ETL/ELT BUILDER - Legacy Code Processor
# ==========================================
# Extracts docstrings and business rules from legacy Python code using the ast module.
# Also detects discrepancies (e.g., misleading comments vs. actual code values).

def _detect_tax_discrepancy(source_code):
    """
    Checks if any function has a comment claiming one tax rate
    but implements a different rate in code.
    Returns a discrepancy notice string or None.
    """
    # Look for the misleading comment pattern
    comment_rate_match = re.search(
        r'#.*?(\d+(?:\.\d+)?)\s*%',
        source_code
    )
    # Look for actual tax_rate assignment
    code_rate_match = re.search(
        r'tax_rate\s*=\s*(\d+(?:\.\d+)?)',
        source_code
    )
    
    if comment_rate_match and code_rate_match:
        comment_rate = float(comment_rate_match.group(1))
        code_rate = float(code_rate_match.group(1)) * 100  # e.g. 0.10 -> 10
        if abs(comment_rate - code_rate) > 0.01:
            return (
                f"DISCREPANCY DETECTED in legacy_tax_calc: "
                f"Comment claims {comment_rate}% but code implements {code_rate}%."
            )
    return None


def extract_logic_from_code(file_path):
    """
    Parses legacy_pipeline.py using the AST module to extract:
    1. Module-level docstring (global business rules / warnings).
    2. Per-function docstrings (Business Logic Rules).
    3. Business rule comments (# Business Logic Rule NNN).
    4. Flags the tax rate discrepancy between comment and code.
    
    Returns a dict formatted for the UnifiedDocument schema.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        source_code = f.read()

    tree = ast.parse(source_code)

    extracted_rules = []

    # --- Module-level docstring ---
    module_docstring = ast.get_docstring(tree)
    if module_docstring:
        extracted_rules.append(f"[MODULE DOC]: {module_docstring.strip()}")

    # --- Function-level docstrings ---
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_doc = ast.get_docstring(node)
            if func_doc:
                extracted_rules.append(
                    f"[FUNCTION: {node.name}]: {func_doc.strip()}"
                )

    # --- Business rule comments (regex over raw source) ---
    business_rule_comments = re.findall(
        r'#\s*(Business Logic Rule \d+[^\n]*)',
        source_code
    )
    for comment in business_rule_comments:
        rule_str = f"[BUSINESS RULE COMMENT]: {comment.strip()}"
        if rule_str not in extracted_rules:
            extracted_rules.append(rule_str)

    # --- Tax discrepancy detection ---
    discrepancy = _detect_tax_discrepancy(source_code)
    discrepancy_flag = discrepancy is not None

    content = "\n\n".join(extracted_rules)
    if discrepancy:
        content += f"\n\n[QA FLAG]: {discrepancy}"

    return {
        "document_id": "code-legacy-pipeline-001",
        "content": content,
        "source_type": "Code",
        "author": "Senior Dev (retired)",
        "timestamp": None,
        "source_metadata": {
            "original_file": "legacy_pipeline.py",
            "functions_extracted": [
                node.name
                for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            ],
            "business_rules_found": len([r for r in extracted_rules if "FUNCTION" in r or "RULE" in r]),
            "tax_discrepancy_detected": discrepancy_flag,
            "discrepancy_detail": discrepancy,
        }
    }
