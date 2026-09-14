from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import sqlite3
from pathlib import Path
from datetime import datetime
import os
import re
import requests
from urllib.parse import urlencode, unquote
from io import BytesIO

from docx import Document
from pypdf import PdfReader

DB_PATH = Path(os.getenv("FILE_ANALYSIS_DB_PATH", "file_analysis.db"))
PLAGIARISM_THRESHOLD = float(os.getenv("PLAGIARISM_THRESHOLD", "50.0"))
FILE_STORING_URL = os.getenv("FILE_STORING_URL", "http://localhost:8081")

app = FastAPI(
    title="File Analysis Service",
    description="Микросервис анализа работ: антиплагиат + облако слов (QuickChart)",
    version="1.0.0",
)


class AnalyzeRequest(BaseModel):
    work_id: int


class Report(BaseModel):
    id: int
    work_id: int
    plagiarism_score: float
    max_similarity_work_id: Optional[int] = None
    word_count: int
    unique_word_count: int
    wordcloud_url: str
    created_at: str




class ReportWithStatus(Report):
    is_plagiarism: bool
    status: str
EXPECTED_COLUMNS = {
    "id",
    "work_id",
    "plagiarism_score",
    "max_similarity_work_id",
    "word_count",
    "unique_word_count",
    "wordcloud_url",
    "created_at",
}




def enrich_report_fields(report: dict) -> dict:
    score = float(report.get("plagiarism_score", 0.0))
    is_plagiarism = score >= PLAGIARISM_THRESHOLD
    report["is_plagiarism"] = is_plagiarism
    report["status"] = "PLAGIARISM" if is_plagiarism else "OK"
    return report
def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reports'")
    exists = cur.fetchone() is not None

    if exists:
        cur.execute("PRAGMA table_info(reports)")
        cols = {row[1] for row in cur.fetchall()}
        if not EXPECTED_COLUMNS.issubset(cols):
            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            cur.execute(f"ALTER TABLE reports RENAME TO reports_old_{ts}")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_id INTEGER NOT NULL,
            plagiarism_score REAL NOT NULL,
            max_similarity_work_id INTEGER,
            word_count INTEGER NOT NULL,
            unique_word_count INTEGER NOT NULL,
            wordcloud_url TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


init_db()


def fetch_work_metadata(work_id: int) -> dict:
    try:
        resp = requests.get(f"{FILE_STORING_URL}/works/{work_id}", timeout=10)
    except requests.exceptions.RequestException:
        raise HTTPException(status_code=503, detail="File Storing Service недоступен")

    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="Работа не найдена")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Ошибка File Storing Service")

    return resp.json()


def fetch_all_works() -> List[dict]:
    try:
        resp = requests.get(f"{FILE_STORING_URL}/works", timeout=10)
    except requests.exceptions.RequestException:
        raise HTTPException(status_code=503, detail="File Storing Service недоступен")

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Ошибка File Storing Service")
    return resp.json()


def parse_filename_from_disposition(disposition: str) -> str:
    if not disposition:
        return "work"

    m = re.search(r"filename\*=UTF-8\'\'([^;]+)", disposition)
    if m:
        return unquote(m.group(1))

    m2 = re.search(r'filename="([^"]+)"', disposition)
    if m2:
        return m2.group(1)

    return "work"


def fetch_work_file(work_id: int) -> tuple[bytes, str, str]:
    try:
        resp = requests.get(f"{FILE_STORING_URL}/works/{work_id}/file", timeout=30)
    except requests.exceptions.RequestException:
        raise HTTPException(status_code=503, detail="File Storing Service недоступен")

    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="Работа не найдена")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Ошибка File Storing Service")

    content_type = resp.headers.get("content-type", "application/octet-stream")
    filename = parse_filename_from_disposition(resp.headers.get("content-disposition", ""))
    return resp.content, filename, content_type


def decode_text_bytes(data: bytes) -> str:
    for enc in ("utf-8", "utf-8-sig", "cp1251", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="ignore")


def extract_text(filename: str, content_type: str, data: bytes) -> str:
    ext = Path(filename).suffix.lower()

    if ext == ".docx":
        try:
            doc = Document(BytesIO(data))
            parts = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n".join(parts)
        except Exception:
            return decode_text_bytes(data)

    if ext == ".pdf":
        try:
            reader = PdfReader(BytesIO(data))
            parts: List[str] = []
            for page in reader.pages:
                t = page.extract_text() or ""
                if t.strip():
                    parts.append(t)
            return "\n".join(parts)
        except Exception:
            return decode_text_bytes(data)

    if content_type.startswith("text/") or ext in {".txt", ".md", ".csv", ".json", ".xml", ".yaml", ".yml"}:
        return decode_text_bytes(data)

    return decode_text_bytes(data)


def tokenize(text: str) -> List[str]:
    return re.findall(r"\w+", text.lower())


def jaccard_similarity(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    uni = len(a | b)
    return inter / uni if uni else 0.0


def build_wordcloud_url(text: str) -> str:
    cleaned = " ".join(text.split())
    params = {"text": cleaned, "format": "png", "width": 600, "height": 400, "fontScale": 15}
    return "https://quickchart.io/wordcloud?" + urlencode(params)


@app.get("/health", tags=["service"])
def health():
    return {"status": "ok"}


@app.post("/reports", response_model=Report, status_code=201, tags=["reports"])
def analyze_work(req: AnalyzeRequest):
    work_id = req.work_id

    fetch_work_metadata(work_id)
    data, filename, content_type = fetch_work_file(work_id)
    text = extract_text(filename, content_type, data).strip()

    tokens = tokenize(text)
    word_count = len(tokens)
    unique_words = set(tokens)
    unique_word_count = len(unique_words)

    works = fetch_all_works()
    max_sim = 0.0
    max_sim_work_id: Optional[int] = None

    for w in works:
        other_id = int(w["id"])
        if other_id == work_id:
            continue

        other_data, other_filename, other_ct = fetch_work_file(other_id)
        other_text = extract_text(other_filename, other_ct, other_data)
        other_set = set(tokenize(other_text))

        sim = jaccard_similarity(unique_words, other_set)
        if sim > max_sim:
            max_sim = sim
            max_sim_work_id = other_id

    plagiarism_score = round(max_sim * 100.0, 2)
    wordcloud_url = build_wordcloud_url(text if text else filename)
    created_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO reports (work_id, plagiarism_score, max_similarity_work_id, word_count, unique_word_count,
                             wordcloud_url, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (work_id, plagiarism_score, max_sim_work_id, word_count, unique_word_count, wordcloud_url, created_at),
    )
    report_id = cur.lastrowid
    conn.commit()

    cur.execute("SELECT * FROM reports WHERE id = ?", (report_id,))
    row = cur.fetchone()
    conn.close()

    return dict(row)


@app.get("/reports", response_model=List[Report], tags=["reports"])
def list_reports():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM reports ORDER BY id ASC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/reports/{work_id}", response_model=Report, tags=["reports"])
def get_latest_report(work_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM reports WHERE work_id = ? ORDER BY id DESC LIMIT 1", (work_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Отчет по работе не найден")
    return dict(row)


@app.get("/reports/{work_id}/all", response_model=List[ReportWithStatus], tags=["reports"])
def get_all_reports_by_work(work_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM reports WHERE work_id = ? ORDER BY id DESC", (work_id,))
    rows = cur.fetchall()
    conn.close()
    if not rows:
        raise HTTPException(status_code=404, detail="Отчеты по работе не найдены")
    result = []
    for row in rows:
        r = dict(row)
        result.append(enrich_report_fields(r))
    return result
