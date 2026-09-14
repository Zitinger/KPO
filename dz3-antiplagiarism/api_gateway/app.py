from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import os
import requests

FILE_STORING_URL = os.getenv("FILE_STORING_URL", "http://localhost:8081")
FILE_ANALYSIS_URL = os.getenv("FILE_ANALYSIS_URL", "http://localhost:8082")

app = FastAPI(
    title="AntiPlagiarism API Gateway",
    description="Центральный сервис-посредник для системы проверки работ на плагиат",
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


class WorkWithReports(BaseModel):
    work: Work
    reports: List[ReportWithStatus]
class WorkWithReport(BaseModel):
    work: Work
    report: Report


@app.get("/health", tags=["service"])
def health():
    return {"status": "ok"}


def call_service(method: str, url: str, **kwargs) -> requests.Response:
    try:
        response = requests.request(method, url, timeout=10, **kwargs)
    except requests.exceptions.RequestException:
        raise HTTPException(status_code=503, detail="Один из внутренних сервисов недоступен")
    return response


@app.post("/works", response_model=WorkWithReport, status_code=201, tags=["works"])
async def create_work(
        student_id: str = Form(...),
        title: Optional[str] = Form(None),
        file: UploadFile = File(...),
):
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Файл пустой")

    files = {
        "file": (file.filename or "work.bin", file_bytes, file.content_type or "application/octet-stream")
    }
    data = {
        "student_id": student_id,
        "title": title or "",
    }

    resp = call_service("POST", f"{FILE_STORING_URL}/works", files=files, data=data)
    if resp.status_code != 201:
        raise HTTPException(status_code=resp.status_code, detail="Ошибка File Storing Service")
    work_data = resp.json()

    resp_an = call_service("POST", f"{FILE_ANALYSIS_URL}/reports", json={"work_id": work_data["id"]})
    if resp_an.status_code != 201:
        raise HTTPException(status_code=resp_an.status_code, detail="Ошибка File Analysis Service")
    report_data = resp_an.json()

    return {"work": work_data, "report": report_data}


@app.get("/works", response_model=List[Work], tags=["works"])
def list_works():
    resp = call_service("GET", f"{FILE_STORING_URL}/works")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Ошибка File Storing Service")
    return resp.json()


@app.get("/works/{work_id}", response_model=Work, tags=["works"])
def get_work(work_id: int):
    resp = call_service("GET", f"{FILE_STORING_URL}/works/{work_id}")
    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="Работа не найдена")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Ошибка File Storing Service")
    return resp.json()


@app.get("/works/{work_id}/report", response_model=WorkWithReport, tags=["reports"])
def get_work_with_report(work_id: int):
    resp_work = call_service("GET", f"{FILE_STORING_URL}/works/{work_id}")
    if resp_work.status_code == 404:
        raise HTTPException(status_code=404, detail="Работа не найдена")
    if resp_work.status_code != 200:
        raise HTTPException(status_code=resp_work.status_code, detail="Ошибка File Storing Service")
    work_data = resp_work.json()

    resp_report = call_service("GET", f"{FILE_ANALYSIS_URL}/reports/{work_id}")
    if resp_report.status_code == 404:
        raise HTTPException(status_code=404, detail="Отчет по работе не найден")
    if resp_report.status_code != 200:
        raise HTTPException(status_code=resp_report.status_code, detail="Ошибка File Analysis Service")
    report_data = resp_report.json()

    return {"work": work_data, "report": report_data}


@app.get("/works/{work_id}/reports", response_model=WorkWithReports, tags=["reports"])
def get_work_reports(work_id: int):
    resp_work = call_service("GET", f"{FILE_STORING_URL}/works/{work_id}")
    if resp_work.status_code == 404:
        raise HTTPException(status_code=404, detail="Работа не найдена")
    if resp_work.status_code != 200:
        raise HTTPException(status_code=resp_work.status_code, detail="Ошибка File Storing Service")
    work_data = resp_work.json()

    resp_reports = call_service("GET", f"{FILE_ANALYSIS_URL}/reports/{work_id}/all")
    if resp_reports.status_code == 404:
        raise HTTPException(status_code=404, detail="Отчеты по работе не найдены")
    if resp_reports.status_code != 200:
        raise HTTPException(status_code=resp_reports.status_code, detail="Ошибка File Analysis Service")
    reports_data = resp_reports.json()

    return {"work": work_data, "reports": reports_data}


@app.get("/works/{work_id}/file", tags=["works"])
def download_work_file(work_id: int):
    resp = call_service("GET", f"{FILE_STORING_URL}/works/{work_id}/file", stream=True)
    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="Работа не найдена")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Ошибка File Storing Service")

    content_type = resp.headers.get("content-type", "application/octet-stream")
    disposition = resp.headers.get("content-disposition")
    headers = {}
    if disposition:
        headers["Content-Disposition"] = disposition

    return StreamingResponse(resp.iter_content(chunk_size=1024 * 256), media_type=content_type, headers=headers)
