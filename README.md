# NextAct Todo App

Ứng dụng quản lý công việc và ghi chú thông minh với tính năng tự động ưu tiên hóa nhờ AI.

## 🎯 Tính Năng

- **Xác thực người dùng**: Đăng ký, đăng nhập an toàn với mã hóa password
- **Quản lý ghi chú**: Tạo, chỉnh sửa, xóa các ghi chú công việc
- **Ưu tiên hóa thông minh**: Sử dụng mô hình ML để tự động gợi ý mức độ ưu tiên
- **Theo dõi trạng thái**: Đánh dấu công việc là "todo", "doing", "done"
- **Hạn chót**: Đặt ngày hạn cho các công việc
- **Thêm nhanh**: Tính năng thêm công việc nhanh chóng
- **Hỗ trợ AI**: Tích hợp Google Generative AI cho các gợi ý thêm

## 🛠️ Công Nghệ

### Backend
- **FastAPI**: Framework web hiện đại, tính năng cao
- **SQLAlchemy**: ORM cho cơ sở dữ liệu
- **PostgreSQL**: Cơ sở dữ liệu quan hệ
- **JWT**: Xác thực token
- **Passlib**: Mã hóa password an toàn
- **Scikit-learn**: Mô hình machine learning

### Frontend
- HTML5
- CSS3
- JavaScript (Vanilla)

### AI & ML
- **Google Generative AI**: Hỗ trợ AI thông minh
- **Joblib**: Lưu và tải mô hình ML

## 📋 Yêu Cầu

- Python 3.8+
- PostgreSQL
- pip (Package manager)

## 🚀 Cài Đặt

### 1. Clone repository
```bash
git clone <repository-url>
cd nextact-todo
```

### 2. Tạo virtual environment
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### 4. Cấu hình cơ sở dữ liệu

Tạo cơ sở dữ liệu PostgreSQL và chạy schema:
```bash
psql -U <username> -d <database_name> -f database/schema.sql
```
nextact_todo_db
### 5. Cấu hình biến môi trường

Tạo file `.env` trong thư mục `backend/`:
```
DATABASE_URL=postgresql://username:password@localhost/database_name
SECRET_KEY=your-secret-key-here
GOOGLE_API_KEY=your-google-api-key
```

### 6. Chạy ứng dụng
```bash
uvicorn backend.app.main:app --reload
```

Ứng dụng sẽ khả dụng tại: `http://localhost:8000`

## 📁 Cấu Trúc Thư Mục

```
nextact-todo/
├── backend/
│   └── app/
│       ├── main.py           # Điểm vào chính
│       ├── auth.py           # Xác thực & đăng nhập
│       ├── notes.py          # Quản lý ghi chú
│       ├── nextact.py        # Ưu tiên hóa AI
│       ├── database.py       # Kết nối DB
│       ├── models.py         # Mô hình SQLAlchemy
│       └── schemas.py        # Pydantic schemas
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css
│   │   └── js/
│   │       └── app.js
│   └── templates/
│       ├── login.html
│       ├── register.html
│       └── dashboard.html
├── model/
│   ├── nextact_model.joblib
│   ├── train_nextact_model.py
│   └── nextact_todo_dataset_2000_diverse_vi.csv
├── database/
│   └── schema.sql
├── requirements.txt
└── README.md
```

## 🔌 API Endpoints

### Xác Thực
- `POST /api/auth/register` - Đăng ký tài khoản mới
- `POST /api/auth/login` - Đăng nhập
- `POST /api/auth/logout` - Đăng xuất

### Ghi Chú
- `GET /api/notes` - Lấy danh sách ghi chú
- `POST /api/notes` - Tạo ghi chú mới
- `PUT /api/notes/{id}` - Cập nhật ghi chú
- `DELETE /api/notes/{id}` - Xóa ghi chú

### Ưu Tiên Hóa
- `POST /api/nextact/predict` - Dự đoán mức độ ưu tiên

## 📊 Mô Hình Machine Learning

### Giới Thiệu
Mô hình được huấn luyện để **phân loại loại công việc** dựa trên nội dung văn bản tiếng Việt. Mô hình có khả năng nhận diện các loại công việc khác nhau như học tập, công việc văn phòng, gặp mặt cá nhân, etc.

### Dataset Chi Tiết
- **Kích thước**: 2000 mẫu đa dạng
- **Ngôn ngữ**: Tiếng Việt
- **Các loại công việc (Scenario)**:
  - `TRUONG_HOC` - Công việc liên quan trường học
  - `VAN_PHONG` - Công việc văn phòng
  - `CA_NHAN` - Công việc cá nhân
  
- **Nhãn phân loại (Labels)**:
  - `HOC_TAP` - Học tập
  - `NOP_BAI` - Nộp bài tập
  - `HOP_LOP` - Họp/sinh hoạt lớp
  - `THI_CU` - Thi cử
  - `GUI_EMAIL` - Gửi email
  - `THEO_DOI_CONG_VIEC` - Theo dõi công việc
  - `HEN_CA_NHAN` - Hẹn cá nhân
  - `MUA_SAM` - Mua sắm
  - `NHAC_VIEC` - Nhắc việc

- **Đặc điểm**:
  - Mỗi mẫu bao gồm: nội dung công việc, loại công việc, nhãn phân loại, thời gian
  - Ví dụ: "học bài môn toán trước ngày mai" → Nhãn: `HOC_TAP`

### Kiến Trúc Mô Hình
```
Pipeline (2 bước):
├── TfidfVectorizer (Trích xuất đặc trưng từ văn bản)
│   ├── ngram_range: (1, 2) - Sử dụng unigram và bigram
│   └── min_df: 2 - Bỏ qua từ xuất hiện ít hơn 2 lần
│
└── LogisticRegression (Phân loại)
    ├── max_iter: 2000 - Số lần lặp tối đa
    └── n_jobs: 1 - Sử dụng 1 luồng xử lý
```

### Quá Trình Huấn Luyện (Training)
1. **Load Dataset**: Đọc 2000 mẫu từ CSV
   ```python
   X = df["text"]  # Nội dung công việc (tiếng Việt)
   y = df["labels"]  # Nhãn phân loại (9 loại)
   ```

2. **Chia Train/Test**: Tỷ lệ 80/20 với stratified split
   ```
   Training: 1600 mẫu (80%)
   Testing: 400 mẫu (20%)
   ```

3. **Trích Xuất Đặc Trưng**: Chuyển văn bản thành vectors
   - TF-IDF Vectors từ unigrams và bigrams
   - Loại bỏ từ hiếm gặp

4. **Huấn Luyện Mô Hình**: Logistic Regression học các mẫu
   - Tìm ranh giới quyết định giữa các lớp
   - Điều chỉnh trọng số cho mỗi từ

5. **Đánh Giá Kết Quả**:
   - Tính Accuracy Score trên tập test
   - In ra Classification Report (Precision, Recall, F1-Score)

6. **Lưu Mô Hình**: Lưu dưới dạng joblib file
   ```
   Model saved: nextact_model.joblib
   ```

### Cách Sử Dụng Mô Hình
Gửi request tới API để phân loại công việc:
```bash
POST /api/nextact/classify
{
  "text": "học bài môn toán trước ngày mai"
}
```

**Response**:
```json
{
  "classification": "HOC_TAP",
  "confidence": 0.95
}
```

### Các Tính Năng Bổ Sung
Mô hình cũng tích hợp:
- **Trích xuất deadline**: Phân tích cụm từ thời gian ("ngày mai", "thứ 6", etc.)
- **Hỗ trợ Gemini AI**: Sử dụng Google Generative AI để đưa gợi ý bổ sung
- **Phân tích toàn diện**: Kết hợp phân loại + thời gian + AI suggestions

### Cải Tiến Trong Tương Lai
- 🔄 Thêm nhiều loại công việc và nhãn mới
- 📊 Mở rộng dataset lên 5000-10000 mẫu
- 🤖 Sử dụng mô hình deep learning (LSTM, BERT)
- ⚙️ Fine-tuning với dữ liệu từ người dùng thực tế
- 🎯 Tối ưu hóa thông số mô hình (hyperparameter tuning)

## 📜 Bản Quyền và Thông Tin Liên Hệ

### Tác Giả
**Nguyễn Đào Phúc Nguyên**

### Thông Tin Liên Hệ
📧 **Email**: [nguyendaophucnguyen13@gmail.com](mailto:nguyendaophucnguyen13@gmail.com)

