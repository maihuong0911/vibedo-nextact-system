import torch
import torch.nn.functional as F
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from underthesea import word_tokenize
import joblib
import requests
import json
import os
import re
import dateparser
from datetime import datetime, timedelta

# 6 nhãn hợp lệ của PhoBert_Model — dùng để validate output
VALID_LABELS = {
    "Gửi/Trả lời email",
    "Lên lịch họp",
    "Tạo nhắc nhở",
    "Soạn báo cáo",
    "Giao việc",
    "Phê duyệt",
}

class AiService:
    def __init__(self):
        # -------------------------------------------------------
        # Thử nhiều đường dẫn để tìm PhoBert_Model tự động
        # Không cần sửa tay dù đặt project ở đâu
        # -------------------------------------------------------
        base_dir = os.path.dirname(__file__)

        candidate_paths = [
            os.path.normpath(os.path.join(base_dir, '..', '..', '..', 'model', 'PhoBert_Model')),
            os.path.normpath(os.path.join(base_dir, '..', '..', 'model', 'PhoBert_Model')),
            os.path.normpath(os.path.join(base_dir, '..', 'model', 'PhoBert_Model')),
            os.path.normpath(os.path.join(base_dir, 'model', 'PhoBert_Model')),
            # Tên cũ phòng khi chưa đổi tên folder
            os.path.normpath(os.path.join(base_dir, '..', '..', '..', 'model', 'phobert_todo_model')),
            os.path.normpath(os.path.join(base_dir, '..', '..', 'model', 'phobert_todo_model')),
        ]

        model_path = None
        for path in candidate_paths:
            if os.path.isdir(path):
                model_path = path
                print(f"--- Tim thay PhoBert_Model tai: {path} ---")
                break

        if model_path is None:
            print("--- KHONG tim thay PhoBert_Model. Kiem tra lai cac duong dan sau: ---")
            for p in candidate_paths:
                print(f"   x {p}")
            self.model = None
            self.tokenizer = None
            self.label_encoder = None
            return

        print(f"--- Dang khoi tao AiService tai: {model_path} ---")

        try:
            self.model = AutoModelForSequenceClassification.from_pretrained(model_path)
            self.tokenizer = AutoTokenizer.from_pretrained(model_path, use_fast=False)
            self.label_encoder = joblib.load(os.path.join(model_path, 'label_encoder.pkl'))
            self.model.eval()
            labels = list(self.label_encoder.classes_)
            print(f"--- Khoi tao AiService THANH CONG! ---")
            print(f"--- Cac nhan model: {labels} ---")
        except Exception as e:
            print(f"--- LOI khoi tao AiService: {e} ---")
            self.model = None
            self.tokenizer = None
            self.label_encoder = None

    # -------------------------------------------------------
    # PHẦN 1: TRÍCH XUẤT CỤM THỜI GIAN BẰNG REGEX
    # -------------------------------------------------------
    TIME_PATTERNS = [
        # Giờ cụ thể + buổi + mốc ngày
        r'\d{1,2}[hH:]\d{0,2}\s*(?:sáng|chiều|tối|đêm|trưa)?\s*(?:hôm nay|ngày mai|mai|hôm sau|ngày kia)',
        r'\d{1,2}[hH:]\d{0,2}\s*(?:sáng|chiều|tối|đêm|trưa)',
        # Buổi + mốc ngày (không có giờ)
        r'(?:sáng|chiều|tối|đêm|trưa)\s*(?:hôm nay|ngày mai|mai|hôm sau|ngày kia)',
        # Mốc ngày đơn
        r'(?:hôm nay|ngày mai|mai|hôm sau|ngày kia|cuối tuần|thứ \w+|tuần tới|tuần sau|tháng tới|tháng sau)',
        # Ngày tháng năm cụ thể (dd/mm/yyyy hoặc dd-mm-yyyy)
        r'\d{1,2}[/\-]\d{1,2}(?:[/\-]\d{2,4})?',
        # "X ngày nữa / X tuần nữa"
        r'\d+\s*(?:ngày|tuần|tháng|giờ)\s*(?:nữa|sau)',
        # "cuối tháng / đầu tháng / giữa tháng"
        r'(?:cuối|đầu|giữa)\s*(?:tháng|tuần)',
    ]

    def _extract_time_phrase(self, text: str) -> str | None:
        """
        Dùng regex tìm cụm thời gian trong câu, trả về cụm đó để parse riêng.
        Tránh trường hợp dateparser bị nhiễu bởi toàn bộ câu.
        """
        text_lower = text.lower()
        for pattern in self.TIME_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                return match.group(0).strip()
        return None

    # -------------------------------------------------------
    # PHẦN 2: PARSE THỜI GIAN VỚI FALLBACK THỦ CÔNG
    # -------------------------------------------------------
    def _parse_deadline(self, text: str) -> datetime | None:
        now = datetime.now()
        text_lower = text.lower()

        # --- Bước 1: Thử trích cụm thời gian rồi parse cụm đó ---
        phrase = self._extract_time_phrase(text)
        if phrase:
            parsed = dateparser.parse(
                phrase,
                languages=['vi'],
                settings={
                    'PREFER_DATES_FROM': 'future',
                    'RELATIVE_BASE': now,
                    'RETURN_AS_TIMEZONE_AWARE': False,
                    'PREFER_DAY_OF_MONTH': 'first',
                }
            )
            if parsed:
                return self._fix_hour(parsed, phrase, text_lower)

        # --- Bước 2: Fallback — thử parse toàn câu ---
        parsed = dateparser.parse(
            text,
            languages=['vi'],
            settings={
                'PREFER_DATES_FROM': 'future',
                'RELATIVE_BASE': now,
                'RETURN_AS_TIMEZONE_AWARE': False,
            }
        )
        if parsed:
            return self._fix_hour(parsed, text, text_lower)

        # --- Bước 3: Fallback thủ công cho các từ phổ biến ---
        return self._manual_fallback(text_lower, now)

    def _fix_hour(self, dt: datetime, phrase: str, text_lower: str) -> datetime:
        """Gán giờ theo buổi nếu dateparser trả về 00:00."""
        if dt.hour != 0 or dt.minute != 0:
            return dt

        phrase_lower = phrase.lower()
        if any(w in phrase_lower or w in text_lower for w in ["sáng"]):
            return dt.replace(hour=8, minute=0)
        if any(w in phrase_lower or w in text_lower for w in ["trưa"]):
            return dt.replace(hour=12, minute=0)
        if any(w in phrase_lower or w in text_lower for w in ["chiều"]):
            return dt.replace(hour=14, minute=0)
        if any(w in phrase_lower or w in text_lower for w in ["tối", "đêm"]):
            return dt.replace(hour=19, minute=0)
        return dt

    def _manual_fallback(self, text_lower: str, now: datetime) -> datetime | None:
        """Parse thủ công các từ phổ biến mà dateparser hay bỏ qua."""
        hour_match = re.search(r'(\d{1,2})[hH:](\d{0,2})', text_lower)
        hour, minute = None, 0
        if hour_match:
            hour = int(hour_match.group(1))
            minute = int(hour_match.group(2)) if hour_match.group(2) else 0
            if "chiều" in text_lower or "tối" in text_lower:
                if hour < 12:
                    hour += 12
            elif "sáng" in text_lower and hour == 12:
                hour = 0

        base_date = None
        if any(w in text_lower for w in ["ngày mai", "mai", "sáng mai", "chiều mai", "tối mai", "hôm sau"]):
            base_date = now + timedelta(days=1)
        elif any(w in text_lower for w in ["hôm nay", "chiều nay", "sáng nay", "tối nay"]):
            base_date = now
        elif "ngày kia" in text_lower or "ngày mốt" in text_lower:
            base_date = now + timedelta(days=2)
        elif "cuối tuần" in text_lower:
            days_ahead = 5 - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            base_date = now + timedelta(days=days_ahead)
        elif "tuần tới" in text_lower or "tuần sau" in text_lower:
            base_date = now + timedelta(weeks=1)
        elif "tháng tới" in text_lower or "tháng sau" in text_lower:
            month = now.month % 12 + 1
            year = now.year + (1 if now.month == 12 else 0)
            base_date = now.replace(year=year, month=month, day=1)

        if base_date and hour is not None:
            return base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        elif base_date:
            return base_date.replace(second=0, microsecond=0)

        return None

    # -------------------------------------------------------
    # PHẦN 3: KIỂM TRA TEXT CÓ Ý NGHĨA — chặn input bàn phím linh tinh
    # -------------------------------------------------------
    # Nguyên âm tiếng Việt đầy đủ (có dấu + không dấu)
    _VOWELS = set(
        'aăâeêiouươ'
        'áàảãạắằẳẵặấầẩẫậéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ'
        'AĂÂEÊIOUƯƠÁÀẢÃẠẮẰẲẴẶẤẦẨẪẬÉÈẺẼẸẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌỐỒỔỖỘỚỜỞỠỢÚÙỦŨỤỨỪỬỮỰÝỲỶỸỴ'
    )

    # Từ khóa tiếng Việt / hành động phổ biến — nếu có ít nhất 1 từ này → meaningful
    _VN_KEYWORDS = {
        'gửi', 'giao', 'tạo', 'họp', 'soạn', 'lên', 'lịch', 'báo', 'cáo',
        'email', 'phê', 'duyệt', 'nhắc', 'nhở', 'việc', 'task', 'deadline',
        'hôm', 'nay', 'mai', 'tuần', 'tháng', 'cuối', 'sáng', 'chiều', 'tối',
        'gặp', 'call', 'meeting', 'report', 'submit', 'review', 'check',
        'send', 'write', 'prepare', 'finish', 'complete', 'update', 'fix',
        'nộp', 'kiểm', 'tra', 'chuẩn', 'bị', 'hoàn', 'thành', 'xử', 'lý',
    }

    def _check_meaningful(self, text: str) -> bool:
        """
        Trả về True nếu text CÓ nghĩa, False nếu là chuỗi gõ linh tinh.

        Thuật toán 3 lớp:
        1. Nếu có từ khóa tiếng Việt / hành động → meaningful ngay
        2. Kiểm tra tỷ lệ nguyên âm trong từng "word"
           - Từ thật (vi/en) luôn có nguyên âm
           - Chuỗi random (kjhg, uerrthytf) thường thiếu nguyên âm hoặc cụm bất thường
        3. Kiểm tra tỷ lệ consonant cluster bất thường (> 4 phụ âm liên tiếp)
        """
        t = text.strip().lower()
        if not t or len(t) < 2:
            return False

        # Lớp 1: có từ khóa thật → pass ngay
        words = t.split()
        for w in words:
            if w in self._VN_KEYWORDS:
                return True

        # Lớp 2: kiểm tra từng word có nguyên âm không
        total_words = 0
        bad_words = 0
        for w in words:
            alpha_only = ''.join(c for c in w if c.isalpha())
            if len(alpha_only) < 2:
                continue
            total_words += 1
            has_vowel = any(c in self._VOWELS for c in alpha_only)
            if not has_vowel:
                bad_words += 1
                continue
            # Lớp 3: cụm phụ âm liên tiếp > 4 ký tự → nghi ngờ
            consonant_run = 0
            max_run = 0
            for c in alpha_only:
                if c not in self._VOWELS:
                    consonant_run += 1
                    max_run = max(max_run, consonant_run)
                else:
                    consonant_run = 0
            if max_run > 4:
                bad_words += 1

        if total_words == 0:
            return False

        bad_ratio = bad_words / total_words
        # > 60% từ bất thường → vô nghĩa
        if bad_ratio > 0.6:
            return False

        return True

    # -------------------------------------------------------
    # PHẦN 4: PREDICT CHÍNH — confidence score THẬT từ softmax
    # -------------------------------------------------------
    def predict(self, text):
        """
        Dự đoán nhãn (PhoBERT) + trích xuất thời gian.
        Confidence = xác suất softmax thật (không hardcode).

        Quy tắc quan trọng:
        - Nếu text rỗng  → label=None, không gán nhãn bừa
        - Nếu model chưa load → label=None, không gán nhãn bừa
        - Nếu model predict ra nhãn ngoài VALID_LABELS → label=None
        - Chỉ trả label khi model thật sự predict được và nhãn hợp lệ
        """
        # --- Text rỗng: không gán nhãn ---
        if not text or not text.strip():
            return {
                "label": None,
                "confidence": 0.0,
                "deadline": None,
                "deadline_display": "Không có",
                "error": "Nội dung trống"
            }

        # --- Model chưa load: không gán nhãn bừa ---
        if not self.model or not self.tokenizer or not self.label_encoder:
            deadline = self._parse_deadline(text)
            return {
                "label": None,
                "confidence": 0.0,
                "deadline": deadline.isoformat() if deadline else None,
                "deadline_display": deadline.strftime("%d/%m/%Y %H:%M") if deadline else "Không có",
                "error": "Model PhoBert_Model chưa được khởi tạo"
            }

        # --- Phân loại nhãn + confidence thật từ softmax ---
        label = None
        confidence = 0.0

        try:
            processed_text = word_tokenize(text.strip(), format="text")
            inputs = self.tokenizer(
                processed_text,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=256
            )
            with torch.no_grad():
                outputs = self.model(**inputs)
                # Lấy softmax probability thật — không hardcode
                probs = F.softmax(outputs.logits, dim=-1)
                prediction = torch.argmax(probs, dim=-1).item()
                confidence = round(probs[0][prediction].item() * 100, 2)  # % thật

            predicted_label = self.label_encoder.inverse_transform([prediction])[0]

            # ── GIBBERISH FILTER: dùng entropy của phân phối softmax ──────
            # Text có nghĩa → model rất "chắc" → entropy THẤP, confidence CAO
            # Text vô nghĩa → model phân vân đều → entropy CAO
            # Nhưng PhoBERT đặc biệt: với text random nó vẫn tập trung 1 nhãn
            # → cần kết hợp thêm kiểm tra ngôn ngữ học
            import math
            entropy = -sum(
                p.item() * math.log(p.item() + 1e-9)
                for p in probs[0]
            )
            num_labels = len(probs[0])
            max_entropy = math.log(num_labels)
            # Entropy chuẩn hóa: 0 = chắc chắn 1 nhãn, 1 = phân vân đều
            normalized_entropy = entropy / max_entropy

            # Kiểm tra text có ý nghĩa (tiếng Việt / Anh thật)
            meaningful = self._check_meaningful(text.strip())

            # Từ chối nếu: text vô nghĩa VÀ (entropy cao HOẶC không phải từ điển)
            # Ngưỡng entropy: > 0.3 với text vô nghĩa → reject
            if not meaningful:
                print(f"[AiService] Text vô nghĩa '{text[:30]}' — entropy={normalized_entropy:.3f} — bỏ qua")
                label = None
                confidence = 0.0
            # Chỉ chấp nhận nhãn nằm trong bộ 6 nhãn hợp lệ
            elif predicted_label in VALID_LABELS:
                label = predicted_label
            else:
                # Model trả về nhãn cũ (dataset cũ) → không gán bừa
                print(f"[AiService] Nhãn '{predicted_label}' không hợp lệ — bỏ qua")
                label = None
                confidence = 0.0

        except Exception as e:
            print(f"[AiService] Lỗi predict label: {e}")
            label = None
            confidence = 0.0

        # --- Trích xuất thời gian ---
        deadline = self._parse_deadline(text)

        deadline_iso = None
        deadline_display = "Không có"

        if deadline:
            deadline_iso = deadline.isoformat()
            deadline_display = deadline.strftime("%d/%m/%Y %H:%M")

        return {
            "label": label,
            "confidence": confidence,   # Xác suất thật từ softmax
            "deadline": deadline_iso,
            "deadline_display": deadline_display
        }

    # -------------------------------------------------------
    # PHẦN 5: GỌI GROK API — ĐÃ SỬA INDENT (nằm TRONG class)
    # -------------------------------------------------------
    def call_grok(self, user_input: str):
        """Gọi Grok API để sinh gợi ý hành động."""
        url = "https://api.x.ai/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {os.getenv('GROK_API_KEY')}",
            "Content-Type": "application/json"
        }

        prompt = f"""Bạn là trợ lý phân tích công việc. Hãy đề xuất các hành động cụ thể cho công việc sau:
INPUT: {user_input}

Trả về JSON với format:
{{"actions": ["hành động 1", "hành động 2", "hành động 3"]}}
"""

        data = {
            "model": "grok-2-latest",
            "messages": [
                {"role": "system", "content": "You are a JSON generator. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2
        }

        try:
            res = requests.post(url, headers=headers, json=data, timeout=15)
            result = res.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[AiService] call_grok error: {e}")
            return None

    # -------------------------------------------------------
    # PHẦN 6: PARSE JSON — ĐÃ SỬA INDENT (nằm TRONG class)
    # -------------------------------------------------------
    def clean_json(self, text):
        """Trích xuất JSON từ response text."""
        if not text:
            return None
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                return None
        return None

    # -------------------------------------------------------
    # PHẦN 7: SUGGEST ACTIONS — ĐÃ SỬA INDENT (nằm TRONG class)
    # -------------------------------------------------------
    def suggest_actions(self, text):
        """Kết hợp call_grok + clean_json để trả về danh sách hành động."""
        raw = self.call_grok(text)
        data = self.clean_json(raw)
        return data