from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
import sqlite3
from pathlib import Path
from datetime import datetime
import os
import re

DB_PATH = Path(os.getenv("FILE_STORING_DB_PATH", "file_storing.db"))
STORAGE_DIR = Path(os.getenv("FILE_STORAGE_DIR", "./storage"))
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="File Storing Service",
    description="Микросервис хранения студенческих работ (метаданные в SQLite + файлы на диске)",
    version="1.0.0",
)


class Work(BaseModel):
    id: int
    student_id: str
    title: Optional[str] = None
    original_filename: str
    content_type: str
    file_size: int
    created_at: str


EXPECTED_COLUMNS = {
    "id",
    "student_id",
    "title",
    "original_filename",
    "content_type",
    "file_size",
    "file_path",
    "created_at",
}


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='works'")
    exists = cur.fetchone() is not None

    if exists:
        cur.execute("PRAGMA table_info(works)")
        cols = {row[1] for row in cur.fetchall()}
        if not EXPECTED_COLUMNS.issubset(cols):
            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            cur.execute(f"ALTER TABLE works RENAME TO works_old_{ts}")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS works (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            title TEXT,
            original_filename TEXT NOT NULL,
            content_type TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            file_path TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


init_db()


def safe_filename(name: str) -> str:
    name = Path(name).name
    name = name.strip() or "work"
    name = re.sub(r"[^a-zA-Z0-9._-]+", "_", name)
    return name[:200]


@app.get("/health", tags=["service"])
def health():
    return {"status": "ok"}


@app.post("/works", response_model=Work, status_code=201, tags=["works"])
async def create_work(
        student_id: str = Form(...),
        title: Optional[str] = Form(None),
        file: UploadFile = File(...),
):
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Файл пустой")

    original_name = safe_filename(file.filename or "work.bin")
    content_type = file.content_type or "application/octet-stream"
    file_size = len(file_bytes)
    created_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    title_value = (title or "").strip() or None

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO works (student_id, title, original_filename, content_type, file_size, file_path, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (student_id, title_value, original_name, content_type, file_size, "", created_at),
    )
    work_id = cur.lastrowid

    stored_name = f"{work_id}_{original_name}"
    stored_path = STORAGE_DIR / stored_name

    try:
        stored_path.write_bytes(file_bytes)
    except OSError:
        conn.rollback()
        conn.close()
        raise HTTPException(status_code=500, detail="Не удалось сохранить файл на сервере")

    cur.execute("UPDATE works SET file_path = ? WHERE id = ?", (str(stored_path), work_id))
    conn.commit()

    cur.execute(
        "SELECT id, student_id, title, original_filename, content_type, file_size, created_at FROM works WHERE id = ?",
        (work_id,))
    row = cur.fetchone()
    conn.close()

    return dict(row)


@app.get("/works", response_model=List[Work], tags=["works"])
def list_works():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, student_id, title, original_filename, content_type, file_size, created_at FROM works ORDER BY id ASC"
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/works/{work_id}", response_model=Work, tags=["works"])
def get_work(work_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, student_id, title, original_filename, content_type, file_size, created_at FROM works WHERE id = ?",
        (work_id,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Работа не найдена")
    return dict(row)


@app.get("/works/{work_id}/file", tags=["works"])
def download_work_file(work_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT original_filename, content_type, file_path FROM works WHERE id = ?", (work_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Работа не найдена")

    file_path = Path(row["file_path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Файл не найден на сервере")

    return FileResponse(path=str(file_path), media_type=row["content_type"], filename=row["original_filename"])
