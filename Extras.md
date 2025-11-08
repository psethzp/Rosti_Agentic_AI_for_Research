# Rösti

## 2) The project we’ll ship (fast, API‑first, judge‑friendly)

### Name

**Collective Insight Lab** – agents that *read, argue, and agree* with receipts.

### 2.1 Goals

1. **Quality**: Multiple agents beat a single LLM on *factuality + coverage* for a narrow topic.
2. **Verifiability**: Every insight is backed by **line‑level citations** and a **reasoning trace graph**.
3. **Usability**: A coach‑like UI that a student/analyst can use: upload PDFs → get **Collective Insight Report**.

This maps directly to the brief’s MVP: ingestion → multi‑agent reasoning → **Collective Insight Report with citations & traces**. 

---

## 3) Feature set (scope that wins in 24 hours)

**Hero features (must‑have)**

- **Triage & retrieval**: ingest 10–20 PDFs (arXiv/Semantic Scholar/OpenAlex/Uploads) → chunk + embed.
- **3–5 agents with roles**: *Researcher* (extract claims), *Reviewer* (attack/verify), *Synthesizer* (assemble insights), *Red‑Team* (find contradictions). Agents message through a controllable graph.
- **Collective Insight Report** (JSON → UI): for each **Insight** include *claim*, *evidence snippets* (source/page/quote), *confidence*, *disagreements resolved*.
- **Evidence viewer**: click any claim to see PDF snippets and which agent argued what.
- **Eval harness**: **citation precision**, **hallucination rate**, **coverage** vs a tiny gold set; **cost/insight** and **latency**.

**Stretch (time‑permitting)**

- **Open protocols**: MCP/A2A for plug‑in agents.
- **Hypothesis generator**: propose “next experiment / next dataset” lines (clearly marked speculative).
- **Contradiction map**: a mini Sankey from papers → supporting vs refuting claims.

---

## 4) Architecture & tools (minimal training; mostly APIs)

**Core orchestration**

- **LangGraph** or **OpenAI Assistants** for stateful, tool‑calling agents with guards. (Judges recognize both; LangGraph gives fine control & tracing.) [LangChain Blog](https://blog.langchain.com/langchain-state-of-ai-2024/?utm_source=chatgpt.com)
- **FastAPI** backend + **Streamlit** (or Next.js) frontend.

**Document ingestion**

- **PDF parsing**: `pymupdf`/`pdfminer.six`; **GROBID** if needed for better references.
- **OCR fallback**: Tesseract (only for scanned PDFs).
- **Embeddings**: text-embedding-large (OpenAI) or compatible; **FAISS/Chroma** vector store.
- **Metadata**: store source id, page, char offsets to support quotes.

**Reasoning loop**

- **Tool‑calling** LLM (GPT family) with **JSON schema** outputs for: `Claim`, `Evidence`, `Citations`, `Confidence`, `OpenQuestions`.
- **Reviewer agent** uses retrieval tools + regex heuristics to check **exact string presence** near cited spans (simple but effective guard).
- **Synthesizer agent** must include a **provenance array** for every sentence.

**Visualization**

- **Agent graph**: D3.js (in Streamlit via `components.html`) or Graphviz image.
- **Evidence side‑panel**: highlight PDF text (fitz rects from `pymupdf`).

**Eval & observability**

- `evaluate.py` prints: **Citation Precision@1**, **Claim Hallucination%**, **Coverage%**, **Avg cost ($)**, **Latency (s)**.
- **LangSmith** (optional) to store traces; or local JSON logs.

**Hosting**

- **HF Spaces (CPU)** for demo;
- **Render/Workers** for API if you want separation;
- Repo with **Dockerfile** + `docker compose up`.

> All of this is squarely inside the challenge’s hints: multi‑agent frameworks (CrewAI/LangGraph/AutoGen/Assistants), arXiv/Semantic Scholar/OpenAlex for data, and a dashboard for visualization. 02 Challenge - Agentic AI for a…
> 

---

## 5) Step‑by‑step implementation (24‑hour schedule)

**T‑0 → T+1h (Kickoff)**

- Lock *one* topic (e.g., “AI for flood forecasting”.
- Draft **win doc**: metric, demo storyboard, risks. (Mirrors the submission guide’s emphasis on clarity.)

**T+1 → T+3h**

- Scaffold repo (FastAPI + Streamlit + LangGraph).
- Implement **ingestion** (PDF → chunks with source/page) + **vector store**.
- Write `schema.py` (pydantic models): `Evidence`, `Claim`, `Insight`.

**T+3 → T+8h**

- Implement **Researcher** & **Reviewer** loops with tool‑calling + retrieval.
- Add **citation validator** (string‑match window around cited span); flag fails.
- Build **Collective Insight Report** generator.

**T+8 → T+12h**

- Build **UI**:
    - Upload → Topic selection
    - **Agent Debate graph** (D3)
    - **Insight list** with confidence + citations
    - **Evidence viewer** (highlighted quotes)

**T+12 → T+16h**

- **Eval harness**: label 10–15 Q/A pairs by hand; compute metrics; add latency/$ logs.

**T+16 → T+20h**

- Polish edge cases; add **Red‑Team** mini‑agent (contradiction finder).
- Record **Demo video** (golden path) and **Tech video** (stack + metrics), exactly to guide format. Final Submission Guide.docx

**T+20 → T+24h**

- Final README + **1‑pager** (the 5 sections from guide), tag release, zip code, submit on **both platforms**. Final Submission Guide.docx

---

## 6) UI blueprint (judge‑friendly)

1. **Home / Upload**: topic + PDF drag‑drop → progress banner (“Parsing → Debating → Synthesizing”).
2. **Debate View** (hero): Graph of agents; timeline; click a message to see tool calls & snippets.
3. **Insights**: cards with **claim**, **confidence**, **supporting sources (S1 p.3, S4 p.12)**, **“See evidence”**.
4. **Evidence Panel**: side‑by‑side PDF with highlighted spans and *why Reviewer accepted/rejected*.
5. **Metrics**: mini table (*Citation Precision 92%*, *Hallucination 6%*, *Coverage 78%*, *Cost/insight $0.07*, *Latency 7.2s*).
6. **Export**: **Collective Insight Report** (PDF/JSON) for sharing.

---

## 7) “Wow” factors (how we stand out)

1. **Visible reasoning graph** with *debate steps, objections, and resolutions* (not just a chat log). 
2. **Claim‑level provenance** (hover any sentence → exact quoted lines + page).
3. **Automatic contradiction detector** (Red‑Team agent) that flags conflicts across papers.
4. **Quantified uplift** vs single‑agent baseline (we’ll run the same input through “solo LLM” and show higher **citation precision** / lower hallucination).
5. **Cost/latency dashboard** showing we engineered for reality (great for the Tech video per the guide). Final Submission Guide.docx

---

## 8) Evaluation plan (make “depth” obvious)

- **Citation Precision@1** = fraction of claims whose cited span truly supports the text.
- **Hallucination Rate** = claims with missing/contradictory evidence.
- **Coverage** = % of key questions answered from a tiny “syllabus” (10–15).
- **Agent Uplift** = (precision_multi − precision_single).
- **Cost/Insight & Latency** = runtime + $ per claim.

We’ll show a screenshot of the `evaluate.py` output in the **Tech video** (the guide specifically wants concise tech & challenge highlights). 
Final Submission Guide.docx

---

## 9) Skills & tools (everything you’ll need)

**AI/Reasoning**

- LLM tool‑calling & JSON schemas, **LangGraph** (or Assistants), retrieval engineering, prompt ablations.

**Data & Parsing**

- PDF parsing (`pymupdf`, `pdfminer.six`), optional **GROBID** for references, **Tesseract** OCR fallback, arXiv / Semantic Scholar / OpenAlex loaders. 02 Challenge - Agentic AI for a…

**Backend/Frontend**

- **FastAPI**, **Streamlit** (or Next.js).
- **D3.js/Graphviz** for debate graph; **FAISS/Chroma** for vectors.

**Infra & DevEx**

- Docker, GitHub Actions (CI), Hugging Face Spaces (demo), Render/Workers (API).
- Logging + minimal tests; **LangSmith** (optional) for trace inspection.

**Product**

- Storyboarding (videos), writing the 1‑pager per guide, accessibility (captions), and lightweight UX polish.

---

## 10) Why this will stand out vs similar entries

- **Most teams** will show generic multi‑agent chats.
- **We** will ship **audited, measured reasoning**: claim‑level provenance, quantitative uplift over a single model, and a **contradiction map**—all wrapped in a **one‑click, stable demo**. That combination maps tightly to *all three* rubric pillars (depth, creativity, communication).

---

## 11) The “Winning Formula” (does it fit?):

**Social Impact + Accessibility/Underserved + Multi‑modality + Real User Problem**

**Yes, apply it here—explicitly:**

- **Social impact**: focus topics like *climate risk*, *rare‑disease diagnosis literature*, or *energy storage*.
- **Accessibility**: low‑bandwidth mode (upload PDFs, no logins), captions in videos, readable exports; **non‑English abstracts** tested (agent auto‑translate).
- **Multi‑modality**: parse **text + tables + figures** (basic figure OCR or captions), and let users ask **voice queries** (small STT hook) if time allows.
- **Real user problem**: **literature overload** and **trust**; our core USP is *verifiable synthesis*, not just summaries.
    
    This framing boosts *Creativity & Communication* without derailing scope.
    

---

## 12) Risk management (so we don’t stumble)

- **Data variability** → fix by curating 10–20 short PDFs; keep chunking simple.
- **Latency/cost spikes** → cache retrieval, deterministic parsing, minimal temperature.
- **UI complexity** → prioritize the **Debate→Insight→Evidence** path and leave extras as stretch.
- **Ethics** → clearly mark **speculative** hypotheses; discourage citation out of context.

---

## 13) Final deliverables checklist (mirrors the guide)

- **Demo video (≤60s)**: short intro → live run → result. Final Submission Guide.docx
- **Tech video (≤60s)**: stack → hard part → metrics → reflection. Final Submission Guide.docx
- **One‑pager PDF**: 5 sections (challenge, tools/models, what worked, what was challenging, time allocation). Final Submission Guide.docx Final Submission Guide.docx
- **Public GitHub**, **zipped code**, dataset link/N/A, submit on **both** platforms before Nov **09, 9:00am ET**. Final Submission Guide.docx

---

BONUS ADD-ONS

### 1) “Suggested Reads” (Recommendation System)

**Goal.** Help users go beyond the current set by recommending 3–5 papers that would most **increase coverage** or **resolve contradictions**.

**Method (fast & feasible):**

- **Content‑based:** embed each current paper’s abstract → compute centroid; query **arXiv / Semantic Scholar / OpenAlex** for top K candidates by cosine similarity (also filter by recency).
- **Gap‑targeted:** have the *Reviewer/Red‑Team* produce **open questions / conflicts**; convert each question to a search query; rank candidates by a composite score: similarity + novelty (low similarity to existing set) + “question match” score.
- **Explainable rec:** for each suggestion, show *why*: “addresses unresolved Q2; new method; 2024; 150 citations.”

**Tools:** OpenAI embeddings, FAISS/Chroma, `arxiv`/OpenAlex/Semantic Scholar APIs; small LLM prompt for the “why”. (APIs are listed as recommended sources in the challenge hints.) 
02 Challenge - Agentic AI for a…

**Why it helps judging:** adds **technical depth** (ranking + gap modeling) and **communication** (clear rationale per rec), while staying optional.

---

### 2) Semantic Map (graph/cluster of papers with keyword tagging)

**Goal.** Give a **visual mental model** of the literature (themes, clusters, outliers).

**Method (1–2 hours of work):**

- **Embeddings → 2D projection:** compute document embeddings → **UMAP** (or t‑SNE/PCA) to 2D.
- **Clustering:** **HDBSCAN** or k‑means on embeddings to group topics.
- **Keyword tags:** run **KeyBERT/YAKE** or LLM on each cluster to get 2–4 representative keyphrases.
- **UI:** Plotly scatter (fast in Streamlit) or a force‑directed **PyVis** graph; clicking a node opens the paper card or evidence panel.

**Why it helps judging:** boosts **communication** (one glance understanding), plus **creativity** with low coding overhead.

---

### 3) Scholarly Search + On‑Demand Fact‑Check

**Goal.** Let users **expand** the corpus and **verify** contentious claims with minimal friction.

**Method (guard‑railed):**

- **SearchAgent** with two connectors: **arXiv** and **OpenAlex** (fallback to Semantic Scholar). Limit to **N ≤ 5 results** per query to avoid scope creep.
- **Abstract‑only pre‑screen:** fetch abstract + metadata first; only download full PDFs if a paper is selected to “add to corpus”.
- **ClaimVerifier:** for any highlighted claim, retrieve top matching passages across selected papers and check for **exact/near‑exact support** (string window match + LLM verdict). Mark **Supported / Weak / Contradicted** with citations.

**Why it helps judging:** strengthens **technical depth** (tools + retrieval + verification) and **communication** (clear supported/contradicted badges), but remains **off** by default so the MVP flow is clean.

---

## What changes in our MVP & UI

**Pages / panels**

1. **Debate** (hero): the agent graph + timeline of messages.
2. **Insights**: cards with claim, confidence, and **click‑to‑evidence** (page & quote).
3. **Explore** *(new)*: **Semantic Map** + **Suggested Reads** sidebar (reasons shown inline).
4. **Verify** *(new tab on claim panel)*: run **ClaimVerifier** against the current set or the newly added suggestions.
5. **Metrics**: our uplift metrics vs single‑agent baseline.

**Toggle design (scope control)**

- “**Expand with scholarly search**” button → runs once, adds 3–5 “candidate reads” with **why**.
- “**Add to corpus**” checkboxes → re‑run agents only if you add something; otherwise nothing changes.

This respects the brief’s advice to **keep ingestion simple (10–20 items)** and focus on reasoning, while giving us tasteful extras if time permits. 
02 Challenge - Agentic AI for a…

---

## Implementation details (so it’s weekend‑doable)

**Core (must‑have)**

- **LangGraph / Assistants** agents (Researcher, Reviewer, Synthesizer, Red‑Team).
- **PDF parsing**: `pymupdf` (with Tesseract fallback if a scan appears).
- **RAG**: OpenAI embeddings + FAISS/Chroma; store `(source_id, page, char_range)` for line‑level quotes.
- **Citation validator**: exact/near‑exact match within a small window around the cited text.
- **Eval harness**: `evaluate.py` prints **Citation Precision@1**, **Hallucination%**, **Coverage%**, **Cost/insight**, **Latency**.
- **UI**: Streamlit with D3/Plotly component for the graph.

**Add‑ons (your ideas)**

- **Recs:** embed centroid + “gap queries” → API search → rerank; small LLM for “why”.
- **Semantic Map:** UMAP/HDBSCAN + Plotly scatter; cluster labels via KeyBERT/LLM.
- **Fact‑check:** targeted retrieval + string check + LLM verdict; color badges.

**Hosting / Delivery**

- **HF Spaces (CPU)** for demo; **Dockerfile** + `docker compose up`; shows we followed the submission guide and built a reproducible MVP with clear videos and one‑pager. Final Submission Guide.docx

---

## Risks & guardrails

- **Scope creep:** all extras are **off‑by‑default** and **one‑click**.
- **Rate limits:** cache search results and embeddings; dedupe by DOI.
- **UI time sink:** prefer Plotly scatter (fast) over heavy custom D3 unless time permits.
- **Evaluation clarity:** keep the same 10–20 papers for the core experiment; extras do not change the baseline unless user opts in.

---

## Why these additions *help us win*

- They **directly support the story** that *agents think better together*: the *Red‑Team/Reviewer* create **gaps/contradictions**; the *Scout/Search agent* proposes **reads** that close them; the *Synthesizer* re‑evaluates and **improves metrics**.
- They raise **technical depth** without sacrificing the **communication** pillar—our **map + scorecards** are judge‑friendly visuals.
- They adhere to the challenge’s scope guidance (no “full discovery engine”), keeping ingestion small but thoughtful.

---

USER POV

## A. What the user can do (end‑to‑end feature list)

### 1) Start a review

- **Upload papers (10–20)** as PDFs or paste arXiv/OpenAlex links.
- **Define a topic or prompt**: “What do papers say about LLMs for flood forecasting?”
- **Optionally seed guiding questions** (e.g., data requirements, limitations, evaluation metrics).
- **Choose a mode**:
    - **Quick Scan (Light)** – faster, fewer critique rounds, smaller context windows.
    - **Deep Review (Heavy)** – more agents/iterations, red‑teaming, contradiction search, and extra retrieval passes.
    - **Custom** – sliders for “Critique rounds,” “Max sources per claim,” “Adversarial intensity,” and “Time/Cost budget.”

> This aligns with the challenge’s design: simple ingestion + multi‑agent reasoning + visible traces02 Challenge - Agentic AI for a….
> 

### 2) Talk to it (optional STT)

- **Voice input** for queries/notes via Speech‑to‑Text.
- “Summarize the baselines in simple terms.”
- “Check if paper #4’s claim about R^2>0.9 is actually supported.”
- STT is off by default; when on, your voice note drops into the run as a **user directive** for the current stage.

### 3) Watch the debate (live)

- **Debate Graph**: animated nodes (*Researcher → Reviewer → Red Team → Synthesizer*).
- **Live timeline**: messages stream in as the agents critique and refine.
- **Stage badges**: *Triage → Claims → Evidence Checks → Contradictions → Synthesis*.
- You can **hover any agent turn** to see the tool calls, snippets, and links.

> “Agents converse or message each other” and a visual graph of the reasoning flow are recommended in the challenge brief02 Challenge - Agentic AI for a….
> 

### 4) Intervene while it’s running (no hard stop)

- **Inline nudges**:
    - “Treat paper #3 as lower quality (small sample).”
    - “Add this 2024 preprint (URL) only if it addresses Q2.”
    - “Increase red‑team harshness for claim C7.”
- **Pin/Unpin evidence**: if you pin a snippet, the Synthesizer must include or respond to it.
- **Priority queue**: inject a new question mid‑run—agents schedule it next without flushing progress.
- **Pause/Resume checkpoints**: if you toggle from *Light* to *Deep*, the graph resumes from the next stage using the new settings.

> The “human‑in‑the‑loop” aspect is how we demonstrate agentic control rather than a static pipeline, which the brief encourages via multi‑agent collaboration and reasoning transparency02 Challenge - Agentic AI for a….
> 

### 5) Inspect insights with receipts

- **Insight cards** with: *claim*, *confidence*, *supporting citations* (paper/page/quote), **badges** (Supported / Weak / Contradicted), and a **“See Evidence”** panel that highlights the exact lines in the PDF.
- **Why this conclusion?**: show which agent proposed it and who objected; who changed whose mind.

> “Verifiable reasoning” and sources/snippets for each insight are explicitly called out as stretch/hero behaviors
> 

### 6) Explore (your suggested add‑ons)

- **Semantic Map**: UMAP/HDBSCAN clusters; keywords label each cluster; click a node to open the paper card.
- **Suggested Reads**: “Add 3–5 papers to improve coverage or resolve conflict Q2.” Each suggestion shows a **reason** (“addresses ablation gap; 2024; 150 citations”).
- **On‑demand fact‑check**: select any claim → run a targeted retrieval and **verdict**.

> Scholarly search with arXiv/OpenAlex/Semantic Scholar is explicitly suggested as data sources/hints in the brief02 Challenge - Agentic AI for a….
> 

### 7) Export and share

- **Collective Insight Report** (PDF/HTML/JSON) with a one‑page executive summary + appendix of claims, evidence, contradictions, and open questions.
- **Replay link** (optional): share a read‑only view of the debate timeline, so others can inspect reasoning steps (great for the judging “communication” pillar).
- **BibTeX/CSV** of sources used and suggested reads.

---

---

## C. Feature settings (so users feel in control)

**Modes**

- **Quick Scan**: 1 critique round, ≤2 citations/claim, Red Team off, top‑K=3 retrieval.
- **Deep Review**: 2–3 critique rounds, Red Team + Advocate on, contradiction search, top‑K=6–8, question‑driven recs.
- **Custom sliders**:
    - *Critique rounds* (0–3)
    - *Adversarial intensity* (low/med/high)
    - *Max citations per claim* (1–5)
    - *Search expansion* (off/3/5 new papers)
    - *Budget* ($ cap) and *Latency* (soft cap)

**Intervention tools**

- “**Nudge**” buttons: *Soften/Strengthen a claim*, *Lower quality of a source*, *Re‑run verification for C7*, *Prefer recency*.
- “**Inject source**” field (URL/DOI) with scope (global / only for Q2).
- “**Pin evidence**” and **Thumbs up/down** to bias weighting in the next synthesis.

---

## D. UI sketch (user‑visible elements)

- **Left rail**: Topic, Corpus (paper list with quality badges), Mode selector, Budget/Latency, STT toggle.
- **Center**:
    - **Debate Graph** (hero) with a timeline scrubber.
    - **Insights** list; clicking an insight opens **Evidence Panel** (right).
- **Right**: Evidence viewer with PDF highlights; **Verify** tab (Supported/Weak/Contradicted); **Suggested Reads** with checkboxes to “Add to corpus”.
- **Footer**: Metrics mini‑dash (Citation Precision, Hallucination %, Coverage %, Cost/insight, Latency) and Export buttons.

The **graph of agent reasoning** and transparent **reasoning traces** are exactly what the challenge suggests as strong demo artifacts
02 Challenge - Agentic AI for a….

---

## E. Why these are viable (and help us win)

- **Meets MVP**: 10–20 docs, agents conversing, **verifiable** insights with citations, **graph of reasoning**02 Challenge - Agentic AI for a….
- **Maximizes scoring pillars**:
    - **Technical depth** → multi‑agent roles + contradiction detection + on‑demand verification.
    - **Creativity** → semantic map + suggested reads + live user intervention.
    - **Communication** → clean debate graph, insight cards, and a 1‑page report.
- **Scalable scope**: Advanced features are **off by default** and one‑click to enable; they don’t derail the MVP flow.

---

## F. Implementation notes (brief)

- **Role orchestration**: LangGraph/Assistants with stateful tools; JSON schemas for `Claim`, `Evidence`, `Insight`.
- **Interrupt‑without‑stop**: checkpoint after each graph node; user nudges add **control messages** to the queue for the next node; no pipeline flush needed.
- **STT**: Whisper or Cloud STT; user voice notes become “directives” addressed to Reviewer/Synthesizer.
- **Similarity map**: embeddings → UMAP + HDBSCAN; quick Plotly scatter; cluster labels via KeyBERT/LLM.
- **Recs**: centroid + gap‑queries → arXiv/OpenAlex; rerank; show “why”.
- **Verify**: retrieval + string‑window check + LLM verdict (Supported/Weak/Contradicted).

---

Topic of Study

### 🅰️ Pack A — **Urban Flood Mapping from Satellite (SAR vs Optical)**

**Why this is sexy for the demo**

- Striking **pre/post disaster imagery**; clean overlays of predicted flood masks; **cloud problems** make a compelling narrative; tons of open datasets (Sen1Floods11, C2S‑MS). [CVF Open Access+1](https://openaccess.thecvf.com/content_CVPRW_2020/papers/w11/Bonafilia_Sen1Floods11_A_Georeferenced_Dataset_to_Train_and_Test_Deep_Learning_CVPRW_2020_paper.pdf?utm_source=chatgpt.com)

**Hypotheses & paper pairs (support vs nuance/contradiction)**

**H1. “SAR (Sentinel‑1) is more robust than optical (Sentinel‑2) for rapid flood mapping under clouds.”**

- **Supports:** ArcGIS/Esri tutorial notes **post‑flood optical imagery is often cloud‑obscured**, making SAR preferable in real events. [ArcGIS Learn](https://learn.arcgis.com/en/projects/map-floods-with-sar-data-and-deep-learning/?utm_source=chatgpt.com)
- **Nuance/Counter:** A Europe‑wide study comparing **S1 vs S2** shows both can be effective; **effectiveness depends on event & conditions**—optical works when clouds are absent; best practice may be **combinational** use. [NHESS+1](https://nhess.copernicus.org/articles/22/2473/2022/?utm_source=chatgpt.com)

**H2. “Fusing SAR with elevation (DEM) or land‑cover improves delineation vs SAR alone.”**

- **Supports:** 2024–25 work shows **SAR + DEM + ML** improves **flood depth**/extent estimation. Urban mapping also improves when **SAR + LULC** handles **double‑bounce** artefacts. [ScienceDirect+1](https://www.sciencedirect.com/science/article/pii/S221458182400123X?utm_source=chatgpt.com)
- **Nuance/Counter:** Recent deep nets on **SAR‑only** (e.g., nested U‑Nets) achieve strong segmentation on public datasets—**additional layers may add complexity without universal gains**. [SpringerLink](https://link.springer.com/article/10.1007/s41064-024-00275-1?utm_source=chatgpt.com)

**H3. “Change‑detection (pre/post) generalizes better across events than single‑date classification.”**

- **Supports:** Threshold/ensemble change‑detection pipelines and **modified Sen1Floods11** for **bi‑temporal S1** back this claim. [PMC+1](https://pmc.ncbi.nlm.nih.gov/articles/PMC9988494/?utm_source=chatgpt.com)
- **Nuance/Counter:** A 2025 cross‑dataset evaluation shows **generalization varies** across **S1/S2/multispectral** and datasets; **transfer is non‑trivial**. [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S003442572500286X?utm_source=chatgpt.com)

**H4. “Crowdsourced/weak labels can meaningfully improve models where hand labels are scarce.”**

- **Supports:** *Street to Cloud* integrates **crowdsourcing + ML** to improve flood maps; strong “human‑in‑the‑loop” story. [Amazon Web Services, Inc.+1](https://s3.us-east-1.amazonaws.com/climate-change-ai/papers/neurips2020/34/paper.pdf?utm_source=chatgpt.com)
- **Nuance/Counter:** Weak labels still **introduce noise**—precision on edge cases (urban, double‑bounce) remains challenging; reviews emphasize these pitfalls. [MDPI](https://www.mdpi.com/2072-4292/16/4/656?utm_source=chatgpt.com)

**H5. “Long‑term SAR time series enables robust global mapping vs single‑event models.”**

- **Supports:** 2025 **Nature Communications** paper demonstrates **global flood mapping** with **Sentinel‑1** over a decade using DL change detection. [Nature](https://www.nature.com/articles/s41467-025-60973-1?utm_source=chatgpt.com)

**Datasets / Assets for our demo**

- **Sen1Floods11** (S1 chips + hand‑labels; global events)—perfect for “evidence with masks.” [CVF Open Access](https://openaccess.thecvf.com/content_CVPRW_2020/papers/w11/Bonafilia_Sen1Floods11_A_Georeferenced_Dataset_to_Train_and_Test_Deep_Learning_CVPRW_2020_paper.pdf?utm_source=chatgpt.com)
- **Cloud‑to‑Street / Microsoft Floods (C2S‑MS)** (paired S1/S2 + water labels) for **SAR vs Optical** comparisons. [Registry of Open Data+1](https://registry.opendata.aws/c2smsfloods/?utm_source=chatgpt.com)

**Visuals we’ll ship**

- Side‑by‑side **pre/post** scenes → predicted mask overlay; slider to compare **S1 vs S2 vs fused** predictions.
- **Contradiction matrix**: papers disagree on “fusion benefit” & “change detect vs single‑date”.
- **Semantic map**: clusters for “S1 DL segmentation,” “Fusion with DEM,” “Change detection.”
- **Suggested reads** with reasons (e.g., adds DEM in urban).

---

Optional Accessibility-

## Apply the *Winning Formula*: Social Impact + Accessibility + Multi‑Modality + Real User Problem

**Pick a high‑impact topic** (examples):

- **Urban Flood Mapping from Satellite**

**Accessibility & underserved users:**

- Insight Report includes a **plain‑language** section (CEFR‑B1) + **local language** summary (e.g., Spanish/Hindi) to support public officials/NGOs.

**Multiple modalities:**

- Text (papers) + **tables/CSVs** + **figures re‑plotted** (our micro‑experiment).
- Optional short **audio narration** of the final insight for non‑readers.

**Real user problem:**

- NGOs/public health teams needing **clear, evidence‑linked actions** *fast* before the next wave/outbreak.

This formula **fits perfectly** here without scope creep.