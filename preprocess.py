import os
import re
import fitz  # PyMuPDF
import docx2txt
import pandas as pd
import pypandoc
from typing import Optional

# ---- Helper ----
def _clean_text(s: str) -> str:
    if not s:
        return ""
    s = re.sub(r"\r\n", "\n", s)
    s = re.sub(r"\n+", "\n", s)
    s = re.sub(r"[ \t]{2,}", " ", s)
    return s.strip()

# ---- Extractors ----
def extract_text_from_pdf(file_path: str) -> str:
    text = ""
    try:
        doc = fitz.open(file_path)
        text = "".join(page.get_text() for page in doc)
    except Exception as e:
        print(f"PDF extraction failed for {file_path}: {e}")
    return _clean_text(text)

def extract_text_from_docx(file_path: str) -> str:
    try:
        text = docx2txt.process(file_path)
    except Exception as e:
        print(f"DOCX extraction failed for {file_path}: {e}")
        text = ""
    return _clean_text(text)

def extract_text_from_doc(file_path: str) -> str:
    """
    Convert legacy .doc to .docx using pypandoc, then extract text.
    """
    try:
        tmp_docx = file_path + ".converted.docx"
        pypandoc.convert_file(file_path, "docx", outputfile=tmp_docx)
        text = extract_text_from_docx(tmp_docx)
        os.remove(tmp_docx)  # cleanup
        return text
    except Exception as e:
        print(f"DOC extraction failed for {file_path}: {e}")
        return ""

def extract_text(file_path: str) -> str:
    """
    Extract text from PDF, DOCX, DOC, or TXT files
    """
    try:
        if file_path.endswith(".pdf"):
            return extract_text_from_pdf(file_path)
        elif file_path.endswith(".docx"):
            return extract_text_from_docx(file_path)
        elif file_path.endswith(".doc"):
            return extract_text_from_doc(file_path)
        elif file_path.endswith(".txt"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()
            except UnicodeDecodeError:
                with open(file_path, "r", encoding="latin-1") as f:
                    return f.read()
        else:
            return ""
    except Exception as e:
        print(f"Error extracting text from {file_path}: {e}")
        return ""

# ---- Mapping & Profile derivation ----
FOLDER_CATEGORY_MAP = {
    "peoplesoft resumes": "PeopleSoft",
    "sql developer lightning insight": "SQL Developer",
    "workday resumes": "Workday"
}

PREFIX_PROFILE_MAP = {
    "react dev": "UI Developer (React JS)",
    "react developer": "UI Developer (React JS)",
    "react js developer": "UI Developer (React JS)",
    "ui-developer/ react js developer": "UI Developer (React JS)",
    "ui developer": "UI Developer (React JS)",
    "peoplesoft admin": "PeopleSoft Administrator",
    "peoplesoft": "PeopleSoft Technical/Functional Consultant",
    "peoplesoft finance": "PeopleSoft Finance Specialist",
    "peoplesoft fscm": "PeopleSoft FSCM Consultant",
    "workday": "Workday Specialist",
    "sql developer": "Database Developer (SQL Developer)",
    "sql":  "SQL Developer",
    "internship": "Software Intern",
    "intern": "Software Intern"
}

def _match_prefix_to_profile(prefix: str) -> Optional[str]:
    p = prefix.lower().strip()
    p = re.sub(r"[^a-z0-9 ]+", " ", p)
    p = re.sub(r"\s+", " ", p).strip()
    if not p:
        return None
    if p in PREFIX_PROFILE_MAP:
        return PREFIX_PROFILE_MAP[p]
    for key, val in PREFIX_PROFILE_MAP.items():
        if key in p:
            return val
    return None

def derive_profile(file_name: str, folder_name: str, extracted_text: str) -> str:
    folder_normal = (folder_name or "").strip()
    if folder_normal:
        folder_key = folder_normal.lower()
        if folder_key in FOLDER_CATEGORY_MAP:
            cat = FOLDER_CATEGORY_MAP[folder_key]
            fname = file_name.lower()
            t = extracted_text.lower() if extracted_text else ""
            if cat == "PeopleSoft":
                if "admin" in fname or "admin" in t:
                    return "PeopleSoft Administrator"
                if "fscm" in fname or "fscm" in t:
                    return "PeopleSoft FSCM Consultant"
                if "finance" in fname or "finance" in t:
                    return "PeopleSoft Finance Specialist"
                if "bda" in fname or "business data" in t:
                    return "PeopleSoft Business Data Analyst"
                return "PeopleSoft Technical/Functional Consultant"
            elif cat == "Workday":
                return "Workday Specialist"
            elif cat == "SQL Developer":
                return "Database Developer (SQL Developer)"
            else:
                return cat
        if folder_key not in ("resumes", "resume", ".", ""):
            return folder_normal

    name_root = os.path.splitext(file_name)[0]
    prefix = name_root.split("_")[0] if "_" in name_root else name_root.split("-")[0]
    maybe = _match_prefix_to_profile(prefix)
    if maybe:
        return maybe

    t = (extracted_text or "").lower()
    if "react" in t and any(k in t for k in ("ui", "frontend", "front end", "javascript")):
        return "UI Developer (React JS)"
    if "peoplesoft" in t:
        if "admin" in t:
            return "PeopleSoft Administrator"
        if "fscm" in t:
            return "PeopleSoft FSCM Consultant"
        if "finance" in t or "general ledger" in t:
            return "PeopleSoft Finance Specialist"
        return "PeopleSoft Technical/Functional Consultant"
    if "workday" in t or "hcm" in t:
        return "Workday Specialist"
    if any(k in t for k in ("sql", "pl/sql", "oracle", "mysql", "postgresql", "database")):
        return "Database Developer (SQL Developer)"
    if any(k in t for k in ("intern", "internship")):
        return "Software Intern"

    return "Other"

# ---- Main preprocess function ----
def preprocess_data(main_path: str) -> pd.DataFrame:
    rows = []
    for root, _, files in os.walk(main_path):
        for fname in files:
            path = os.path.join(root, fname)
            ext = os.path.splitext(fname)[1].lower()
            text = extract_text(path)
            folder_basename = os.path.basename(root) or ""
            rows.append({
                "Folder": folder_basename,
                "File": fname,
                "Type": ext,
                "Path": path,
                "Text": text
            })

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df["Category"] = df["Folder"].apply(lambda x: FOLDER_CATEGORY_MAP.get(x.lower(), "React JS Developer"))
    df["Profile"] = df.apply(lambda r: derive_profile(r["File"], r["Folder"], r["Text"]), axis=1)
    return df
