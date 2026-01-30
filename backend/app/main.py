from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from backend.app import auth, notes, nextact


app = FastAPI()

# Static files
static_path = Path(__file__).parent.parent.parent / "frontend" / "static"
app.mount("/static", StaticFiles(directory=static_path), name="static")

# Templates path
templates_path = Path(__file__).parent.parent.parent / "frontend" / "templates"

# ============ ROUTES - Frontend Pages ============

@app.get("/")
def index():
    return FileResponse(templates_path / "login.html")

@app.get("/login")
def login_page():
    return FileResponse(templates_path / "login.html")

@app.get("/register")
def register_page():
    return FileResponse(templates_path / "register.html")

@app.get("/dashboard")
def dashboard_page():
    return FileResponse(templates_path / "dashboard.html")

@app.get("/analysis")
def analysis_page():
    """Analytics & insights page"""
    return FileResponse(templates_path / "analysis.html")

@app.get("/dataset")
def dataset_page():
    """Dataset management page"""
    return FileResponse(templates_path / "dataset.html")

# ============ API ROUTES ============

app.include_router(auth.router)
app.include_router(notes.router)
app.include_router(nextact.router)