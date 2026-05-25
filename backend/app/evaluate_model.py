"""
evaluate_model.py
Đánh giá hiệu suất mô hình PhoBERT trên tập test.
Xuất: Accuracy, F1 (macro/weighted), Confusion Matrix, Classification Report.

Usage:
    python evaluate_model.py
    python evaluate_model.py --data path/to/test_data.csv
    python evaluate_model.py --output results/eval_report.json
"""

import os
import argparse
import json
import torch
import torch.nn.functional as F
import numpy as np
from pathlib import Path
from datetime import datetime

# =====================================================================
# KIỂM TRA THƯ VIỆN — hướng dẫn cài nếu thiếu
# =====================================================================
try:
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    from underthesea import word_tokenize
    import joblib
    from sklearn.metrics import (
        accuracy_score, f1_score,
        confusion_matrix, classification_report,
        ConfusionMatrixDisplay
    )
    import pandas as pd
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.rcParams['font.family'] = 'DejaVu Sans'
except ImportError as e:
    print(f"Thiếu thư viện: {e}")
    print("Cài đặt: pip install scikit-learn pandas matplotlib transformers underthesea")
    exit(1)

# =====================================================================
# CẤU HÌNH
# =====================================================================
MODEL_PATH = os.path.normpath(os.path.join(
    os.path.dirname(__file__), 'model', 'phobert_todo_model'
))

LABELS = [
    "Gửi/Trả lời email",
    "Lên lịch họp",
    "Tạo nhắc nhở",
    "Soạn báo cáo",
    "Theo dõi",
    "Nộp tài liệu",
    "Khác"
]

# =====================================================================
# DỮ LIỆU TEST MẪU — thay bằng file CSV thực nếu có
# =====================================================================
SAMPLE_TEST_DATA = [
    # (text, true_label)
    ("Gửi email báo cáo tháng 3 cho sếp", "Gửi/Trả lời email"),
    ("Trả lời email của khách hàng về đơn hàng", "Gửi/Trả lời email"),
    ("Email xác nhận đặt phòng khách sạn", "Gửi/Trả lời email"),
    ("Gửi thông báo họp cho team", "Gửi/Trả lời email"),

    ("Lên lịch họp với team marketing", "Lên lịch họp"),
    ("Đặt lịch meeting với khách hàng ABC 9h sáng mai", "Lên lịch họp"),
    ("Hẹn gặp đối tác vào chiều thứ 6", "Lên lịch họp"),
    ("Tổ chức cuộc họp review quý 1", "Lên lịch họp"),

    ("Nhắc nhở nộp báo cáo trước 5h chiều", "Tạo nhắc nhở"),
    ("Đặt nhắc nhở thanh toán hóa đơn ngày mai", "Tạo nhắc nhở"),
    ("Reminder: kiểm tra email buổi sáng", "Tạo nhắc nhở"),
    ("Nhớ gọi điện cho khách hàng vào 10h", "Tạo nhắc nhở"),

    ("Soạn báo cáo tình hình kinh doanh tháng 3", "Soạn báo cáo"),
    ("Viết báo cáo tiến độ dự án cho ban lãnh đạo", "Soạn báo cáo"),
    ("Chuẩn bị tài liệu thuyết trình cuối quý", "Soạn báo cáo"),
    ("Lập báo cáo tài chính tuần này", "Soạn báo cáo"),

    ("Theo dõi tiến độ dự án ABC", "Theo dõi"),
    ("Check lại kết quả công việc của team", "Theo dõi"),
    ("Follow up với nhà cung cấp về đơn hàng", "Theo dõi"),
    ("Kiểm tra trạng thái thanh toán", "Theo dõi"),

    ("Nộp hồ sơ xin việc trước thứ 6", "Nộp tài liệu"),
    ("Submit báo cáo cuối kỳ cho giảng viên", "Nộp tài liệu"),
    ("Bàn giao tài liệu dự án cho team mới", "Nộp tài liệu"),
    ("Gửi file hợp đồng đã ký cho phòng pháp lý", "Nộp tài liệu"),

    ("Mua đồ ăn trưa", "Khác"),
    ("Đọc sách về quản lý thời gian", "Khác"),
    ("Tập thể dục buổi sáng", "Khác"),
    ("Dọn dẹp bàn làm việc", "Khác"),
]


# =====================================================================
# LOAD MODEL
# =====================================================================
def load_model(model_path: str):
    print(f"📂 Đang load model từ: {model_path}")
    if not os.path.exists(model_path):
        print(f"❌ Không tìm thấy model tại: {model_path}")
        return None, None, None

    try:
        model = AutoModelForSequenceClassification.from_pretrained(model_path)
        tokenizer = AutoTokenizer.from_pretrained(model_path, use_fast=False)
        label_encoder = joblib.load(os.path.join(model_path, 'label_encoder.pkl'))
        model.eval()
        print(" Load model thành công!")
        return model, tokenizer, label_encoder
    except Exception as e:
        print(f"❌ Lỗi load model: {e}")
        return None, None, None


# =====================================================================
# PREDICT BATCH
# =====================================================================
def predict_batch(texts, model, tokenizer, label_encoder):
    """Dự đoán nhãn + confidence cho danh sách văn bản."""
    predictions = []
    confidences = []

    for text in texts:
        try:
            processed = word_tokenize(text.strip(), format="text")
            inputs = tokenizer(
                processed,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=256
            )
            with torch.no_grad():
                outputs = model(**inputs)
                probs = F.softmax(outputs.logits, dim=-1)
                pred_idx = torch.argmax(probs, dim=-1).item()
                confidence = round(probs[0][pred_idx].item() * 100, 2)

            label = label_encoder.inverse_transform([pred_idx])[0]
            predictions.append(label)
            confidences.append(confidence)
        except Exception as e:
            print(f"  ⚠️ Lỗi predict: {text[:50]}... → {e}")
            predictions.append("Khác")
            confidences.append(0.0)

    return predictions, confidences


# =====================================================================
# LOAD TEST DATA TỪ CSV
# =====================================================================
def load_test_data_from_csv(csv_path: str):
    """Load test data từ CSV với cột: text, label"""
    try:
        df = pd.read_csv(csv_path, encoding='utf-8')
        if 'text' not in df.columns or 'label' not in df.columns:
            print(f" CSV cần có cột 'text' và 'label'. Có: {list(df.columns)}")
            return None
        texts = df['text'].tolist()
        labels = df['label'].tolist()
        print(f" Load {len(texts)} mẫu từ: {csv_path}")
        return list(zip(texts, labels))
    except Exception as e:
        print(f"❌ Lỗi đọc CSV: {e}")
        return None


# =====================================================================
# VẼ CONFUSION MATRIX
# =====================================================================
def plot_confusion_matrix(cm, labels, output_dir: str):
    """Vẽ và lưu confusion matrix dạng heatmap."""
    try:
        fig, ax = plt.subplots(figsize=(10, 8))

        im = ax.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
        plt.colorbar(im, ax=ax)

        ax.set(
            xticks=np.arange(len(labels)),
            yticks=np.arange(len(labels)),
            xticklabels=labels,
            yticklabels=labels,
            title="Confusion Matrix — PhoBERT NextAct",
            ylabel="Nhãn thật",
            xlabel="Nhãn dự đoán"
        )

        plt.setp(ax.get_xticklabels(), rotation=30, ha="right", rotation_mode="anchor", fontsize=9)
        plt.setp(ax.get_yticklabels(), fontsize=9)

        # Hiển thị số trong mỗi ô
        thresh = cm.max() / 2.0
        for i in range(len(labels)):
            for j in range(len(labels)):
                ax.text(j, i, format(cm[i, j], 'd'),
                        ha="center", va="center",
                        color="white" if cm[i, j] > thresh else "black",
                        fontsize=10)

        fig.tight_layout()
        out_path = os.path.join(output_dir, "confusion_matrix.png")
        plt.savefig(out_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f" Đã lưu confusion matrix: {out_path}")
        return out_path
    except Exception as e:
        print(f"⚠️ Không thể vẽ confusion matrix: {e}")
        return None


# =====================================================================
# MAIN EVALUATION
# =====================================================================
def evaluate(data_path: str = None, output_dir: str = "results"):
    # Load model
    model, tokenizer, label_encoder = load_model(MODEL_PATH)
    if model is None:
        print(" Không thể chạy evaluation vì model không load được.")
        return

    # Load test data
    if data_path and os.path.exists(data_path):
        test_data = load_test_data_from_csv(data_path)
        if test_data is None:
            print("Dùng dữ liệu test mẫu...")
            test_data = SAMPLE_TEST_DATA
    else:
        print("ℹ️  Không có file CSV → dùng dữ liệu test mẫu tích hợp sẵn")
        test_data = SAMPLE_TEST_DATA

    texts = [d[0] for d in test_data]
    true_labels = [d[1] for d in test_data]

    print(f"\n🔍 Đang dự đoán {len(texts)} mẫu...")
    pred_labels, confidences = predict_batch(texts, model, tokenizer, label_encoder)

    # Tính metrics
    accuracy = accuracy_score(true_labels, pred_labels)
    f1_macro = f1_score(true_labels, pred_labels, average='macro', zero_division=0)
    f1_weighted = f1_score(true_labels, pred_labels, average='weighted', zero_division=0)

    # Lấy tất cả nhãn xuất hiện
    all_labels = sorted(list(set(true_labels + pred_labels)))
    cm = confusion_matrix(true_labels, pred_labels, labels=all_labels)
    report = classification_report(true_labels, pred_labels, labels=all_labels, zero_division=0, output_dict=True)
    report_text = classification_report(true_labels, pred_labels, labels=all_labels, zero_division=0)

    # ===== IN KẾT QUẢ =====
    print("\n" + "="*60)
    print("        ĐÁNH GIÁ MÔ HÌNH PHOBERT — NEXTACT")
    print("="*60)
    print(f"📊 Accuracy:           {accuracy*100:.2f}%")
    print(f"📊 F1 (macro):         {f1_macro*100:.2f}%")
    print(f"📊 F1 (weighted):      {f1_weighted*100:.2f}%")
    print(f"📊 Confidence TB:      {np.mean(confidences):.2f}%")
    print(f"📊 Tổng mẫu test:      {len(texts)}")
    print(f"📊 Phân loại đúng:     {sum(p == t for p, t in zip(pred_labels, true_labels))}")
    print(f"📊 Phân loại sai:      {sum(p != t for p, t in zip(pred_labels, true_labels))}")
    print("="*60)
    print("\n📋 Classification Report:")
    print(report_text)

    # ===== LƯU KẾT QUẢ =====
    os.makedirs(output_dir, exist_ok=True)

    # Lưu confusion matrix hình
    plot_confusion_matrix(cm, all_labels, output_dir)

    # Lưu report JSON đầy đủ
    eval_result = {
        "timestamp": datetime.now().isoformat(),
        "model_path": MODEL_PATH,
        "num_samples": len(texts),
        "accuracy": round(accuracy * 100, 2),
        "f1_macro": round(f1_macro * 100, 2),
        "f1_weighted": round(f1_weighted * 100, 2),
        "avg_confidence": round(float(np.mean(confidences)), 2),
        "classification_report": report,
        "confusion_matrix": cm.tolist(),
        "labels": all_labels,
        "per_sample": [
            {
                "text": t[:80],
                "true": true,
                "pred": pred,
                "confidence": conf,
                "correct": true == pred
            }
            for t, true, pred, conf in zip(texts, true_labels, pred_labels, confidences)
        ]
    }

    json_path = os.path.join(output_dir, "eval_report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(eval_result, f, ensure_ascii=False, indent=2)
    print(f"\n Đã lưu báo cáo đầy đủ: {json_path}")

    # Lưu CSV chi tiết từng mẫu
    df_result = pd.DataFrame(eval_result["per_sample"])
    csv_path = os.path.join(output_dir, "eval_details.csv")
    df_result.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f" Đã lưu chi tiết từng mẫu: {csv_path}")

    # ===== IN CÁC MẪU DỰ ĐOÁN SAI =====
    wrong = [(t, true, pred, conf)
             for t, true, pred, conf in zip(texts, true_labels, pred_labels, confidences)
             if true != pred]

    if wrong:
        print(f"\n⚠️  {len(wrong)} mẫu dự đoán SAI:")
        for text, true, pred, conf in wrong:
            print(f"  Text:   {text[:60]}")
            print(f"  Thật:   {true}  →  Dự đoán: {pred}  (conf: {conf:.1f}%)")
            print()

    return eval_result


# =====================================================================
# ENTRY POINT
# =====================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Đánh giá PhoBERT model NextAct")
    parser.add_argument("--data", type=str, default=None,
                        help="Đường dẫn file CSV test (cột: text, label). Mặc định: dùng dữ liệu mẫu")
    parser.add_argument("--output", type=str, default="results",
                        help="Thư mục lưu kết quả (mặc định: results/)")
    args = parser.parse_args()

    evaluate(data_path=args.data, output_dir=args.output)