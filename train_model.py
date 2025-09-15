# train_model.py
import os
import pickle
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from preprocess import preprocess_data

MAIN_PATH = r"C:\Users\dolly\OneDrive\Desktop\Resume Classification Project\Resumes\Resumes"

def main():
    print("Preprocessing resumes (this may take a while)...")
    df = preprocess_data(MAIN_PATH)
    print(f"Files found: {len(df)}")

    # Drop rows with empty text
    df = df[df["Text"].str.strip().astype(bool)].reset_index(drop=True)
    print(f"Files with extracted text: {len(df)}")

    # Use Profile as the target label (detailed role)
    X_texts = df["Text"].astype(str).values
    y = df["Profile"].astype(str).values

    print("Vectorizing...")
    vectorizer = TfidfVectorizer(stop_words="english", max_features=7000)
    X = vectorizer.fit_transform(X_texts)

    print("Splitting data...")

    # stratify only if all classes have at least 2 samples
    class_counts = pd.Series(y).value_counts()
    if class_counts.min() >= 2 and len(class_counts) > 1:
        stratify_opt = y
    else:
        stratify_opt = None
        print("Some classes have <2 samples → disabling stratify.")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=stratify_opt
    )

    print("Training RandomForest...")
    model = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)
    print("Training completed.")

    # Evaluate
    y_pred = model.predict(X_test)
    print("Accuracy:", accuracy_score(y_test, y_pred))
    print("Classification report:\n", classification_report(y_test, y_pred, zero_division=0))

    # Save artifacts
    with open("rf_resume_model.pkl", "wb") as f:
        pickle.dump(model, f)
    with open("tfidf_vectorizer.pkl", "wb") as f:
        pickle.dump(vectorizer, f)

    print("Saved rf_resume_model.pkl and tfidf_vectorizer.pkl")

if __name__ == "__main__":
    main()
