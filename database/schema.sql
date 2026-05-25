
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
 
CREATE TABLE IF NOT EXISTS notes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    content TEXT,
    status VARCHAR(20) DEFAULT 'todo',
    priority INTEGER DEFAULT 1,
    due_date TIMESTAMP,                     -- FIX 1: DATE → TIMESTAMP để lưu được cả giờ (9h sáng)
    label VARCHAR(100),                     -- FIX 2: Bỏ ALTER TABLE trùng lặp bên dưới
    is_quick_add BOOLEAN DEFAULT FALSE,     -- FIX 3: Gộp vào CREATE TABLE, bỏ ALTER TABLE
    calendar_event_id VARCHAR(255),         -- FIX 4: Thêm cột mới để liên kết Google Calendar
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_user
        FOREIGN KEY(user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);
 
-- ============================================================
-- Nếu DB đã tồn tại, chạy các lệnh ALTER này để cập nhật
-- (Bỏ qua nếu tạo DB mới từ đầu)
-- ============================================================
ALTER TABLE notes ALTER COLUMN due_date TYPE TIMESTAMP USING due_date::timestamp;
ALTER TABLE notes ADD COLUMN IF NOT EXISTS label VARCHAR(100);
ALTER TABLE notes ADD COLUMN IF NOT EXISTS is_quick_add BOOLEAN DEFAULT FALSE;
ALTER TABLE notes ADD COLUMN IF NOT EXISTS calendar_event_id VARCHAR(255);
 
-- ============================================================
-- Kiểm tra dữ liệu
-- ============================================================
SELECT * FROM users;
SELECT * FROM notes;
 