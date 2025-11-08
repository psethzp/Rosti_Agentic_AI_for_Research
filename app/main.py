import asyncio
import uuid
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from typing import List

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
    """
    Handle the form submit
    """
    run_id = str(uuid.uuid4())

    # Print the prompt
    print(f"\n{'='*60}")
    print(f"New Request - Run ID: {run_id}")
    print(f"{'='*60}")
    print(f"Prompt: {prompt}")

    # Print uploaded file names
    if pdf_files and len(pdf_files) > 0 and pdf_files[0].filename:
        print(f"\nUploaded PDF files ({len(pdf_files)}):")
        for i, file in enumerate(pdf_files, 1):
            print(
                f"  {i}. {file.filename} (Content-Type: {file.content_type}, Size: {file.size} bytes)"
            )
    else:
        print("\nNo PDF files uploaded")

    print(f"{'='*60}\n")

    url = request.url_for("result", run_id=run_id)

    return RedirectResponse(url=url, status_code=303)


@app.get("/result/{run_id}", name="result")
async def result(request: Request, run_id: str):
    return templates.TemplateResponse(
        "result.html", {"request": request, "run_id": run_id}
    )


@app.get("/events/{run_id}")
async def sse_events(run_id: str):
    """
    SSE stream that sends HTML snippets for the result page to insert
    """

    async def event_gen():
        yield "retry: 2000\n\n"

        steps = [
            "Booting agents…",
            "Planning…",
            "Fetching tools…",
            "Coordinating…",
            "Synthesizing answer…",
        ]

        for i, step in enumerate(steps, start=1):
            await asyncio.sleep(1)
            html = f"<div>Step {i}/{len(steps)}: {step}</div>"
            yield f"event: message\ndata: {html}\n\n"

        await asyncio.sleep(0.5)
        yield "event: message\ndata: <div><strong>Done!</strong></div>\n\n"

        while True:
            await asyncio.sleep(60)

    return StreamingResponse(event_gen(), media_type="text/event-stream")
