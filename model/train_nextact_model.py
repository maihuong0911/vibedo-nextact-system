import pandas as pd
import torch
import numpy as np
import os
import pickle
from transformers import AutoTokenizer, AutoModelForSequenceClassification, TrainingArguments, Trainer
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import f1_score, classification_report
from underthesea import word_tokenize
from datasets import Dataset

current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, 'dataset_next.csv')

print("Đang load dataset...")
df = pd.read_csv(file_path, encoding='utf-8', sep=';', on_bad_lines='skip')

# Chuẩn hóa tên cột (vì Excel export ra Text và Label)
df = df.rename(columns={'Text': 'text', 'Label': 'label'})
print("Các cột sau khi rename:", df.columns.tolist())

print(f"Đã load {len(df)} mẫu.")
print("\n3 dòng đầu tiên:\n", df.head(3))

# ====================== TIỀN XỬ LÝ ======================
def preprocess_text(text):
    if pd.isna(text) or not isinstance(text, str):
        return ""
    return word_tokenize(text, format="text")

print("\nĐang tách từ tiếng Việt...")
df['text'] = df['text'].apply(preprocess_text)

# Mã hóa nhãn
le = LabelEncoder()
df['label_id'] = le.fit_transform(df['label'])
num_labels = len(le.classes_)

print("\nCác nhãn:", le.classes_.tolist())

# Chia dataset
train_df, temp_df = train_test_split(df, test_size=0.2, random_state=42, stratify=df['label_id'])
val_df, test_df = train_test_split(temp_df, test_size=0.5, random_state=42, stratify=temp_df['label_id'])

print(f"\nTrain: {len(train_df)} | Val: {len(val_df)} | Test: {len(test_df)}")

# Lưu lại
train_df.to_csv(os.path.join(current_dir, 'train.csv'), index=False, encoding='utf-8')
val_df.to_csv(os.path.join(current_dir, 'val.csv'), index=False, encoding='utf-8')
test_df.to_csv(os.path.join(current_dir, 'test.csv'), index=False, encoding='utf-8')

# ====================== TRAINING ======================
model_name = "vinai/phobert-base-v2"
tokenizer = AutoTokenizer.from_pretrained(model_name)

def tokenize_func(examples):
    return tokenizer(examples['text'], padding="max_length", truncation=True, max_length=256)

train_dataset = Dataset.from_pandas(train_df[['text', 'label_id']])
val_dataset = Dataset.from_pandas(val_df[['text', 'label_id']])
test_dataset = Dataset.from_pandas(test_df[['text', 'label_id']])

train_dataset = train_dataset.map(tokenize_func, batched=True)
val_dataset = val_dataset.map(tokenize_func, batched=True)
test_dataset = test_dataset.map(tokenize_func, batched=True)

train_dataset = train_dataset.rename_column("label_id", "labels")
val_dataset = val_dataset.rename_column("label_id", "labels")
test_dataset = test_dataset.rename_column("label_id", "labels")

model = AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=num_labels)

def compute_metrics(eval_pred):
    predictions, labels = eval_pred
    preds = np.argmax(predictions, axis=1)
    return {
        'f1_macro': round(f1_score(labels, preds, average='macro'), 4),
        'accuracy': round((preds == labels).mean(), 4)
    }

training_args = TrainingArguments(
    output_dir=os.path.join(current_dir, 'results'),
    num_train_epochs=4,
    per_device_train_batch_size=6,
    per_device_eval_batch_size=8,
    gradient_accumulation_steps=2,
    warmup_steps=300,
    weight_decay=0.01,
    logging_steps=50,
    evaluation_strategy="epoch",
    save_strategy="epoch",
    load_best_model_at_end=True,
    metric_for_best_model="f1_macro",
    report_to="none",
    fp16=False,
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
    compute_metrics=compute_metrics,
)

print("\n🚀 Bắt đầu huấn luyện PhoBERT...")
trainer.train()

# Đánh giá
print("\n=== ĐÁNH GIÁ TRÊN TEST SET ===")
test_results = trainer.evaluate(test_dataset)
print(test_results)

predictions_output = trainer.predict(test_dataset)
preds = np.argmax(predictions_output.predictions, axis=1)
print("\nClassification Report trên Test Set:")
print(classification_report(test_df['label_id'], preds, target_names=le.classes_, digits=4))

# Lưu model
save_path = os.path.join(current_dir, 'final_model')
os.makedirs(save_path, exist_ok=True)
model.save_pretrained(save_path)
tokenizer.save_pretrained(save_path)

with open(os.path.join(save_path, 'label_encoder.pkl'), 'wb') as f:
    pickle.dump(le, f)

print(f"\n✅ HOÀN TẤT! Model đã lưu tại: {save_path}")