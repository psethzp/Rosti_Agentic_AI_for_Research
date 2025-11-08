# Rösti Plan

## 3) `plan.md`

> Copy the content below into a file named plan.md and execute it step‑by‑step with your Codex‑high agent. Every step has exact file names, function signatures, prompts, and tests.
> 

---

# plan.md — Collective Insight Lab (3–4h rapid prototype)

**Goal:** Ship a *judge‑friendly*, verifiable, multi‑agent literature summarizer with evidence highlights and a compact reasoning graph. Scope and UX mirror the working plan in the attached project notes. 
ReadME2

**Submission outputs** and formatting follow the hackathon’s official guide. 
Final Submission Guide.docx

---

## 0) Implementation mode & conventions

- **Language:** Python 3.11
- **Single app:** **Streamlit** (UI + orchestration) to minimize glue code
- **Vector DB:** **Chroma** (file‑backed) under `.data/chroma/`
- **PDF parser:** **PyMuPDF** (`fitz`)
- **LLM & embeddings:** OpenAI (model names via env vars)
- **JSON typing:** **pydantic v2** models
- **File layout:** all code in `app/`, assets in `assets/`, data in `.data/`

**Repository tree (create exactly):**

```
collective-insight-lab/
├─ app/
│  ├─ main.py                 # Streamlit entry
│  ├─ ingestion.py            # PDF → chunks → embeddings
│  ├─ retrieval.py            # semantic + keyword retrieval
│  ├─ agents.py               # Researcher, Reviewer, Synthesizer
│  ├─ schemas.py              # pydantic models for Claim/Evidence/Insight
│  ├─ validator.py            # string-window evidence checker
│  ├─ reporting.py            # JSON→HTML/PDF export
│  ├─ graph.py                # reasoning graph (Graphviz DOT)
│  └─ utils.py                # common helpers (logging, ids, paths)
├─ tests/
│  ├─ test_ingestion.py
│  ├─ test_retrieval.py
│  └─ test_validator.py
├─ assets/
│  └─ report_template.html
├─ .env.example
├─ requirements.txt
├─ README.md
├─ Makefile
└─ scripts/
   └─ ingest.py               # CLI: python scripts/ingest.py --input docs/

```

**Environment variables (`.env.example`):**

```
OPENAI_API_KEY=sk-...
EMBED_MODEL=text-embedding-large
CHAT_MODEL=gpt-5-pro-codex-high
CHROMA_DIR=.data/chroma

```

> Note: set CHAT_MODEL/EMBED_MODEL to your available Codex‑high / embedding model IDs. Keep names in .env so swapping is trivial.
> 

---

## 1) Stage I — Bootstrap & Ingestion (≈ 45 min)

### 1.1 Dependencies (`requirements.txt`)

Pin minimal, battle‑tested libs:

```
streamlit==1.39.0
openai>=1.45.0
python-dotenv==1.0.1
pydantic==2.8.2
pymupdf==1.24.9
chromadb==0.5.5
tiktoken==0.7.0
numpy==2.1.1
pandas==2.2.2
graphviz==0.20.3
pytest==8.3.2

```

### 1.2 Ingestion contract (schemas)

Create `app/schemas.py`:

```python
from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Tuple

class EvidenceSpan(BaseModel):
    source_id: str
    page: int
    char_start: int
    char_end: int
    quote: str

class Claim(BaseModel):
    id: str
    topic: str
    text: str
    citations: List[EvidenceSpan] = Field(default_factory=list)
    confidence: Optional[float] = None
    status: Literal["draft","reviewed"] = "draft"

class ReviewedClaim(Claim):
    verdict: Literal["Supported","Weak","Contradicted"]
    reviewer_notes: str = ""

class Insight(BaseModel):
    id: str
    topic: str
    claim_ids: List[str]
    text: str
    confidence: float
    provenance: List[EvidenceSpan]

```

### 1.3 Chunk & embed (`app/ingestion.py`)

**Requirements:**

- Accept `.pdf` paths.
- Extract text per page with char offsets.
- Chunk with `target_tokens=350` overlap `60`.
- Store: `(text, source_id, page, char_start, char_end)`.
- Write to **Chroma** collection `docs`.

**Functions to implement:**

```python
def load_pdf(path: str) -> list[dict]:
    """Return list of {'source_id','page','text','char_start','char_end'}."""
def chunk_pages(pages: list[dict], target_tokens=350, overlap=60) -> list[dict]:
    """Greedy chunker that attaches source_id/page/char spans."""
def embed_chunks(chunks: list[dict]) -> None:
    """Upsert into Chroma with ids = f"{source_id}:{page}:{i}" and metadata."""
def ingest_dir(input_dir: str) -> None:
    """Walk PDFs in input_dir and ingest into vector store."""

```

### 1.4 CLI to run ingestion (`scripts/ingest.py`)

- Args: `-input docs/`
- Calls `ingest_dir`
- Prints count of chunks inserted

### 1.5 Tests

`tests/test_ingestion.py`:

- Load a tiny sample PDF.
- Assert: > 0 chunks, each has non‑empty text & required metadata.
- Smoke test `embed_chunks` (collection size increases).

**Stage I — Done when:**

- `python scripts/ingest.py --input docs/` completes with a chunk count.
- `pytest tests/test_ingestion.py -q` passes.

---

## 2) Stage II — Retrieval & Researcher (≈ 45 min)

### 2.1 Retrieval helper (`app/retrieval.py`)

Provide hybrid search: dense top‑k + simple keyword fallback.

```python
def search(query: str, k: int = 6) -> list[dict]:
    """
    Return list of dicts:
      {'text','score','source_id','page','char_start','char_end'}
    from Chroma metadata. Ensure stable ordering by score then id.
    """

```

### 2.2 Researcher agent (`app/agents.py`)

**Prompt template (system):**

> You are Researcher, tasked to propose factual claims about: "{topic}".
> 
> 
> Use ONLY the provided retrieval tool; each claim MUST include citations with page‑level quotes.
> 
> Output strictly as JSON matching the **Claim[]** schema.
> 

**Tooling contract:** pass a Python retrieval tool to the LLM (`search()`), provide the top‑k texts.

**Generation spec:**

- Produce **3–7 claims**.
- For each claim, include **1–3 EvidenceSpan** items:
    - exact `quote` (<= 320 chars), `source_id`, `page`, `char_start`, `char_end`.

**Function:**

```python
def run_researcher(topic: str) -> list[Claim]:
    """Calls LLM with retrieval tool; parses JSON into Claim models; assigns ids."""

```

### 2.3 Save artifacts

- Write `artifacts/claims.json` (list of `Claim.dict()`).
- Ensure deterministic ids `c0001..`.

### 2.4 Tests

`tests/test_retrieval.py`:

- For a fixed topic, assert `run_researcher()` returns ≥3 claims.
- Every claim has ≥1 citation where `quote` substring exists in its source `text` (basic sanity).

**Stage II — Done when:**

- `python -c "from app.agents import run_researcher; import json; print(len(run_researcher('Your Topic')))"` prints ≥3.
- `artifacts/claims.json` is created.
- `pytest tests/test_retrieval.py -q` passes.
- **Integration:** Manually spot‑check that at least one quote lines up with the PDF.

---

## 3) Stage III — Reviewer & Validator (≈ 45 min)

### 3.1 Evidence validator (`app/validator.py`)

Windowed “exact‑string” check around cited spans—simple and effective. 
ReadME2

```python
def verify_span(span: EvidenceSpan, window: int = 280) -> tuple[bool, str]:
    """
    Load original page text, slice [char_start-window, char_end+window],
    and check exact presence of `quote`. Return (ok, reason).
    """

```

### 3.2 Reviewer agent (`app/agents.py`)

**Purpose:** For each Claim, confirm verdict:

- **Supported**: all citations verify; text is consistent with snippets.
- **Weak**: some citations verify OR evidence is off‑by‑a‑bit.
- **Contradicted**: citations verify but imply the opposite OR clear conflict across sources.

**Implementation:**

- Run `verify_span` for each citation.
- Provide the LLM with: the claim, verified quotes, and any mismatches; ask for one of {Supported, Weak, Contradicted} + 1–2 sentence note.
- Return `ReviewedClaim`.

```python
def run_reviewer(claims: list[Claim]) -> list[ReviewedClaim]:
    """LLM assigns verdict + notes; always respects validator outcomes."""

```

### 3.3 Save artifacts

- Write `artifacts/claims_reviewed.json`.

### 3.4 Tests

`tests/test_validator.py`:

- Craft a Claim with a correct and incorrect `quote` and assert `verify_span` flags them.
- Ensure `run_reviewer` labels all‑pass claims as Supported.

**Stage III — Done when:**

- Review produces a JSON with verdicts (at least one Supported).
- A failing quote is correctly flagged Weak/Contradicted with a note.
- **Integration:** Running Stage II then III yields a clean reviewed set.

---

## 4) Stage IV — Synthesizer, Report & UI (≈ 55 min)

### 4.1 Synthesizer (`app/agents.py`)

**System prompt:**

> You are Synthesizer. Given reviewed claims on "{topic}", assemble 2–5 concise insights that:
> 
> - reuse only **Supported** or clearly‑argued **Weak** claims,
> - include confidence ∈ [0,1] and **provenance spans** for every sentence,
> - avoid speculation; if speculative, tag `[Speculative]`.

```python
def run_synthesizer(topic: str, reviewed: list[ReviewedClaim]) -> list[Insight]:
    """Produce Insight models with provenance arrays referencing EvidenceSpan."""

```

**Output artifacts:**

- `artifacts/report.json` (Insights array)
- `artifacts/report.html` (exported)
- `artifacts/report.pdf` (optional: `pdfkit` if wkhtmltopdf is available; else HTML only)

### 4.2 Reporter (`app/reporting.py`)

- Minimal Jinja‑style string fill (no dependency) using `assets/report_template.html`.
- Include a table of **claims** with verdicts and **insights** with citations.

### 4.3 Reasoning graph (`app/graph.py`)

- Build a **Graphviz DOT** string with nodes: Researcher → Reviewer → Synthesizer → (Red‑Team optional).
- Render as SVG and show in UI.

### 4.4 Streamlit UI (`app/main.py`)

Panels:

1. **Upload**: file_uploader (multiple PDFs). On upload: write files to `docs/` and call ingestion.
2. **Run**: text_input `topic`; buttons for *Run Researcher*, *Run Reviewer*, *Synthesize*; a progress/status area.
3. **Insights**: show Insight cards; on select, open **Evidence Panel** with quotes + `(source_id, page)` and a link to “open page text” (simple text view).
4. **Graph**: display Graphviz SVG.

**UI success criteria (match the earlier blueprint):** Insight cards with confidence & citations; click reveals evidence; tiny reasoning graph visible. 
ReadME2

### 4.5 Manual end‑to‑end test

- Upload 2–3 short PDFs.
- Enter a topic (“Urban flood mapping from satellite”) and click **Run** through all stages.
- Confirm at least 2 **Insights** render with citations and clicking shows evidence lines.
- Export `report.html` and open locally.

**Stage IV — Done when:** You can run the entire flow from upload → report in one sitting without exceptions.

---

## 5) Stage V — Submission assets (15–25 min)

Produce the exact artifacts the jury expects (names/limits below are from the guide). 
Final Submission Guide.docx

1. **Short description (150–300 words)** → `SUBMISSION/short_description.txt`
    - Problem, what you built during the hackathon, who benefits, what already works.
2. **Demo video (≤60s)** → `SUBMISSION/demo.mp4`
    - 5–10s intro; 45–50s live screen recording of the app; optional closing.
3. **Tech video (≤60s)** → `SUBMISSION/tech.mp4`
    - Stack overview (10–15s), implementation highlight (15–20s), challenges/limits (15–20s), 1 takeaway (5s).
4. **1‑page report (PDF)** → `SUBMISSION/OnePager.pdf`
    
    Include *Challenge, Tools/Models, What Worked, What Was Challenging, Time Allocation* (0–3h, 3–8h, etc.); keep to one page, clean layout.
    
5. **GitHub repository** (public) with `README.md` (setup, run, deps)
6. **Zipped code** → `SUBMISSION/code.zip` (no large datasets/weights)
7. **Dataset link or “N/A”**

*(The guide also suggests captions/voiceover for videos and prioritizing a simple, functional demo over polish.)* 
Final Submission Guide.docx

---

## 6) Exact tasks for Codex‑high (copy/paste prompts)

> Run these one at a time. Each task names the files to create and the acceptance tests.
> 

**Task A — Scaffold repo**

```
Create the repo structure exactly as shown in plan.md.
Populate .env.example and requirements.txt with the specified content.
Add a minimal README.md with "Setup", "Run", and "Submission Checklist" sections.

```

**Task B — Implement ingestion**

```
Implement app/ingestion.py with load_pdf, chunk_pages, embed_chunks, ingest_dir as specified.
Create scripts/ingest.py CLI and tests/test_ingestion.py.
Add a tiny sample PDF under docs/sample.pdf and make the test use it.
Acceptance: running `python scripts/ingest.py --input docs/` prints a chunk count; pytest passes.

```

**Task C — Retrieval + Researcher**

```
Implement app/retrieval.py::search() and app/agents.py::run_researcher(topic).
Persist artifacts/claims.json. Add tests/test_retrieval.py.
Acceptance: run_researcher('your topic') returns ≥3 claims; test passes.

```

**Task D — Validator + Reviewer**

```
Implement app/validator.py::verify_span() and app/agents.py::run_reviewer().
Persist artifacts/claims_reviewed.json and tests/test_validator.py.
Acceptance: a synthetic failing quote is flagged; reviewer sets Supported for all-pass claims.

```

**Task E — Synthesizer + Reporting + UI**

```
Implement app/agents.py::run_synthesizer(), app/reporting.py, app/graph.py, and app/main.py.
Add assets/report_template.html.
Acceptance: Streamlit runs; upload PDFs; topic -> Run pipeline; see insights with citations and evidence panel; export report.html.

```

**Task F — Submission pack**

```
Create SUBMISSION/ with short_description.txt, OnePager.md -> PDF, and draft scripts for two 60s videos (demo.md, tech.md).
Add `make zip` in Makefile that zips code into SUBMISSION/code.zip.

```

---

## 7) Prompts (verbatim, ready to paste)

**Researcher (system):**

```
You are Researcher. Goal: propose factual claims about "{topic}" from the given corpus.
Rules:
- Use ONLY the retrieval tool to cite evidence.
- Each claim must include 1–3 EvidenceSpan objects with exact quotes and page indices.
- Output STRICT JSON: [{"id":"", "topic":"", "text":"", "citations":[...], "confidence":0.0, "status":"draft"}]
No extra commentary.

```

**Reviewer (system):**

```
You are Reviewer. For each claim you receive, the validator has already run on its citations.
- If all citations are present and support the text, verdict=Supported.
- If some citations are present but evidence is partial or off-by-a-bit, verdict=Weak.
- If citations are present but contradict the claim, verdict=Contradicted.
Return STRICT JSON ReviewedClaim[] with 'verdict' and 'reviewer_notes' (≤ 2 sentences).

```

**Synthesizer (system):**

```
You are Synthesizer. Input: reviewed claims. Output: 2–5 clear insights for "{topic}".
- Use only Supported claims by default; you may use Weak claims if you qualify them.
- For every insight, attach a 'provenance' array of EvidenceSpan objects backing each sentence.
- Output STRICT JSON Insight[] with fields: id, topic, claim_ids, text, confidence, provenance.
No extra commentary.

```

---

## 8) Testing matrix (incremental)

| Stage | Test | Command | Pass criteria |
| --- | --- | --- | --- |
| I | Ingestion unit | `pytest tests/test_ingestion.py -q` | ≥1 chunk with full metadata |
| II | Researcher smoke | Python one‑liner | ≥3 claims, each has ≥1 citation |
| III | Validator | `pytest tests/test_validator.py -q` | Bad quote flagged; good quote passes |
| III | Reviewer | run function | Verdicts set; notes non‑empty |
| IV | Full run | Streamlit manual | Insights render; evidence panel shows quotes; report exported |

---

## 9) UX notes (keep it judge‑friendly)

- Keep the **Debate Graph → Insights → Evidence** path simple; it’s the hero path judges expect. ReadME2
- The 1‑page report should follow the guide’s five sections and 1‑page limit; use whitespace, bold headers, bullets. Final Submission Guide.docx

---

## 10) Risk & fallback toggles

- If embeddings are slow: lower top‑k to 4; pre‑cache chunk embeddings after ingestion.
- If PDF text extraction is messy: switch to larger chunk size (500 tokens) to absorb noise; still keep page & char offsets.
- If HTML→PDF isn’t available: submit **HTML report**; the guide doesn’t require a PDF export of the app output. Final Submission Guide.docx

---

## 11) Definition of Done (DoD)

- End‑to‑end run (upload→report) **without manual edits**.
- Report contains **claims with citations**, **insights with provenance**, and a visible **reasoning graph**. ReadME2
- Submission folder contains **all 7 items** in the checklist with correct formats and names. Final Submission Guide.docx

---

**That’s it.** If you follow the staged tasks above with Codex‑high, you’ll have a working MVP, a clear demo, and all required submission materials within your 3–4 hour window.