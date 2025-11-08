# Rösti 1D

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
- **4 agents with roles**: *Researcher* (extract claims), *Reviewer* (attack/verify), *Synthesizer* (assemble insights), *Red‑Team* (find contradictions). Agents message through a controllable graph.
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

---

USER POV

## A. What the user can do (end‑to‑end feature list)

### 1) Start a review

- **Upload papers (10–20)** as PDFs or paste arXiv/OpenAlex links.
- **Define a topic or prompt**: “What do papers say about LLMs for flood forecasting?”
- **Optionally seed guiding questions** (e.g., data requirements, limitations, evaluation metrics).

### 3) Watch the debate (live)

- **Debate Graph**: animated nodes (*Researcher → Reviewer → Red Team → Synthesizer*).
- **Live timeline**: messages stream in as the agents critique and refine.
- **Stage badges**: *Triage → Claims → Evidence Checks → Contradictions → Synthesis*.
- You can **hover any agent turn** to see the tool calls, snippets, and links.

> “Agents converse or message each other” and a visual graph of the reasoning flow are recommended in the challenge brief02 Challenge - Agentic AI for a….
> 

### 5) Inspect insights with receipts

- **Insight cards** with: *claim*, *confidence*, *supporting citations* (paper/page/quote), **badges** (Supported / Weak / Contradicted), and a **“See Evidence”** panel that highlights the exact lines in the PDF.
- **Why this conclusion?**: show which agent proposed it and who objected; who changed whose mind.

> “Verifiable reasoning” and sources/snippets for each insight are explicitly called out as stretch/hero behaviors
> 

### 7) Export and share

- **Collective Insight Report** (PDF/HTML/JSON) with a one‑page executive summary + appendix of claims, evidence, contradictions, and open questions.
- **Replay link** (optional): share a read‑only view of the debate timeline, so others can inspect reasoning steps (great for the judging “communication” pillar).
- **BibTeX/CSV** of sources used and suggested reads.

---

---

---

## D. UI sketch (user‑visible elements)

- **Left rail**: Topic, Corpus (paper list with quality badges)
- **Center**:
    - **Debate Graph** (hero) with a timeline scrubber.
    - **Insights** list; clicking an insight opens **Evidence Panel** (right).
- **Right**: Evidence viewer with PDF highlights; **Verify** tab (Supported/Weak/Contradicted); **Suggested Reads** with checkboxes to “Add to corpus”.
- **Footer**: Metrics mini‑dash (Citation Precision, Hallucination %, Coverage %, Cost/insight, Latency) and Export buttons.

The **graph of agent reasoning** and transparent **reasoning traces** are exactly what the challenge suggests as strong demo artifacts

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
- **Verify**: retrieval + string‑window check + LLM verdict (Supported/Weak/Contradicted).

---

 Accessibility-

## Apply the *Winning Formula*: Social Impact + Accessibility + Multi‑Modality + Real User Problem

**Pick a high‑impact topic** (examples):

- **Urban Flood Mapping from Satellite**

**Real user problem:**

- NGOs/public health teams needing **clear, evidence‑linked actions** *fast* before the next wave/outbreak.

This formula **fits perfectly** here without scope creep.

---

Topic of Study

# Pack A — **Urban Flood Mapping from Satellite (SAR vs Optical)**

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



# Pack B: Urban Environmental Justice in Smart Cities
## Overview
This topic connects **urban data science**, **IoT applications**, **remote sensing**, and **social equity** to examine how technological innovation reshapes urban environmental justice.  
Recent debates focus on whether smart city tools close gaps in justice, accessibility, and civic engagement — or further widen them.

---

## Hypothesis 1
### “Urban computing reveals climate vulnerability hotspots and guides fair resource allocation.”

#### Supporting Evidence
1. **Frontiers in Built Environment (2022)** – *Remote sensing and socio-economic analysis of urban heat islands and inequality dynamics.*  
   [PDF](https://www.frontiersin.org/articles/10.3389/fbuil.2022.861485/pdf)
2. **ArXiv Preprint (2021)** – *Remote sensing and AI for building climate adaptation applications.*  
   [PDF](https://arxiv.org/pdf/2107.02693.pdf)
3. **ScienceDirect (2023)** – *Urban climate variability and remote sensing applications for social-environmental mapping.*  
   [PDF](https://reader.elsevier.com/reader/sd/pii/S2405844023002772?token=5333F0D6B45E457D8A79634DE67D2C73DC5D75EE2A393D1D53F85AD2A967E44B63C43A23CE1D5BFE1B52CFCE71FB890A&originRegion=eu-west-1&originCreation=20231123123827)
4. **DLR (2019)** – *Urban climate analysis integrating satellite and ground-level meteorological data for heat mitigation.*  
   [PDF](https://elib.dlr.de/130915/1/Masson_Heldens_etal_UrbanClimate_2019.pdf)

#### Nuanced / Counter Perspectives
5. **Cogitatio Press (2024)** – *Reframing Urban Nature-Based Solutions through Environmental Justice.*  
   [PDF](https://www.cogitatiopress.com/urbanplanning/article/download/6374/6374)
6. **Umwelt Bundesamt (2015)** – *Environmental Justice in Urban Areas: Synthesizing health and environmental data for policy alignment.*  
   [Full text PDF](https://www.umweltbundesamt.de/sites/default/files/medien/378/publikationen/umwelt_und_gesundheit_01_2015_summary.pdf)
7. **OAPEN (2021)** – *Urban Sustainability and Justice.*  
   [PDF](https://library.oapen.org/handle/20.500.12657/23377)
8. **University of Groningen Journal (2023)** – *Participatory risk mapping and urban environmental governance.*  
   [Open Access](https://ugp.rug.nl/potcj/article/view/41048)

**Current count:** 8 sources  
→ To reach 10, add two more open-access review or case-study articles from *Frontiers*, *MDPI*, or *Urban Climate (Elsevier)* on vulnerability mapping or equity-driven adaptation planning.

---

## Hypothesis 2
### “Technology deployment often reproduces inequities due to uneven infrastructure and data accessibility.”

#### Supporting Evidence
1. **MDPI Sustainability (2023)** – *Smart city inequality and IoT sensor distribution across neighborhoods.*  
   [PDF](https://www.mdpi.com/2071-1050/15/3/1962/pdf)
2. **TU Delft IET Smart Cities (2024)** – *Hierarchies of urban sensing: distributional inequity in networked infrastructure.*  
   [PDF](https://pure.tudelft.nl/ws/portalfiles/portal/160762935/Kumar_et_al_2024_Internet_of_Things.pdf)
3. **RSIS International (2023)** – *Smart Cities and Internet of Things: Review of developments, challenges, and social gaps.*  
   [PDF](https://www.rsisinternational.org/journals/ijrsi/articles/smart-cities-and-internet-of-things-iot-a-review-of-recent-developments-challenges-and-opportunities.pdf)
4. **TU Delft (2024)** – *Sense and the City: From IoT sensors and open data platforms to urban inclusion.*  
   [PDF](https://pure.tudelft.nl/ws/portalfiles/portal/209254661/IET_Smart_Cities_-_2024_-_Kumar_-_Sense_and_the_city_From_Internet_of_Things_sensors_and_open_data_platforms_to_urban.pdf)

#### Nuanced / Counter Perspectives
5. **DIVA Portal (2024)** – *IoT applications and challenges in smart cities.*  
   [PDF](https://www.diva-portal.org/smash/get/diva2:1765956/FULLTEXT01.pdf)
6. **Library OAPEN (2021)** – *Urban Sustainability and Justice: Practical frameworks for equitable smart transition.*  
   [PDF](https://library.oapen.org/bitstream/handle/20.500.12657/58830/9781786994943.pdf?sequence=1&isAllowed=y)
7. **RSIS International (2024)** – *Smart Cities and IoT: Addressing emerging technologies and socio-ethical challenges.*  
   [Full PDF](https://rsisinternational.org/journals/ijriss/articles/smart-cities-and-internet-of-things-iot-a-review-of-emerging-technologies-and-challenges/)
8. **Cogitatio Press (2023)** – *Citizen co-design and platform equity in digital cities.*  
   [Full Text](https://www.cogitatiopress.com/urbanplanning/article/view/6018)

**Current count:** 8 sources  
→ To reach 10, locate additional papers on digital infrastructure equity or participatory IoT governance (try *IEEE Access*, *MDPI Smart Cities*, or *Urban Informatics*).


---

# 📱 Pack C: Smartphone Use and Cognitive Function

## Overview
This topic explores how **smartphone usage**, **digital dependence**, and **AI-assisted tools** influence **human cognition**, **attention**, and **behavioral outcomes**.  
The literature reflects both supportive and nuanced perspectives: while many studies associate heavy phone use with reduced cognitive control or focus, others emphasize context-dependent effects such as cognitive offloading and adaptive multitasking.

---

## Hypothesis 1  
### “Smartphone dependence and presence impair attention, memory, and executive function.”

#### Supporting Evidence
1. **M. L. Méndez et al. (2024)** – *Effects of Internet and Smartphone Addiction on Cognitive Performance.*  
   [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0149763424000411)  
   Correlates smartphone/internet addiction with lower cognitive test performance in college students.

2. **G. Niu et al. (2022)** – *Can Smartphone Presence Affect Cognitive Function?*  
   [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0747563222002217)  
   Experimental “brain drain” study — proximity of smartphones reduces working memory and attention.

3. **H. H. Wilmer et al. (2017)** – *Smartphones and Cognition: A Review of Research.*  
   [PMC (NCBI)](https://pmc.ncbi.nlm.nih.gov/articles/PMC5403814/)  
   Meta-analysis summarizing cognitive impacts across attention, memory, and learning domains.

4. **J. Skowronek et al. (2023)** – *The Mere Presence of a Smartphone Results in Lower Cognitive Performance.*  
   [Nature](https://www.nature.com/articles/s41598-023-36256-4)  
   Controlled lab study measuring decreased working memory when smartphones are visible but unused.

5. **A. Al-Amri et al. (2023)** – *Effects of Smartphone Addiction on Cognitive Function and Physical Activity in Middle-School Children.*  
   [Frontiers in Psychology](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2023.1182749/full)  
   Finds smartphone addiction linked to lower executive function and reduced physical activity in adolescents.

6. **N. Talaei et al. (2024)** – *The Impact of Smartphone Addiction on Cognitive and Driving Behavior.*  
   [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5153559)  
   Driving simulator study showing increased reaction times and distraction under phone exposure.

#### Nuanced / Counter Perspectives
7. **M. Gerlich et al. (2025)** – *AI Tools in Society: Impacts on Cognitive Offloading and Human Dependence.*  
   [MDPI](https://www.mdpi.com/3119574)  
   Suggests “digital offloading” can sometimes optimize performance, paralleling smartphone-based cognitive outsourcing.

8. **Novel Smartphone Interventions Improve Cognitive Flexibility and OCD Symptoms in Individuals with Contamination Fears**  
   *(2024, Journal TBD)*  
   Demonstrates therapeutic use of smartphone apps for enhancing cognitive flexibility — showing positive effects of digital intervention.

9. **All Extern? Exploring the Impact of Social Media and Physical Activity on Adolescents’ Body Image and Interoception**  
   *(2024, Preprint or Early View)*  
   Investigates interaction effects — smartphone/social media use moderated by physical activity on body image and perception.

10. **The Association Between Real-Life Markers of Phone Use and Cognitive Performance, Health-Related Quality of Life, and Sleep**  
    [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0013935123008034)  
    Large-scale observational study linking objective phone-use data with cognitive and lifestyle outcomes.

---

## Summary Insights
- **Converging Evidence:** Heavy smartphone presence or dependence consistently correlates with reduced working memory and sustained attention.  
- **Age Sensitivity:** Effects are stronger in adolescents and young adults, potentially moderated by self-regulation development.  
- **Positive Interventions:** Targeted or therapeutic smartphone use (e.g., CBT apps) can enhance cognitive flexibility or reduce symptoms.  
- **Emergent Trend:** Cognitive offloading — shifting memory or decision load to digital tools — introduces a new debate on *functional vs. detrimental* dependence.

---

## Suggested Extensions
- Use **EEG datasets** or **digital behavior tracking APIs** for multimodal replication.  
- Integrate **AI-driven digital well-being assistants** (e.g., usage prediction, screen-time adaptation).  
- Explore **cross-domain parallels**: compare smartphone effects to **AI cognitive tools** (as in Gerlich et al., 2025).

---

**Current count:** 10 sources  
→ To expand: include meta-reviews from *Frontiers in Psychology*, *MDPI Behavioral Sciences*, or *Nature Human Behaviour* on **cognitive offloading**, **screen dependency**, or **AI-mediated attention**.
