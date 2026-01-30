import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, accuracy_score
import joblib
from pathlib import Path

# ===============================
# XÁC ĐỊNH ĐƯỜNG DẪN AN TOÀN
# ===============================
BASE_DIR = Path(__file__).resolve().parent

DATA_PATH = BASE_DIR / "nextact_todo_dataset_2000_diverse_vi.csv"
MODEL_PATH = BASE_DIR / "nextact_model.joblib"

# ===============================
# LOAD DATASET
# ===============================
df = pd.read_csv(DATA_PATH)

X = df["text"].astype(str)
y = df["labels"].astype(str)

# ===============================
# TRAIN / TEST SPLIT
# ===============================
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

# ===============================
# BUILD MODEL
# ===============================
model = Pipeline([
    ("tfidf", TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=2
    )),
    ("clf", LogisticRegression(
        max_iter=2000,
        n_jobs=1
    ))
])

# ===============================
# TRAIN
# ===============================
model.fit(X_train, y_train)

# ===============================
# EVALUATE
# ===============================
pred = model.predict(X_test)
acc = accuracy_score(y_test, pred)

print("Accuracy:", acc)
print(classification_report(y_test, pred))

# ===============================
# SAVE MODEL (TỰ TẠO FILE)
# ===============================
joblib.dump(model, MODEL_PATH)

print("✅ Model đã được lưu tại:", MODEL_PATH)
