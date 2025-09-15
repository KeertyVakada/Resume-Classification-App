import pickle

# Load model + vectorizer
with open("rf_resume_model.pkl", "rb") as f:
    model = pickle.load(f)

with open("tfidf_vectorizer.pkl", "rb") as f:
    vectorizer = pickle.load(f)

def predict_resume(text: str) -> str:
    X_new = vectorizer.transform([text])
    return model.predict(X_new)[0]

if __name__ == "__main__":
    sample_resume = """
    Experienced SQL Developer with strong knowledge in databases,
    queries, and performance tuning. Worked on multiple ERP integrations.
    """
    print("Predicted Job Role:", predict_resume(sample_resume))
