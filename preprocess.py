# preprocess.py
import os
import re
import fitz  # PyMuPDF
import docx2txt
import pandas as pd
from typing import List, Tuple, Optional

# ---- Helper utilities ----
def _clean_text(s: str) -> str:
    if not s:
        return ""
    s = re.sub(r"\r\n", "\n", s)
    s = re.sub(r"\n+", "\n", s)
    s = re.sub(r"[ \t]{2,}", " ", s)
    return s.strip()

# ---- Extractors ----
def extract_text_from_pdf(path: str) -> str:
    text = ""
    try:
        doc = fitz.open(path)
        pages = []
        for p in doc:
            try:
                pages.append(p.get_text("text") or "")
            except Exception:
                pages.append("")
        text = " ".join(pages)
    except Exception as e:
        print(f"PDF extraction failed for {path}: {e}")
    return _clean_text(text)

def extract_text_from_docx(path: str) -> str:
    try:
        text = docx2txt.process(path) or ""
    except Exception as e:
        print(f"DOCX extraction failed for {path}: {e}")
        text = ""
    return _clean_text(text)

def extract_text_from_doc(path: str) -> str:
    """
    Extract text from legacy .doc using Word COM.
    This initializes COM in the current thread and uninitializes afterwards.
    """
    text = ""
    try:
        pythoncom.CoInitialize()
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        doc = word.Documents.Open(path)
        text = doc.Content.Text or ""
        doc.Close(False)
        word.Quit()
    except Exception as e:
        print(f"DOC extraction failed for {path}: {e}")
        text = ""
    finally:
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass
    return _clean_text(text)

# preprocess.py
import docx2txt
import fitz  # PyMuPDF

def extract_text(file_path):
    if file_path.endswith(".pdf"):
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    elif file_path.endswith(".docx"):
        text = docx2txt.process(file_path)
        return text
    else:
        # txt or other formats
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()


# ---- Mapping & Profile derivation ----
FOLDER_CATEGORY_MAP = {
    "peoplesoft resumes": "PeopleSoft",
    "sql developer lightning insight": "SQL Developer",
    "workday resumes": "Workday"
}

PREFIX_PROFILE_MAP = {
    # common filename prefixes -> normalized profile
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
    "sql developer": "Database / SQL Developer",
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
    # try exact keys, then substring match
    if p in PREFIX_PROFILE_MAP:
        return PREFIX_PROFILE_MAP[p]
    for key, val in PREFIX_PROFILE_MAP.items():
        if key in p:
            return val
    return None

def derive_profile(file_name: str, folder_name: str, extracted_text: str) -> str:
    """
    Determine the detailed profile (job role) using:
     1) folder name if it is a specific role folder,
     2) filename prefix (before underscore or hyphen),
     3) simple keyword checks inside the resume text.
    """
    # 1) folder-based
    folder_normal = (folder_name or "").strip()
    if folder_normal:
        folder_key = folder_normal.lower()
        # if folder is mapped to a known category, prefer that mapping
        if folder_key in FOLDER_CATEGORY_MAP:
            cat = FOLDER_CATEGORY_MAP[folder_key]
            # map category to a sensible profile
            if cat == "PeopleSoft":
                # further inspection on filename/text to specify admin/fscm/finance...
                fname = file_name.lower()
                if "admin" in fname or "admin" in extracted_text.lower():
                    return "PeopleSoft Administrator"
                if "fscm" in fname or "fscm" in extracted_text.lower():
                    return "PeopleSoft FSCM Consultant"
                if "finance" in fname or "finance" in extracted_text.lower():
                    return "PeopleSoft Finance Specialist"
                if "bda" in fname or "business data" in extracted_text.lower():
                    return "PeopleSoft Business Data Analyst"
                return "PeopleSoft Technical/Functional Consultant"
            elif cat == "Workday":
                return "Workday Specialist"
            elif cat == "SQL Developer":
                return "Database Developer / SQL Developer"
            else:
                # if folder maps to other string, use it
                return cat

        # If folder name itself looks like a role (not generic "Resumes"), use it
        if folder_key and folder_key not in ("resumes", "resume", ".", ""):
            # normalize common patterns: remove extension-like bits
            return folder_normal

    # 2) filename prefix (e.g., "React Dev_Krishna...")
    name_root = os.path.splitext(file_name)[0]
    prefix = name_root.split("_")[0] if "_" in name_root else name_root.split("-")[0]
    maybe = _match_prefix_to_profile(prefix)
    if maybe:
        return maybe

    # 3) keyword-based from text (fallback)
    t = (extracted_text or "").lower()
    if "react" in t and ("ui" in t or "frontend" in t or "front end" in t or "javascript" in t):
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
        return "Database Developer / SQL Developer"
    if any(k in t for k in ("intern", "internship")):
        return "Software Intern"

    # Final fallback
    return "Other"

# ---- Main preprocess function ----
def preprocess_data(main_path: str) -> pd.DataFrame:
    """
    Walks `main_path` recursively, extracts text from known resume files,
    and returns a DataFrame with columns: Folder, File, Type, Path, Text, Category, Profile
    """
    rows = []
    for root, _, files in os.walk(main_path):
        for fname in files:
            path = os.path.join(root, fname)
            ext = os.path.splitext(fname)[1].lower()
            # Extract text (safe; extract_text handles exceptions)
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

    # Category mapping (main category)
    df["Category"] = df["Folder"].apply(lambda x: FOLDER_CATEGORY_MAP.get(x.lower(), "React JS Developer"))

    # Profile (detailed job role)
    df["Profile"] = df.apply(lambda r: derive_profile(r["File"], r["Folder"], r["Text"]), axis=1)

    return df
