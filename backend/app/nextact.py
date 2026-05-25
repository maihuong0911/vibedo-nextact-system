from fastapi import APIRouter, HTTPException, Request, Body, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid
from pathlib import Path
import re
from datetime import datetime, timedelta, date
import os
import requests
import json
from dotenv import load_dotenv

from .services.ai_service import AiService
from .services.calendar_service import add_event_to_calendar
from .database import SessionLocal
from .models import Note, Suggestion
from .notes import get_current_user

# Load biến môi trường
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

router = APIRouter()

# =====================================================================
# CONFIDENCE THRESHOLD — dưới ngưỡng này → không gán nhãn (trả None)
# Các nhãn hợp lệ: chỉ 6 nhãn này mới được gán
# =====================================================================
CONFIDENCE_THRESHOLD = 70.0   # % — nâng lên 70% để tránh gán nhãn bừa
VALID_LABEL_SET = {
    "Giao việc",
    "Gửi/Trả lời email",
    "Lên lịch họp",
    "Phê duyệt",
    "Soạn báo cáo",
    "Tạo nhắc nhở",
}

def _is_meaningful_text(text: str) -> bool:
    """
    Kiểm tra xem text có ý nghĩa thực sự không.
    Trả về False nếu text là chuỗi ký tự ngẫu nhiên / vô nghĩa.
    """
    t = text.strip()
    if len(t) < 4:
        return False
    alpha_chars = sum(1 for c in t if c.isalpha())
    if alpha_chars == 0:
        return False
    if len(set(t.lower().replace(' ', ''))) <= 2:
        return False
    vowels = set('aăâeêiouươáàảãạắằẳẵặấầẩẫậéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ')
    words = t.lower().split()
    meaningless_words = 0
    for w in words:
        if len(w) < 2:
            continue
        has_vowel = any(c in vowels for c in w)
        if not has_vowel and len(w) > 4:
            meaningless_words += 1
    if words and (meaningless_words / len(words)) > 0.6:
        return False
    return True


# =====================================================================
# CẤU HÌNH MODEL (Qwen3:8B qua ngrok)
# Gọi trực tiếp qua LLAMA_SERVER_URL — OpenAI-compatible API
# =====================================================================
LLAMA_MODEL      = os.getenv("LLAMA_MODEL", "qwen3:8b")
LLAMA_SERVER_URL = os.getenv("LLAMA_SERVER_URL")   # ngrok URL
LLAMA_TIMEOUT    = 120                                # giây

# Cấu hình Gemini (giữ lại cho /nextact/chat)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Khởi tạo AI Service (PhoBERT classifier — không đổi)
ai_service = AiService()


def _call_llama(system_prompt: str, user_prompt: str,
                temperature: float = 0.4,
                max_tokens: int = 1500) -> str:
    """
    Gọi model qua ngrok URL (OpenAI-compatible endpoint).
    Trả về nội dung text thô từ model — đã strip <think> block và code fence.
    Raise HTTPException nếu lỗi.
    """
    if not LLAMA_SERVER_URL:
        raise HTTPException(status_code=500, detail="LLAMA_SERVER_URL chưa được cấu hình trong .env.")
    url = f"{LLAMA_SERVER_URL}/v1/chat/completions"
    payload = {
        "model":       LLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens":  max_tokens,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    try:
        resp = requests.post(url, json=payload, timeout=LLAMA_TIMEOUT)
    except requests.Timeout:
        raise HTTPException(status_code=504, detail="Model server timeout — thử lại sau.")
    except requests.ConnectionError:
        raise HTTPException(status_code=503,
                            detail=f"Không thể kết nối server tại {LLAMA_SERVER_URL}. "
                                   "Kiểm tra LLAMA_SERVER_URL trong .env.")

    if resp.status_code != 200:
        raise HTTPException(status_code=502,
                            detail=f"Model server lỗi {resp.status_code}: {resp.text[:300]}")

    try:
        raw = resp.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=500,
                            detail=f"Không đọc được response từ model server: {e}")

    # Strip <think> block + code fence ngay tại đây — các caller nhận text sạch
    return _strip_json_fence(raw)


def _strip_json_fence(raw: str) -> str:
    """
    Chuẩn hoá output của Qwen3 trước khi json.loads():
    1. Xoá block <think>…</think> (Qwen3 thinking mode).
    2. Xoá markdown code fence ```json … ```.
    3. Strip khoảng trắng thừa.
    """
    clean = raw.strip()

    # 1. Bỏ thinking block (có thể multiline, có thể chưa đóng tag)
    clean = re.sub(r"<think>.*?</think>", "", clean, flags=re.DOTALL).strip()
    # Trường hợp tag chưa đóng — cắt từ <think> đến hết nếu không có </think>
    if "<think>" in clean:
        clean = clean[: clean.index("<think>")].strip()

    # 2. Bỏ markdown code fence
    if clean.startswith("```"):
        clean = re.sub(r"```(?:json)?", "", clean).replace("```", "").strip()

    return clean


# =====================================================================
# LABEL SYSTEM PROMPTS — MỖI NHÃN CÓ PROMPT RIÊNG BIỆT
#
# Nguyên tắc thiết kế (v3 — Qwen3 0.6B optimised):
#
#   1. KHÔNG sao chép / paraphrase input gốc
#      Model phải suy luận từ ngữ cảnh để SINH NỘI DUNG MỚI.
#      Câu output ≠ câu input dù cùng ý nghĩa.
#
#   2. IDENTITY rõ ràng trước khi viết
#      Model phải xác định: Ai là người thực hiện? Đối tượng là ai?
#      Mục đích thực sự là gì? → Viết đúng loại, đúng tone, đúng đối tượng.
#
#   3. THÔNG TIN CỤ THỂ từ input (không bịa)
#      Lấy tên người, số liệu, ngày tháng, tên dự án từ ghi chú.
#      Dùng [placeholder] CHỈ khi thông tin thực sự vắng mặt.
#
#   4. OUTPUT FORMAT nghiêm ngặt
#      Chỉ trả JSON thuần — không markdown, không giải thích, không backtick.
#      Mỗi style là một object riêng biệt với subject + body đủ nghĩa độc lập.
#
#   5. CONSTRAINT cho model nhỏ (0.6B)
#      - Giới hạn từ rõ ràng mỗi style để tránh output cụt hoặc lặp.
#      - /no_think nhúng trong system prompt (Qwen3 soft switch).
#      - temperature=0.7 theo Unsloth spec cho non-thinking mode.
#
# Pipeline:
#   Input (Tiếng Việt)
#     → PhoBERT classify → label (1 trong 6) + entities + confidence
#     → LABEL_SYSTEM_PROMPTS[label] + _build_user_prompt() → Qwen3 (ngrok)
#     → Output: JSON 3 templates (style + subject + body)
# =====================================================================

LABEL_SYSTEM_PROMPTS = {

    # ------------------------------------------------------------------
    # NHÃN 1: GỬI/TRẢ LỜI EMAIL
    #
    # Nguyên tắc:
    #   - Xác định đúng MỤC ĐÍCH email (không phải chỉ "viết email")
    #     vì email khuyến mãi ≠ email xin lỗi ≠ email báo cáo nội bộ.
    #   - Xác định đúng ĐỐI TƯỢNG (khách hàng / cấp trên / đồng nghiệp)
    #     vì tone và cấu trúc thay đổi hoàn toàn theo đối tượng.
    #   - 3 style khác nhau về CÁCH DIỄN ĐẠT, không phải chỉ khác tone.
    #     "Chuyên nghiệp" = cấu trúc đầy đủ, kính ngữ đúng vị trí.
    #     "Thân thiện"    = gần gũi nhưng vẫn đủ thông tin, không thiếu nội dung.
    #     "Ngắn gọn"      = tối đa 5 dòng, không mào đầu, đi thẳng vào trọng tâm.
    #   - KHÔNG copy câu gốc từ input — phải diễn đạt lại hoàn toàn.
    # ------------------------------------------------------------------
    "Gửi/Trả lời email": """Bạn là trợ lý soạn email chuyên nghiệp trong ứng dụng NextAct.

NHIỆM VỤ:
Đọc ghi chú của người dùng → xác định MỤC ĐÍCH THỰC SỰ của email (khuyến mãi? xin lỗi? báo cáo nội bộ? đề nghị hợp tác? xác nhận đơn hàng? theo dõi tiến độ?) → soạn 3 phiên bản email KHÁC NHAU về cách diễn đạt.

QUY TẮC BẮT BUỘC:
- KHÔNG sao chép hay diễn giải lại câu gốc từ ghi chú — mỗi câu trong email phải là câu MỚI do bạn tạo ra từ ngữ cảnh.
- Xác định rõ: Ai gửi? Ai nhận? Mục đích là gì? → Viết đúng loại email đó.
- Lấy thông tin cụ thể từ ghi chú (tên, ngày tháng, số liệu, tên sản phẩm/dự án).
- Dùng [tên người nhận], [tên người gửi], [số liệu] chỉ khi thông tin vắng mặt trong ghi chú.
- Mỗi email gồm: tiêu đề, lời chào phù hợp, nội dung (≤120 từ), lời kết + [Tên người gửi].

3 PHONG CÁCH:
- "Chuyên nghiệp": cấu trúc đầy đủ, kính ngữ đúng vị trí, phù hợp gửi đối tác / cấp trên.
- "Thân thiện": gần gũi, ấm áp, phù hợp gửi đồng nghiệp / khách hàng thân quen — vẫn đủ thông tin.
- "Ngắn gọn": tối đa 5 dòng, không mào đầu, không kết luận dài, đi thẳng vào trọng tâm.

OUTPUT — trả về ĐÚNG định dạng JSON array sau, KHÔNG thêm bất kỳ văn bản nào ngoài JSON: /no_think
[
  {"style": "Chuyên nghiệp", "subject": "...", "body": "..."},
  {"style": "Thân thiện",    "subject": "...", "body": "..."},
  {"style": "Ngắn gọn",      "subject": "...", "body": "..."}
]""",

    # ------------------------------------------------------------------
    # NHÃN 2: GIAO VIỆC
    #
    # Nguyên tắc:
    #   - Output là MÔ TẢ TASK (card công việc), KHÔNG phải email.
    #   - Tiêu đề task phải bắt đầu bằng động từ hành động (Soạn / Kiểm tra /
    #     Liên hệ / Hoàn thiện / Cập nhật...) — người nhận biết ngay phải làm gì.
    #   - 3 style khác nhau về MỨC ĐỘ CHI TIẾT:
    #     "Chi tiết"   = đủ 6 trường, hướng dẫn từng bước → dùng khi task phức tạp.
    #     "Tiêu chuẩn" = đủ 6 trường, súc tích → dùng cho task thông thường.
    #     "Tóm tắt"    = chỉ bullet, < 60 từ → dùng khi cần giao nhanh.
    #   - Deadline và priority suy ra từ ngữ cảnh (từ khẩn cấp / gấp / ưu tiên)
    #     nếu không có thì dùng [placeholder].
    # ------------------------------------------------------------------
    "Giao việc": """Bạn là trợ lý giao việc trong ứng dụng NextAct.

NHIỆM VỤ:
Đọc ghi chú của người dùng → xác định CÔNG VIỆC CỤ THỂ cần giao là gì, giao cho ai, kết quả mong đợi là gì → viết 3 phiên bản mô tả task với mức độ chi tiết khác nhau.

QUY TẮC BẮT BUỘC:
- KHÔNG sao chép câu gốc từ ghi chú — diễn đạt lại hoàn toàn bằng văn phong chỉ đạo công việc.
- Tiêu đề task BẮT ĐẦU bằng động từ hành động: Soạn / Kiểm tra / Hoàn thiện / Liên hệ / Cập nhật / Xử lý / Triển khai...
- Lấy tên người, tên dự án, số liệu, deadline cụ thể từ ghi chú.
- Priority: suy từ từ ngữ khẩn cấp trong ghi chú (gấp/ngay/hôm nay → Cao; bình thường → Trung bình).
- Dùng [placeholder] chỉ khi thông tin thực sự không có.

MỖI PHIÊN BẢN GỒM 6 TRƯỜNG:
1. Tiêu đề task: ngắn, bắt đầu động từ hành động.
2. Mô tả chi tiết: cụ thể phải làm gì.
3. Kết quả bàn giao: người nhận cần nộp/báo cáo lại cái gì.
4. Deadline: từ ghi chú hoặc [deadline cụ thể].
5. Độ ưu tiên: Cao / Trung bình / Thấp.
6. Hỗ trợ: thông tin/tài nguyên bổ sung cho người nhận.

3 PHONG CÁCH:
- "Chi tiết":   đủ 6 trường, hướng dẫn từng bước — dùng cho task phức tạp.
- "Tiêu chuẩn": đủ 6 trường, súc tích, dễ scan — dùng cho task thông thường.
- "Tóm tắt":    chỉ bullet điểm chính, dưới 60 từ — dùng khi cần giao nhanh.

OUTPUT — trả về ĐÚNG định dạng JSON array sau, KHÔNG thêm bất kỳ văn bản nào ngoài JSON: /no_think
[
  {"style": "Chi tiết",    "subject": "Tiêu đề task", "body": "..."},
  {"style": "Tiêu chuẩn", "subject": "Tiêu đề task", "body": "..."},
  {"style": "Tóm tắt",    "subject": "Tiêu đề task", "body": "..."}
]""",

    # ------------------------------------------------------------------
    # NHÃN 3: LÊN LỊCH HỌP
    #
    # Nguyên tắc:
    #   - Output là LỜI MỜI HỌP đầy đủ thông tin, KHÔNG phải email thông thường.
    #   - Xác định loại họp (nội bộ team / với khách hàng / online standup /
    #     board review) để viết đúng format và ngữ điệu.
    #   - Agenda phải được suy ra từ nội dung ghi chú — không viết agenda chung chung.
    #   - "Ngắn gọn" chỉ giữ: thời gian + địa điểm/link + chủ đề + RSVP (≤60 từ).
    # ------------------------------------------------------------------
    "Lên lịch họp": """Bạn là trợ lý lên lịch họp trong ứng dụng NextAct.

NHIỆM VỤ:
Đọc ghi chú của người dùng → xác định LOẠI CUỘC HỌP (nội bộ team? với khách hàng/đối tác? online standup? họp hội đồng?) → viết 3 phiên bản lời mời họp đầy đủ thông tin, sẵn sàng gửi cho người tham dự.

QUY TẮC BẮT BUỘC:
- KHÔNG sao chép câu gốc từ ghi chú — toàn bộ nội dung phải được viết lại theo văn phong lời mời họp chuyên nghiệp.
- Agenda phải SỤY RA từ nội dung ghi chú — không viết agenda chung chung như "thảo luận công việc".
- Lấy thời gian, địa điểm, tên người tham dự từ ghi chú. Dùng [placeholder] khi vắng mặt.
- Mỗi lời mời họp gồm: tiêu đề cuộc họp, thời gian + thời lượng dự kiến, hình thức (trực tiếp tại [địa điểm] / online qua [Google Meet/Zoom — link: placeholder]), mục đích (2-3 câu), agenda (3-5 điểm), chuẩn bị của người tham dự, RSVP.

3 PHONG CÁCH:
- "Chuyên nghiệp": formal, đủ section, kính ngữ — dùng khi họp với đối tác/cấp trên/khách hàng.
- "Thân thiện":    gần gũi, thông tin đầy đủ nhưng không cứng nhắc — dùng cho họp nội bộ team.
- "Ngắn gọn":      chỉ giữ thời gian + địa điểm/link + chủ đề + RSVP, dưới 60 từ.

OUTPUT — trả về ĐÚNG định dạng JSON array sau, KHÔNG thêm bất kỳ văn bản nào ngoài JSON: /no_think
[
  {"style": "Chuyên nghiệp", "subject": "...", "body": "..."},
  {"style": "Thân thiện",    "subject": "...", "body": "..."},
  {"style": "Ngắn gọn",      "subject": "...", "body": "..."}
]""",

    # ------------------------------------------------------------------
    # NHÃN 4: TẠO NHẮC NHỞ
    #
    # Nguyên tắc:
    #   - Output là NHẮC NHỞ CÁ NHÂN cho chính người dùng, KHÔNG phải email gửi ai.
    #   - Xác định đúng ĐỐI TƯỢNG của nhắc nhở: deadline nộp tài liệu? cuộc gọi
    #     cần thực hiện? theo dõi kết quả? uống thuốc? thanh toán?
    #   - "Khẩn cấp" style chỉ dùng khi deadline sắp đến — nhấn mạnh hậu quả nếu trễ.
    #   - calendar_info phục vụ Google Calendar integration — title ≤50 ký tự.
    #   - reminder_minutes: 15 nếu khẩn cấp, 30 mặc định, 60 nếu deadline còn xa.
    # ------------------------------------------------------------------
    "Tạo nhắc nhở": """Bạn là trợ lý tạo nhắc nhở cá nhân trong ứng dụng NextAct.

NHIỆM VỤ:
Đọc ghi chú của người dùng → xác định VIỆC CẦN NHỚ là gì (nộp tài liệu? thực hiện cuộc gọi? thanh toán? theo dõi kết quả? uống thuốc?) → viết 3 phiên bản nhắc nhở với độ khẩn cấp khác nhau.

QUY TẮC BẮT BUỘC:
- Đây là nhắc nhở CHO CHÍNH NGƯỜI DÙNG — không phải email gửi người khác. Viết theo ngôi thứ hai ("Bạn cần...", "Đừng quên...") hoặc dạng thông báo ("Nhắc nhở: ...").
- KHÔNG sao chép câu gốc — toàn bộ phải được diễn đạt lại theo văn phong nhắc nhở súc tích.
- Tiêu đề nhắc nhở ≤10 từ, nêu rõ hành động cụ thể.
- Lấy thời gian deadline, tên việc, tên người liên quan từ ghi chú.

MỖI PHIÊN BẢN GỒM:
1. Tiêu đề: ≤10 từ, bắt đầu động từ hành động.
2. Nội dung: 1-3 câu mô tả việc cần làm.
3. Thời gian: ngày/giờ cụ thể từ ghi chú, hoặc "trước [X] ngày/giờ".
4. Bước tiếp theo: 1-2 hành động cụ thể ngay bây giờ.

3 PHONG CÁCH:
- "Chuyên nghiệp": rõ ràng, lịch sự, phù hợp công việc văn phòng.
- "Thân thiện":    gần gũi, ấm áp, như nhắc từ người bạn.
- "Khẩn cấp":      nhấn mạnh deadline sắp đến, nêu hậu quả nếu trễ — chỉ dùng khi ghi chú có dấu hiệu gấp.

NGOÀI 3 TEMPLATE, hãy trả thêm calendar_info để tích hợp Google Calendar:
- title: tiêu đề sự kiện, ≤50 ký tự.
- description: mô tả ngắn sự kiện.
- reminder_minutes: số nguyên — 15 nếu khẩn cấp, 30 mặc định, 60 nếu deadline còn xa.
- email_subject: tiêu đề email nhắc nhở.

OUTPUT — trả về ĐÚNG định dạng JSON object sau, KHÔNG thêm bất kỳ văn bản nào ngoài JSON: /no_think
{
  "templates": [
    {"style": "Chuyên nghiệp", "subject": "...", "body": "..."},
    {"style": "Thân thiện",    "subject": "...", "body": "..."},
    {"style": "Khẩn cấp",      "subject": "...", "body": "..."}
  ],
  "calendar_info": {
    "title": "...",
    "description": "...",
    "reminder_minutes": 30,
    "email_subject": "..."
  }
}""",

    # ------------------------------------------------------------------
    # NHÃN 5: SOẠN BÁO CÁO
    #
    # Nguyên tắc:
    #   - Output là CẤU TRÚC BÁO CÁO, KHÔNG phải email.
    #   - Xác định đúng LOẠI báo cáo (tiến độ dự án? KPI/doanh thu? sự cố?
    #     đề xuất? biên bản họp?) để chọn đúng template.
    #   - 3 style khác nhau về CẤU TRÚC TRÌNH BÀY:
    #     "Đầy đủ"       = heading + 5 section → báo cáo chính thức.
    #     "Tóm tắt"      = bullet snapshot → báo cáo nhanh / status update.
    #     "Theo form chuẩn" = form điền sẵn các trường → báo cáo định kỳ.
    #   - Dùng [placeholder] cho số liệu/tên cụ thể không có trong ghi chú.
    #   - Tiêu đề báo cáo phải nêu rõ: loại + đối tượng + kỳ báo cáo.
    # ------------------------------------------------------------------
    "Soạn báo cáo": """Bạn là trợ lý soạn báo cáo trong ứng dụng NextAct.

NHIỆM VỤ:
Đọc ghi chú của người dùng → xác định LOẠI BÁO CÁO (tiến độ dự án? KPI/doanh thu? sự cố/lỗi? đề xuất kế hoạch? biên bản cuộc họp?) → tạo 3 phiên bản cấu trúc báo cáo với định dạng trình bày khác nhau.

QUY TẮC BẮT BUỘC:
- Đây là BÁO CÁO, không phải email — không có lời chào/kết email.
- KHÔNG sao chép câu gốc từ ghi chú — tất cả nội dung phải được tái cấu trúc theo văn phong báo cáo chuyên nghiệp.
- Tiêu đề báo cáo phải nêu rõ: loại báo cáo + đối tượng/dự án + kỳ báo cáo.
- Lấy số liệu, tên dự án, tên người phụ trách từ ghi chú. Dùng [placeholder] khi vắng mặt.

3 PHONG CÁCH:
- "Đầy đủ" (báo cáo chính thức — đủ 5 section):
  I. TỔNG QUAN — mục tiêu, phạm vi, kỳ báo cáo
  II. KẾT QUẢ / TÌNH TRẠNG — kết quả chính, % hoàn thành, chỉ số đo lường
  III. VẤN ĐỀ & RỦI RO — điểm tắc nghẽn, rủi ro (nếu có)
  IV. ĐỀ XUẤT HÀNH ĐỘNG TIẾP THEO
  V. KẾT LUẬN

- "Tóm tắt" (bullet snapshot — báo cáo nhanh):
  • Tình trạng: [một dòng trạng thái]
  • Đã hoàn thành: ...
  • Đang thực hiện: ...
  • Cần hỗ trợ: ...
  • Bước tiếp theo: ...
  • Deadline: ...

- "Theo form chuẩn" (form điền sẵn — báo cáo định kỳ):
  Người báo cáo: [Tên]
  Phòng ban / Dự án: [Tên]
  Kỳ báo cáo: [Ngày]
  Nội dung: [nội dung chi tiết phù hợp loại báo cáo]
  Đề xuất: [hành động tiếp theo]

OUTPUT — trả về ĐÚNG định dạng JSON array sau, KHÔNG thêm bất kỳ văn bản nào ngoài JSON: /no_think
[
  {"style": "Đầy đủ",          "subject": "Tiêu đề báo cáo", "body": "..."},
  {"style": "Tóm tắt",         "subject": "Tiêu đề báo cáo", "body": "..."},
  {"style": "Theo form chuẩn", "subject": "Tiêu đề báo cáo", "body": "..."}
]""",

    # ------------------------------------------------------------------
    # NHÃN 6: PHÊ DUYỆT
    #
    # Nguyên tắc:
    #   - 3 style tương ứng 3 KẾT QUẢ PHÁN QUYẾT hoàn toàn khác nhau:
    #     "Chấp thuận"   = phê duyệt + điều kiện + bước tiếp theo.
    #     "Từ chối"      = từ chối + lý do khách quan + điều kiện tái nộp.
    #     "Cần bổ sung"  = hoãn + danh sách thiếu + hướng dẫn bổ sung.
    #   - Xác định đúng ĐỐI TƯỢNG phê duyệt: đề xuất ngân sách? xin nghỉ phép?
    #     đề xuất dự án? hồ sơ ứng viên? yêu cầu thay đổi?
    #   - Mỗi phản hồi ≤200 từ, dứt khoát — không mơ hồ, không cảm xúc.
    #   - "Từ chối" phải có lý do cụ thể, khách quan — không phán xét cá nhân.
    #   - "Cần bổ sung" phải liệt kê CỤ THỂ những gì còn thiếu — không viết chung chung.
    # ------------------------------------------------------------------
    "Phê duyệt": """Bạn là trợ lý phê duyệt điều hành trong ứng dụng NextAct.

NHIỆM VỤ:
Đọc ghi chú của người dùng → xác định ĐỐI TƯỢNG ĐANG ĐƯỢC PHÊ DUYỆT (đề xuất ngân sách? đơn xin nghỉ phép? đề xuất dự án? hồ sơ ứng viên? yêu cầu thay đổi?) → viết 3 phản hồi phê duyệt với kết quả phán quyết khác nhau.

QUY TẮC BẮT BUỘC:
- KHÔNG sao chép câu gốc từ ghi chú — toàn bộ phải được viết lại theo văn phong phản hồi điều hành dứt khoát.
- Xác định rõ TÊN ĐỐI TƯỢNG được phê duyệt để câu mở đầu mỗi phản hồi dứt khoát ngay.
- Lấy tên người, tên đề xuất, số liệu, ngày tháng từ ghi chú. Dùng [placeholder] khi vắng mặt.
- Mỗi phản hồi ≤200 từ, tone chuyên nghiệp và tôn trọng xuyên suốt.

3 PHONG CÁCH (3 kết quả phán quyết HOÀN TOÀN KHÁC NHAU):

"Chấp thuận" — phê duyệt:
- Câu mở đầu: CHẤP THUẬN [tên đề xuất/yêu cầu]
- Điều kiện đi kèm nếu có
- Bước tiếp theo cho người nộp
- Deadline thực hiện
- Ký tên: [Tên người phê duyệt]

"Từ chối" — không phê duyệt:
- Câu mở đầu: CHƯA PHÊ DUYỆT [tên đề xuất/yêu cầu]
- Lý do cụ thể, khách quan (không phán xét cá nhân)
- Điều kiện để nộp lại thành công (nếu có)
- Giải pháp thay thế (nếu có)
- Tone: kiên quyết nhưng tôn trọng

"Cần bổ sung" — tạm hoãn chờ thêm thông tin:
- Xác nhận đã nhận đề xuất/yêu cầu
- Danh sách CỤ THỂ những thông tin/tài liệu còn thiếu
- Hướng dẫn cách bổ sung và gửi lại
- Deadline bổ sung để kịp tiến độ xét duyệt

OUTPUT — trả về ĐÚNG định dạng JSON array sau, KHÔNG thêm bất kỳ văn bản nào ngoài JSON: /no_think
[
  {"style": "Chấp thuận",   "subject": "...", "body": "..."},
  {"style": "Từ chối",      "subject": "...", "body": "..."},
  {"style": "Cần bổ sung",  "subject": "...", "body": "..."}
]""",

}

# Prompt mặc định — fallback cho nhãn không có trong danh sách
DEFAULT_SYSTEM_PROMPT = """Bạn là trợ lý gợi ý nội dung trong ứng dụng NextAct.

NHIỆM VỤ:
Đọc ghi chú → xác định mục đích thực sự → viết 3 phiên bản nội dung KHÁC NHAU.

QUY TẮC: KHÔNG sao chép câu gốc. Lấy thông tin cụ thể từ ghi chú. Dùng [placeholder] chỉ khi thiếu.

OUTPUT — trả về ĐÚNG định dạng JSON array, KHÔNG thêm văn bản nào khác: /no_think
[
  {"style": "Chuyên nghiệp", "subject": "...", "body": "..."},
  {"style": "Thân thiện",    "subject": "...", "body": "..."},
  {"style": "Ngắn gọn",      "subject": "...", "body": "..."}
]"""


# =====================================================================
# SYSTEM PROMPT: TÓM TẮT CUỘC HỌP / ĐOẠN HỘI THOẠI
# Áp dụng cho endpoint /nextact/summarize
# Trích xuất: summary, action items, JSON entity object
# =====================================================================
SUMMARIZE_SYSTEM_PROMPT = """Bạn là AI cốt lõi của NextAct, ứng dụng quản lý công việc thông minh.
Nhiệm vụ: phân tích biên bản cuộc họp hoặc đoạn hội thoại tiếng Việt, tóm tắt nội dung và trích xuất thực thể hành động chính xác.

QUY TẮC NGHIÊM NGẶT:
1. Chỉ dựa vào nội dung văn bản được cung cấp. Tuyệt đối KHÔNG bịa ngày tháng, tên người, hay nhiệm vụ.
2. Nếu một trường (Location, Time) không có trong văn bản → đặt "Không xác định".
3. Nhóm action items theo người/vai trò chịu trách nhiệm.
4. Nhãn hợp lệ cho tasks: "Gửi/Trả lời email", "Lên lịch họp", "Tạo nhắc nhở", "Soạn báo cáo", "Giao việc", "Phê duyệt", "Khác".
5. Priority: 1=thấp, 2=trung bình, 3=cao — suy từ ngôn ngữ khẩn cấp trong văn bản.
6. Trường deadline: "YYYY-MM-DD" nếu có ngày cụ thể, ngược lại null.

OUTPUT — trả về ĐÚNG định dạng JSON sau, KHÔNG markdown, KHÔNG giải thích: /no_think
{
  "summary": ["Ý chính 1", "Ý chính 2", "Ý chính 3"],
  "labels":  ["nhãn 1", "nhãn 2"],
  "ner": {
    "actions": ["cụm động từ/hành động được trích xuất"],
    "people":  ["tên người hoặc vai trò"],
    "times":   ["biểu thức thời gian, deadline"],
    "places":  ["địa điểm, nền tảng, phòng họp"]
  },
  "action_items": [
    {
      "person":   "Họ tên hoặc vai trò",
      "action":   "Động từ mệnh lệnh + mô tả nhiệm vụ",
      "time":     "Khi nào cần hoàn thành",
      "location": "Phòng / Zoom / Slack / v.v."
    }
  ],
  "tasks": [
    {
      "title":       "Tiêu đề task ngắn gọn, bắt đầu động từ mệnh lệnh",
      "action_type": "Nhãn hành động",
      "priority":    2,
      "deadline":    "YYYY-MM-DD hoặc null",
      "reason":      "Lý do ngắn trích từ biên bản"
    }
  ]
}"""

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class TodoTextRequest(BaseModel):
    text: str


class ChatRequest(BaseModel):
    task_title: str
    task_description: str = ""
    due_date: str = ""
    message: str


class SuggestRequest(BaseModel):
    text: str
    mode: str = "single"


class SuggestionItem(BaseModel):
    id: str
    action_type: str
    title: str
    deadline: Optional[str] = None
    suggested_priority: int = 2
    confidence: float = 0.0
    evidence: str = ""


def split_actions(text: str) -> List[str]:
    """Tách nội dung thành nhiều hành động"""
    chunks = re.split(r'[\n\.;!]+', text)
    chunks = [c.strip() for c in chunks if c.strip()]
    return [c for c in chunks if len(c) >= 3]


@router.post("/nextact/classify")
def classify_todo(request: TodoTextRequest):
    """Phân loại công việc dựa trên văn bản — trả về confidence thật từ softmax"""
    try:
        if not _is_meaningful_text(request.text):
            return {
                "text":             request.text,
                "category":         None,
                "confidence":       0,
                "deadline":         None,
                "deadline_display": "Không có",
                "probabilities":    {},
            }

        ai_result = ai_service.predict(request.text)
        raw_label = ai_result["label"]
        conf      = ai_result["confidence"]

        label = raw_label if (conf >= CONFIDENCE_THRESHOLD and raw_label in VALID_LABEL_SET) else None

        return {
            "text":             request.text,
            "category":         label,
            "confidence":       conf,
            "deadline":         ai_result["deadline"],
            "deadline_display": ai_result["deadline_display"],
            "probabilities":    {},
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/nextact/suggest")
def suggest_todo(request: SuggestRequest, db=Depends(get_db), req: Request = None):
    text = (request.text or "").strip()
    if len(text) < 3:
        return {
            "text": text,
            "category": "",
            "confidence": 0,
            "deadline": None,
            "suggested_actions": [],
            "suggested_priority": 2,
            "reason": [],
            "suggestions": [],
            "calendar_link": None
        }

    is_bulk = (request.mode == "bulk") or ("\n" in text)
    items = split_actions(text) if is_bulk else [text]

    suggestions: List[Dict[str, Any]] = []

    for s in items[:10]:
        if not _is_meaningful_text(s):
            suggestions.append({
                "id": str(uuid.uuid4()),
                "action_type": None,
                "title": s[:80],
                "deadline": None,
                "deadline_display": "Không có",
                "suggested_priority": 1,
                "confidence": 0,
                "evidence": s
            })
            continue

        ai_result  = ai_service.predict(s)
        raw_label  = ai_result['label']
        pred_conf  = ai_result['confidence']
        deadline_str     = ai_result['deadline']
        deadline_display = ai_result['deadline_display']

        pred_label = raw_label if (pred_conf >= CONFIDENCE_THRESHOLD and raw_label in VALID_LABEL_SET) else None

        if deadline_str or pred_conf >= 75:
            suggested_priority = 3
        elif pred_conf >= 50:
            suggested_priority = 2
        else:
            suggested_priority = 1

        suggestions.append({
            "id": str(uuid.uuid4()),
            "action_type": pred_label,
            "title": s[:80],
            "deadline": deadline_str,
            "deadline_display": deadline_display,
            "suggested_priority": suggested_priority,
            "confidence": round(pred_conf, 2),
            "evidence": s
        })

    top = suggestions[0] if suggestions else None

    # ====== LƯU VÀO BẢNG SUGGESTIONS (nếu có user) ======
    if top and req:
        try:
            user_id = get_current_user(req)
            deadline_dt = None
            if top.get("deadline"):
                try:
                    deadline_dt = datetime.fromisoformat(top["deadline"])
                except (ValueError, TypeError):
                    pass

            new_suggestion = Suggestion(
                user_id=user_id,
                original_text=text,
                action_type=top["action_type"],
                confidence=top["confidence"],
                title=top["title"],
                suggested_priority=top["suggested_priority"],
                deadline=deadline_dt,
                status="pending"
            )
            db.add(new_suggestion)
            db.commit()
        except Exception:
            db.rollback()

    # ====== TẠO GOOGLE CALENDAR EVENT ======
    calendar_link = None
    if top and top.get("action_type") in ['Lên lịch họp', 'Tạo nhắc nhở'] and top.get("deadline"):
        calendar_result = add_event_to_calendar(
            title=top["title"],
            date_str=top["deadline"],
            description=f"Được tạo tự động từ AI NextAct\nNội dung gốc: {text}"
        )
        if calendar_result.get("success"):
            calendar_link = calendar_result.get("htmlLink")

    return {
        "text": text,
        "category": top["action_type"] if top else "",
        "confidence": top["confidence"] if top else 0,
        "deadline": top["deadline"] if top else None,
        "deadline_display": top["deadline_display"] if top else "Không có",
        "suggested_actions": [f"Tạo việc: {top['title']}"] if top else [],
        "suggested_priority": top["suggested_priority"] if top else 2,
        "reason": ["Tách từ nội dung nhập vào", "Dựa trên nhãn dự đoán + hạn chót"] if top else [],
        "suggestions": suggestions,
        "calendar_link": calendar_link
    }


# =====================================================================
# SCHEMA CHO LLAMA SUGGEST (thay thế groq-suggest)
# =====================================================================
class LlamaSuggestRequest(BaseModel):
    text: str
    category: str
    deadline_display: str = ""


def _build_user_prompt(text: str, category: str, deadline_display: str = "") -> str:
    """
    Xây dựng user prompt chuẩn cho Qwen3 — áp dụng đồng nhất cho
    llama_suggest và groq_suggest_compat.

    Nguyên tắc thiết kế:
    - Cung cấp đủ ngữ cảnh để model ĐỊNH DANH trước khi sinh nội dung:
        + Đối tượng là ai? Mục đích thực sự là gì? Tone phù hợp là gì?
    - Nhấn mạnh lại "KHÔNG sao chép" và "lấy thông tin cụ thể" ngay trong
      user prompt (không chỉ system prompt) để model nhỏ 0.6B nhớ constraint.
    - Dòng deadline (nếu có) được đặt nổi bật ngay trên câu hỏi để model
      không bỏ qua thông tin thời gian quan trọng.
    - Kết thúc bằng yêu cầu JSON thuần để tránh model sinh mào đầu thừa.
    """
    deadline_line = (
        f"\nThời gian được đề cập: {deadline_display}"
        if deadline_display else ""
    )

    return f'''
Ghi chú của người dùng:
"{text}"{deadline_line}

Nhãn AI phân loại: "{category}"

YÊU CẦU QUAN TRỌNG:
- Đọc kỹ và hiểu đúng chủ đề, mục đích, bối cảnh của ghi chú.
- Sinh ra 3 template nội dung hoàn toàn mới, mỗi template phải khác cấu trúc câu, khác cách diễn đạt, không lặp lại ý hoặc copy nguyên văn input.
- Nội dung phải bám sát chủ đề/ngữ cảnh, không được lạc đề, không được tạo nội dung chung chung hoặc không liên quan.
- Tuyệt đối KHÔNG sử dụng form mẫu cố định rồi chỉ thay input vào, mà phải tự sáng tạo lại toàn bộ nội dung cho phù hợp từng trường hợp.
- Lấy thông tin cụ thể từ ghi chú (tên người, ngày tháng, số liệu, tên sản phẩm/dự án). Dùng [placeholder] chỉ khi thông tin thực sự không có.
- KHÔNG sao chép, không paraphrase, không giải thích ngoài lề.

Trả về JSON thuần túy đúng schema của nhãn "{category}" (không markdown, không backtick, không giải thích thêm).
'''


@router.post("/nextact/llama-suggest")
def llama_suggest(req: LlamaSuggestRequest):
    """
    Nhận nhãn + text + deadline từ frontend.
    Gọi Qwen3 qua ngrok với SYSTEM PROMPT riêng cho từng nhãn.
    Trả về JSON: {"templates": [...], "label": "...", "calendar_info": {...}}
    """
    system_prompt = LABEL_SYSTEM_PROMPTS.get(req.category, DEFAULT_SYSTEM_PROMPT)
    user_prompt   = _build_user_prompt(req.text, req.category, req.deadline_display)

    raw = _call_llama(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.7,    # Unsloth spec: 0.7 cho enable_thinking=False
        max_tokens=1500,
    )

    clean = _strip_json_fence(raw)

    try:
        parsed = json.loads(clean)
    except json.JSONDecodeError as e:
        print(f"[llama-suggest] JSON parse error. Raw snippet: {raw[:400]}")
        raise HTTPException(status_code=500, detail=f"Lỗi parse JSON từ Qwen3: {e}")

    # Hỗ trợ 2 format output:
    #   - Array  [...] : 5 nhãn (email, giao việc, họp, báo cáo, phê duyệt)
    #   - Object {...} : nhãn "Tạo nhắc nhở" có thêm calendar_info
    if isinstance(parsed, list):
        templates     = parsed
        calendar_info = None
        extra         = {}
    elif isinstance(parsed, dict):
        templates     = parsed.get("templates") or parsed.get("items") or []
        calendar_info = parsed.get("calendar_info")
        extra         = {k: v for k, v in parsed.items()
                         if k not in ("templates", "items", "calendar_info")}
        if not templates and any(k in parsed for k in ("style", "subject", "body")):
            templates = [parsed]
    else:
        raise HTTPException(status_code=500, detail="Qwen3 trả về dữ liệu không hợp lệ")

    if not templates:
        raise HTTPException(status_code=500, detail="Qwen3 trả về danh sách template rỗng")

    result = {"templates": templates, "label": req.category}
    if calendar_info:
        result["calendar_info"] = calendar_info
    result.update(extra)
    return result


# Alias để tương thích với frontend cũ đang gọi /nextact/groq-suggest
# (đổi tên endpoint từng bước — giữ route cũ trỏ về handler mới)
class GroqSuggestRequest(BaseModel):
    text: str
    category: str
    deadline_display: str = ""


@router.post("/nextact/groq-suggest")
def groq_suggest_compat(req: GroqSuggestRequest):
    """
    Alias tương thích ngược — frontend cũ vẫn gọi /groq-suggest,
    handler thực sự là llama_suggest (Qwen3 local).
    """
    return llama_suggest(LlamaSuggestRequest(
        text=req.text,
        category=req.category,
        deadline_display=req.deadline_display,
    ))


@router.post("/nextact/create_task")
async def create_task(request: Request, payload: dict = Body(...), db=Depends(get_db)):
    user_input   = payload.get("title")
    is_quick_add = payload.get("is_quick_add", False)
    priority_val = payload.get("priority", 2)
    due_date_str = payload.get("due_date")
    content_val  = payload.get("content")
    project_id   = payload.get("project_id")

    ai_result = ai_service.predict(user_input)
    raw_label = ai_result.get("label")
    raw_conf  = ai_result.get("confidence", 0)

    label = raw_label if (raw_conf >= CONFIDENCE_THRESHOLD and raw_label in VALID_LABEL_SET) else None

    due_date = None
    if due_date_str:
        try:
            due_date = datetime.fromisoformat(str(due_date_str))
        except (ValueError, TypeError):
            try:
                due_date = datetime.fromisoformat(str(due_date_str)[:10])
            except (ValueError, TypeError):
                due_date = None

    if not due_date:
        deadline_str = ai_result.get("deadline")
        if deadline_str:
            try:
                due_date = datetime.fromisoformat(deadline_str)
            except (ValueError, TypeError):
                due_date = None

    user_id = get_current_user(request)
    new_note = Note(
        title=user_input,
        label=label,
        content=content_val,
        due_date=due_date,
        priority=priority_val,
        is_quick_add=is_quick_add,
        user_id=user_id,
        project_id=int(project_id) if project_id else None,
    )
    db.add(new_note)
    db.commit()
    db.refresh(new_note)

    return {"status": "success", "id": new_note.id, "project_id": new_note.project_id}


# =====================================================================
# SUMMARIZE: Tóm tắt hội thoại / ghi chú cuộc họp
# Dùng Qwen3 (qua ngrok) thay vì Groq
# =====================================================================
class SummarizeRequest(BaseModel):
    title: str = ""
    content: str  # Đoạn hội thoại / văn bản dài


class SummarizeTaskItem(BaseModel):
    title: str
    action_type: str
    priority: int = 2
    deadline: Optional[str] = None
    reason: str = ""


@router.post("/nextact/summarize")
def summarize_conversation(req: SummarizeRequest):
    """
    Tóm tắt hội thoại / ghi chú cuộc họp dài bằng Qwen3 (ngrok).
    Trả về:
    - summary      : danh sách ý chính (3–5 câu)
    - labels       : nhãn gán cho nội dung
    - ner          : entities (people, times, places, actions)
    - action_items : việc cần làm nhóm theo người chịu trách nhiệm
    - tasks        : 2–4 task được đề xuất tạo trong NextAct
    """
    content = (req.content or "").strip()
    if len(content) < 10:
        raise HTTPException(status_code=400, detail="Nội dung quá ngắn để tóm tắt")

    title_line = f"Tiêu đề / chủ đề: {req.title.strip()}\n" if req.title.strip() else ""

    user_prompt = f"""{title_line}Nội dung hội thoại / ghi chú cuộc họp:
---
{content}
---

Hãy phân tích toàn bộ đoạn văn bản trên và trả về JSON theo đúng schema đã định nghĩa.
Lưu ý:
- summary: tối đa 5 ý chính, mỗi ý 1 câu ngắn gọn bằng tiếng Việt.
- labels: gán ĐỦ tất cả nhãn liên quan — không bỏ sót.
- action_items: nhóm theo người/vai trò chịu trách nhiệm.
- tasks: mỗi công việc cụ thể → 1 task riêng, tối đa 4 tasks.
- Chỉ trả về JSON thuần túy, không markdown, không giải thích."""

    raw = _call_llama(
        system_prompt=SUMMARIZE_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=0.2,   # Thấp hơn để output ổn định, bám sát nội dung
        max_tokens=2000,
    )

    clean = _strip_json_fence(raw)

    try:
        result = json.loads(clean)
    except json.JSONDecodeError as e:
        print(f"[summarize] JSON parse error. Raw snippet: {raw[:400]}")
        raise HTTPException(status_code=500, detail=f"Lỗi parse kết quả AI: {e}")

    return {
        "summary":      result.get("summary", []),
        "labels":       result.get("labels", []),
        "ner":          result.get("ner", {"actions": [], "people": [], "times": [], "places": []}),
        "action_items": result.get("action_items", []),
        "tasks":        result.get("tasks", []),
    }


# =====================================================================
# CREATE MULTI TASKS: Tạo nhiều task từ kết quả tóm tắt
# =====================================================================
class CreateMultiTasksRequest(BaseModel):
    tasks: List[Dict[str, Any]]
    source_title: str = ""
    source_content: str = ""


@router.post("/nextact/create_multi_tasks")
async def create_multi_tasks(request: Request, payload: CreateMultiTasksRequest, db=Depends(get_db)):
    """Tạo nhiều task cùng lúc từ kết quả tóm tắt AI"""
    user_id = get_current_user(request)
    created = []

    for task_data in payload.tasks[:5]:
        title = task_data.get("title", "").strip()
        if not title:
            continue

        due_date = None
        deadline_str = task_data.get("deadline")
        if deadline_str and deadline_str != "null":
            try:
                due_date = datetime.fromisoformat(str(deadline_str)[:10])
            except (ValueError, TypeError):
                due_date = None

        priority    = int(task_data.get("priority", 2))
        action_type = task_data.get("action_type", "Khác")

        reason = task_data.get("reason", "")
        content_parts = []
        if reason:
            content_parts.append(f"Lý do: {reason}")
        if payload.source_title:
            content_parts.append(f"Nguồn: {payload.source_title}")
        content_val = "\n".join(content_parts) if content_parts else None

        new_note = Note(
            user_id=user_id,
            title=title,
            content=content_val,
            status="todo",
            priority=priority,
            due_date=due_date,
            label=action_type,
            is_quick_add=False
        )
        db.add(new_note)
        db.flush()
        created.append({"id": new_note.id, "title": title})

    db.commit()
    return {"created": created, "count": len(created)}


@router.get("/nextact/models")
def list_models():
    """Debug: trả về thông tin model đang dùng"""
    return {
        "backend":    "Qwen3 via ngrok",
        "model":      LLAMA_MODEL,
        "server_url": LLAMA_SERVER_URL,
    }


class FeedbackRequest(BaseModel):
    suggestion_id: str
    action: str  # ACCEPT | EDIT | REJECT
    edited_fields: Optional[Dict[str, Any]] = None


@router.post("/nextact/feedback")
def save_feedback(request: FeedbackRequest, db=Depends(get_db)):
    """Lưu feedback — ghi JSONL (cho training) + update DB nếu có id số"""
    base_dir = Path(__file__).resolve().parent.parent.parent
    fp = base_dir / "model" / "feedback_log.jsonl"
    payload = {
        "suggestion_id": request.suggestion_id,
        "action":        request.action,
        "edited_fields": request.edited_fields or {},
        "ts":            datetime.now().isoformat()
    }
    try:
        fp.parent.mkdir(parents=True, exist_ok=True)
        with open(fp, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[Feedback] Lỗi ghi log: {e}")

    try:
        suggestion_id_int = int(request.suggestion_id)
        suggestion = db.query(Suggestion).filter(Suggestion.id == suggestion_id_int).first()
        if suggestion:
            action_map = {"ACCEPT": "accepted", "REJECT": "rejected", "EDIT": "edited"}
            suggestion.status = action_map.get(request.action, "pending")
            suggestion.feedback_action = request.action
            if request.edited_fields:
                if "title" in request.edited_fields:
                    suggestion.edited_title = request.edited_fields["title"]
                if "priority" in request.edited_fields:
                    suggestion.edited_priority = request.edited_fields["priority"]
            db.commit()
    except (ValueError, TypeError):
        pass
    except Exception as e:
        print(f"[Feedback] Lỗi update DB: {e}")
        db.rollback()

    return {"ok": True}


# =====================================================================
# CHAT: Trợ lý ảo trả lời câu hỏi liên quan đến task cụ thể
# Vẫn dùng Gemini cho tính năng chat hội thoại dài (stateful)
# =====================================================================
@router.post("/nextact/chat")
def chat_with_assistant(request: ChatRequest):
    """
    Trợ lý ảo trả lời câu hỏi về một task cụ thể.
    Ưu tiên Gemini nếu có API key; fallback về Qwen3 qua ngrok.
    """
    if GEMINI_API_KEY:
        return _chat_gemini(request)
    return _chat_llama(request)


def _build_chat_system_prompt(request: ChatRequest) -> str:
    return f"""Bạn là trợ lý ảo thông minh trong ứng dụng NextAct, hỗ trợ người dùng quản lý công việc hiệu quả.

Thông tin task hiện tại:
- Tiêu đề   : {request.task_title}
- Mô tả     : {request.task_description or '(Không có mô tả)'}
- Hạn chót  : {request.due_date or '(Không có hạn chót)'}

Vai trò của bạn:
1. Trả lời câu hỏi liên quan trực tiếp đến task này (cách thực hiện, ưu tiên, chia nhỏ công việc...).
2. Gợi ý hành động tiếp theo cụ thể, thiết thực.
3. Tóm tắt hoặc giải thích nội dung phức tạp nếu được yêu cầu.

Định dạng trả lời:
TÓM TẮT: [1 câu tóm tắt câu trả lời]
HIGHLIGHTS: [điểm quan trọng 1; điểm quan trọng 2; ...]
REPLY: [câu trả lời đầy đủ bằng tiếng Việt]"""


def _parse_chat_reply(raw: str) -> Dict[str, Any]:
    summary    = ""
    highlights = []
    reply      = raw
    try:
        for line in raw.split('\n'):
            if line.startswith('TÓM TẮT:'):
                summary = line.replace('TÓM TẮT:', '').strip()
            elif line.startswith('HIGHLIGHTS:'):
                hl_text    = line.replace('HIGHLIGHTS:', '').strip()
                highlights = [h.strip() for h in hl_text.split(';') if h.strip()]
            elif line.startswith('REPLY:'):
                reply = line.replace('REPLY:', '').strip()
                break
    except Exception:
        pass
    return {"reply": reply, "summary": summary, "highlights": highlights, "success": True}


def _chat_gemini(request: ChatRequest) -> Dict[str, Any]:
    system_prompt = _build_chat_system_prompt(request)
    url = (f"https://generativelanguage.googleapis.com/v1/models/"
           f"gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}")
    payload = {
        "contents": [{
            "parts": [{"text": f"{system_prompt}\n\nCâu hỏi của người dùng: {request.message}"}]
        }]
    }
    try:
        response = requests.post(url, json=payload, timeout=30)
        result   = response.json()
        if response.status_code != 200:
            err_status = result.get("error", {}).get("status", "")
            if response.status_code in (503, 429) or err_status == "UNAVAILABLE":
                return {"reply": "Trợ lý AI tạm thời không khả dụng. Vui lòng thử lại sau.",
                        "summary": "", "highlights": [], "success": False}
            raise HTTPException(status_code=400, detail=f"Gemini API error: {result}")
        raw_reply = result['candidates'][0]['content']['parts'][0]['text']
        return _parse_chat_reply(raw_reply)
    except HTTPException:
        raise
    except Exception as e:
        print(f"[chat/gemini] ERROR: {e}")
        raise HTTPException(status_code=400, detail=f"Chat error: {e}")


def _chat_llama(request: ChatRequest) -> Dict[str, Any]:
    system_prompt = _build_chat_system_prompt(request)
    try:
        raw = _call_llama(
            system_prompt=system_prompt,
            user_prompt=f"Câu hỏi của người dùng: {request.message}",
            temperature=0.5,
            max_tokens=800,
        )
        return _parse_chat_reply(raw)
    except HTTPException:
        raise
    except Exception as e:
        print(f"[chat/llama] ERROR: {e}")
        raise HTTPException(status_code=400, detail=f"Chat error: {e}")


@router.post("/ai/actions")
def get_actions(input_text: str):
    result  = ai_service.predict(input_text)
    actions = ai_service.suggest_actions(input_text)
    return {
        "label":      result["label"],
        "confidence": result["confidence"],
        "deadline":   result["deadline"],
        "actions":    actions["actions"] if actions else []
    }


# ===== SUGGESTIONS CRUD =====
@router.get("/nextact/suggestions")
def get_suggestions(request: Request, status: str = None, db=Depends(get_db)):
    """Lấy danh sách gợi ý của user"""
    user_id = get_current_user(request)
    query   = db.query(Suggestion).filter(Suggestion.user_id == user_id)
    if status:
        query = query.filter(Suggestion.status == status)
    suggestions = query.order_by(Suggestion.created_at.desc()).all()
    return suggestions


@router.put("/nextact/suggestions/{suggestion_id}/status")
def update_suggestion_status(
    suggestion_id: int,
    request: Request,
    payload: dict = Body(...),
    db=Depends(get_db)
):
    """Cập nhật trạng thái gợi ý (accept/reject/edit)"""
    user_id    = get_current_user(request)
    suggestion = db.query(Suggestion).filter(
        Suggestion.id == suggestion_id,
        Suggestion.user_id == user_id
    ).first()

    if not suggestion:
        raise HTTPException(status_code=404, detail="Không tìm thấy gợi ý")

    new_status = payload.get("status")
    if new_status not in ["pending", "accepted", "rejected", "edited"]:
        raise HTTPException(status_code=400, detail="Trạng thái không hợp lệ")

    suggestion.status          = new_status
    suggestion.feedback_action = new_status.upper()

    if payload.get("edited_title"):
        suggestion.edited_title = payload["edited_title"]
    if payload.get("edited_priority"):
        suggestion.edited_priority = payload["edited_priority"]

    db.commit()
    db.refresh(suggestion)
    return {"ok": True, "status": suggestion.status}