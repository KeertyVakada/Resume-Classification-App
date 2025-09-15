# streamlit_app.py
import streamlit as st
import pickle
import tempfile
import os
from preprocess import extract_text  # reuse same extraction logic

# Load model + vectorizer (cached)
@st.cache_resource
def load_artifacts():
    with open("rf_resume_model.pkl", "rb") as f:
        model = pickle.load(f)
    with open("tfidf_vectorizer.pkl", "rb") as f:
        vect = pickle.load(f)
    return model, vect

model, vectorizer = load_artifacts()

st.title("Resume Classification")
st.write("Upload a resume (.pdf, .docx, .doc, .txt).")

uploaded = st.file_uploader("Upload file", type=["pdf", "docx", "doc", "txt"])
if uploaded is not None:
    # save uploaded file to a temp path (win32com needs a path for .doc)
    tmpdir = tempfile.mkdtemp()
    tmp_path = os.path.join(tmpdir, uploaded.name)
    with open(tmp_path, "wb") as f:
        f.write(uploaded.getbuffer())

    # extract text using preprocess logic
    extracted = extract_text(tmp_path)

    if extracted.strip():
        st.subheader("Extracted Text (preview)")
        st.text_area("", extracted[:2000] + ("..." if len(extracted) > 2000 else ""), height=300)

        X = vectorizer.transform([extracted])
        pred = model.predict(X)[0]
        st.success(f"Predicted Job Role: **{pred}**")
    else:
        st.error("Could not extract text from the uploaded file. Try another file.")

    # cleanup temp file
    try:
        os.remove(tmp_path)
        os.rmdir(tmpdir)
    except Exception:
        pass
