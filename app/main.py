from __future__ import annotations

from typing import List

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from . import run_manager as runs

app = FastAPI()

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/start")
async def start(
    request: Request,
    prompt: str = Form(),
    pdf_files: List[UploadFile] = File(default=[]),
):
    run = runs.create_run(prompt)
    await runs.save_uploaded_files(run, pdf_files)
    runs.start_run(run)

    url = request.url_for("result", run_id=run.id)

    return RedirectResponse(url=url, status_code=303)


@app.get("/pdfs/{run_id}/{filename}")
async def get_pdf(run_id: str, filename: str):
    run = runs.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    file_path = run.pdf_dir / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found")
    return FileResponse(
        file_path,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename={filename}",
            "Access-Control-Allow-Origin": "*",
        },
    )


@app.get("/result/{run_id}", name="result")
async def result(request: Request, run_id: str):
    return templates.TemplateResponse(
        "result.html", {"request": request, "run_id": run_id}
    )


@app.get("/events/{run_id}")
async def sse_events(run_id: str):
    run = runs.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return StreamingResponse(runs.event_stream(run), media_type="text/event-stream")


@app.get("/api/runs/{run_id}")
async def get_run_details(run_id: str):
    run = runs.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return JSONResponse(
        {
            "run_id": run.id,
            "prompt": run.prompt,
            "status": run.status,
            "error": run.error,
            "payload": run.payload,
        }
    )
