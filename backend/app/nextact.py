from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import joblib
from pathlib import Path
import re
from datetime import datetime, timedelta
import os
import requests
from dotenv import load_dotenv

# Load biến môi trường
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

router = APIRouter()

# Cấu hình Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Load model
MODEL_PATH = Path(__file__).resolve().parent.parent.parent / "model" / "nextact_model.joblib"
try:
    model = joblib.load(MODEL_PATH)
except Exception as e:
    print(f"Error loading model: {e}")
    model = None

class TodoTextRequest(BaseModel):
    text: str

class ChatRequest(BaseModel):
    task_title: str
    task_description: str = ""
    due_date: str = ""
    message: str

def extract_deadline(text):
    """Phân tích hạn chót từ text tiếng Việt"""
    text_lower = text.lower()
    today = datetime.now().date()
    is_this_week = 'tuần này' in text_lower or 'tuần hiện tại' in text_lower
    is_next_week = 'tuần sau' in text_lower or 'tuần tiếp theo' in text_lower or 'tuần tiếp' in text_lower
    
    # Mapping các cụm từ sang ngày
    patterns = {
        r'hôm nay': today,
        r'ngày mai': today + timedelta(days=1),
        r'ngày kia': today + timedelta(days=2),
        r'thứ 2|thứ hai': _get_target_day(today, 0, is_this_week, is_next_week),
        r'thứ 3|thứ ba': _get_target_day(today, 1, is_this_week, is_next_week),
        r'thứ 4|thứ tư': _get_target_day(today, 2, is_this_week, is_next_week),
        r'thứ 5|thứ năm': _get_target_day(today, 3, is_this_week, is_next_week),
        r'thứ 6|thứ sáu': _get_target_day(today, 4, is_this_week, is_next_week),
        r'thứ 7|thứ bảy': _get_target_day(today, 5, is_this_week, is_next_week),
        r'chủ nhật': _get_target_day(today, 6, is_this_week, is_next_week),
        r'cuối tuần': today + timedelta(days=(5-today.weekday()) % 7) if today.weekday() < 5 else today,
    }
    
    for pattern, date in patterns.items():
        if re.search(pattern, text_lower):
            return str(date)
    
    return None

def _get_target_day(today, target_weekday, is_this_week=False, is_next_week=False):
    """
    Tính ngày có weekday chỉ định
    - Nếu is_next_week=True: lấy ngày đó ở tuần tiếp theo (cộng thêm 7 ngày)
    - Nếu is_this_week=True: lấy ngày đó trong tuần hiện tại (hoặc hôm nay nếu trùng)
    - Nếu cả hai False: luôn lấy ngày tiếp theo
    """
    current_weekday = today.weekday()
    
    if is_next_week:
        # Luôn lấy tuần tiếp theo
        days_ahead = target_weekday - current_weekday
        if days_ahead <= 0:
            days_ahead += 7
        days_ahead += 7  # Thêm 7 ngày để sang tuần tiếp theo
    elif is_this_week:
        days_ahead = target_weekday - current_weekday
        if days_ahead < 0:
            # Ngày đó đã qua trong tuần này, lấy tuần tiếp theo
            days_ahead += 7
    else:
        days_ahead = target_weekday - current_weekday
        if days_ahead <= 0:
            days_ahead += 7
    
    return today + timedelta(days=days_ahead)

@router.post("/nextact/classify")
def classify_todo(request: TodoTextRequest):
    """Phân loại công việc dựa trên văn bản"""
    if not model:
        raise HTTPException(status_code=500, detail="Model not loaded")
    
    try:
        # Dự đoán nhãn
        prediction = model.predict([request.text])[0]
        
        # Lấy xác suất cho từng lớp
        probabilities = model.predict_proba([request.text])[0]
        
        # Tạo mapping lớp -> xác suất
        class_names = model.classes_
        confidence = float(max(probabilities))
        
        # Phân tích hạn chót
        deadline = extract_deadline(request.text)
        
        return {
            "text": request.text,
            "category": prediction,
            "confidence": round(confidence * 100, 2),
            "deadline": deadline,
            "probabilities": {
                class_name: round(float(prob) * 100, 2)
                for class_name, prob in zip(class_names, probabilities)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/nextact/models")
def list_models():
    """Debug: List available models"""
    if not GEMINI_API_KEY:
        return {"error": "No API key"}
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1/models?key={GEMINI_API_KEY}"
        response = requests.get(url)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.json()
    except Exception as e:
        return {"error": str(e)}

@router.post("/nextact/chat")
def chat_with_gemini(request: ChatRequest):
    """Chat với Gemini để nhận gợi ý về công việc"""
    if not GEMINI_API_KEY:
        print("ERROR: Gemini API key not found")
        raise HTTPException(status_code=500, detail="Gemini API key not configured")
    
    try:
        # Tạo prompt context về công việc
        system_prompt = f"""Bạn là một trợ lý ảo giúp người dùng quản lý công việc và chuẩn bị cho công việc.
Thông tin công việc hiện tại:
- Tiêu đề: {request.task_title}
- Mô tả: {request.task_description or '(Không có mô tả)'}
- Hạn chót: {request.due_date or '(Không có hạn chót)'}

Hãy trả lời câu hỏi của người dùng một cách cụ thể, hữu ích và liên quan đến công việc này.
Nếu câu hỏi là yêu cầu gợi ý chung, hãy đưa ra các bước chuẩn bị, cảnh báo, và khoảng thời gian cần thiết.
Nếu câu hỏi cụ thể, hãy trả lời trực tiếp và liên quan đến công việc này.
Trả lời bằng tiếng Việt, ngắn gọn và dễ hiểu."""
        
        print(f"DEBUG: API Key present: {bool(GEMINI_API_KEY)}")
        print(f"DEBUG: Request message: {request.message}")
        print(f"DEBUG: Task: {request.task_title}")
        
        # Gọi Gemini API qua REST
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": f"{system_prompt}\n\nCâu hỏi của người dùng: {request.message}"
                        }
                    ]
                }
            ]
        }
        
        response = requests.post(url, json=payload)
        result = response.json()
        
        if response.status_code != 200:
            print(f"ERROR: {response.status_code} - {result}")
            raise HTTPException(status_code=400, detail=f"Gemini API error: {result}")
        
        # Extract text từ response
        reply = result['candidates'][0]['content']['parts'][0]['text']
        
        return {
            "reply": reply,
            "success": True
        }
    except Exception as e:
        print(f"ERROR in chat endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Chat error: {str(e)}")