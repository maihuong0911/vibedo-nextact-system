"""
migrate_assignments.py
Chạy 1 lần để tạo bảng task_assignments và notifications trong DB.

Usage:
    python migrate_assignments.py
"""
from sqlalchemy import create_engine, text
import os

DATABASE_URL = "postgresql://postgres:1234@localhost:5433/nextact_todo_db"
engine = create_engine(DATABASE_URL)

SQL = """
-- =====================================================================
-- Bảng task_assignments: lưu giao việc / mời họp giữa 2 tài khoản
-- =====================================================================
CREATE TABLE IF NOT EXISTS task_assignments (
    id               SERIAL PRIMARY KEY,
    note_id          INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    sender_id        INTEGER NOT NULL REFERENCES users(id),
    receiver_id      INTEGER NOT NULL REFERENCES users(id),
    assignment_type  VARCHAR(20) NOT NULL DEFAULT 'task',
    status           VARCHAR(20) NOT NULL DEFAULT 'pending',
    message          TEXT,
    created_at       TIMESTAMP DEFAULT NOW(),
    responded_at     TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_assign_receiver
    ON task_assignments(receiver_id, status);

CREATE INDEX IF NOT EXISTS idx_assign_sender
    ON task_assignments(sender_id);

-- =====================================================================
-- Bảng notifications: thông báo hiển thị trên icon chuông
-- =====================================================================
CREATE TABLE IF NOT EXISTS notifications (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    sender_id       INTEGER REFERENCES users(id),
    type            VARCHAR(50) NOT NULL,
    title           VARCHAR(255) NOT NULL,
    body            TEXT,
    assignment_id   INTEGER REFERENCES task_assignments(id),
    note_id         INTEGER REFERENCES notes(id),
    is_read         BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notif_user_unread
    ON notifications(user_id, is_read);
"""


def run():
    with engine.connect() as conn:
        conn.execute(text(SQL))
        conn.commit()
        r1 = conn.execute(text("SELECT COUNT(*) FROM task_assignments")).scalar()
        r2 = conn.execute(text("SELECT COUNT(*) FROM notifications")).scalar()
        print(f"Tạo bảng thành công!")
        print(f"   task_assignments: {r1} bản ghi")
        print(f"   notifications   : {r2} bản ghi")


if __name__ == "__main__":
    run()