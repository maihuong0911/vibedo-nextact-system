from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse, HTMLResponse
from pathlib import Path
from fastapi.templating import Jinja2Templates
from backend.app import auth, notes, nextact, home

# Import assignment nếu file đã được tạo, fallback nếu chưa có
try:
    from backend.app import assignment as assignment_router
    HAS_ASSIGNMENT = True
except ImportError:
    HAS_ASSIGNMENT = False

# Import profile router
try:
    from backend.app import profile as profile_router
    HAS_PROFILE = True
except ImportError:
    HAS_PROFILE = False

# Import projects router
try:
    from backend.app import projects as projects_router
    HAS_PROJECTS = True
except ImportError:
    HAS_PROJECTS = False

app = FastAPI()


# =====================================================================
# AUTO-MIGRATE: Tự động tạo bảng DB khi server khởi động
# =====================================================================
@app.on_event("startup")
def auto_migrate():
    from sqlalchemy import create_engine, text
    import os

    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:1234@localhost:5433/nextact_todo_db"
    )
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            # Bảng projects
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS projects (
                    id          SERIAL PRIMARY KEY,
                    owner_id    INTEGER NOT NULL REFERENCES users(id),
                    name        VARCHAR(200) NOT NULL,
                    description TEXT,
                    created_at  TIMESTAMP DEFAULT NOW()
                );
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_projects_owner
                    ON projects(owner_id);
            """))
            # Cột project_id trong notes (nếu chưa có)
            conn.execute(text("""
                ALTER TABLE notes ADD COLUMN IF NOT EXISTS
                    project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL;
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_notes_project
                    ON notes(project_id);
            """))
            # Bảng task_assignments
            conn.execute(text("""
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
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_assign_receiver
                    ON task_assignments(receiver_id, status);
            """))
            # Bảng notifications
            conn.execute(text("""
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
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_notif_user_unread
                    ON notifications(user_id, is_read);
            """))
            # Bảng project_members — thành viên dự án
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS project_members (
                    id          SERIAL PRIMARY KEY,
                    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    joined_at   TIMESTAMP DEFAULT NOW(),
                    UNIQUE(project_id, user_id)
                );
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_proj_members
                    ON project_members(project_id, user_id);
            """))
            # ── Profile columns trên bảng users ──────────────────────
            conn.execute(text("""
                ALTER TABLE users ADD COLUMN IF NOT EXISTS
                    avatar_url TEXT;
            """))
            conn.execute(text("""
                ALTER TABLE users ADD COLUMN IF NOT EXISTS
                    gender VARCHAR(10);
            """))
            conn.execute(text("""
                ALTER TABLE users ADD COLUMN IF NOT EXISTS
                    birthday DATE;
            """))
            conn.execute(text("""
                ALTER TABLE users ADD COLUMN IF NOT EXISTS
                    bio TEXT;
            """))
            conn.commit()
            print("[Startup] DB migration OK — projects, task_assignments, notifications, project_members, profile sẵn sàng")
    except Exception as e:
        print(f"⚠️  [Startup] Migration warning: {e}")
static_path    = Path(__file__).parent.parent.parent / "frontend" / "static"
templates_path = Path(__file__).parent.parent.parent / "frontend" / "templates"

app.mount("/static", StaticFiles(directory=static_path), name="static")
templates = Jinja2Templates(directory=str(templates_path))


def _t(request: Request, name: str, ctx: dict = None):
    """TemplateResponse + no-cache."""
    ctx = ctx or {}
    ctx["request"] = request
    resp = templates.TemplateResponse(name, ctx)
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"]  = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


# ── Auth (plain HTML, không extends base) ────────────────────────────
@app.get("/")
def index():
    return FileResponse(templates_path / "login.html")

@app.get("/login")
def login_page():
    return FileResponse(templates_path / "login.html")

@app.get("/register")
def register_page():
    return FileResponse(templates_path / "register.html")


# ── Trang chủ ─────────────────────────────────────────────────────────
@app.get("/home", response_class=HTMLResponse)
async def home_page(request: Request):
    return _t(request, "home.html", {"active_page": "home"})


# ── Công việc ─────────────────────────────────────────────────────────
@app.get("/tasks", response_class=HTMLResponse)
async def tasks_page(request: Request):
    return _t(request, "tasks.html", {
        "active_page":     "tasks",
        "show_filter_btn": False,
    })


# ── Dự án ─────────────────────────────────────────────────────────────
@app.get("/projects-page", response_class=HTMLResponse)
async def projects_page(request: Request):
    return _t(request, "projects.html", {"active_page": "projects"})


# ── Kế hoạch tuần ────────────────────────────────────────────────────
@app.get("/weekly_planner", response_class=HTMLResponse)
async def weekly_planner_page(request: Request):
    return _t(request, "weekly_planner.html", {"active_page": "weekly_planner"})


# ── Redirect cũ ───────────────────────────────────────────────────────
@app.get("/dashboard")
def dashboard_page():
    return RedirectResponse(url="/tasks")

@app.get("/analysis")
def analysis_page():
    return FileResponse(templates_path / "analysis.html")

@app.get("/dataset")
def dataset_page():
    return FileResponse(templates_path / "dataset.html")

# ── Suggestions redirect → tasks ──────────────────────────────────────
@app.get("/suggestions")
def suggestions_redirect():
    return RedirectResponse(url="/tasks")


# ── Routers ───────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(notes.router,   prefix="/notes")
app.include_router(nextact.router)
app.include_router(home.router)

if HAS_ASSIGNMENT:
    app.include_router(assignment_router.router)

if HAS_PROJECTS:
    app.include_router(projects_router.router)
    app.include_router(projects_router.users_router)

if HAS_PROFILE:
    app.include_router(profile_router.router)