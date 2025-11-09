# Rosti_Agentic_AI_for_Research

An advanced multi-agent AI system for research paper analysis with interactive PDF viewing and citation highlighting.

## Features

### 🤖 Multi-Agent Reasoning
- **Researcher Agent**: Extracts and analyzes claims from research papers
- **Reviewer Agent**: Validates and verifies claims with confidence scoring
- **Red Team Agent**: Identifies challenges, contradictions, and gaps
- **Synthesizer Agent**: Combines insights and proposes next steps

### 📊 Interactive Results Dashboard
- **Key Insights**: Synthesized findings with confidence levels
- **Concerns/Challenges**: Identified issues with severity ratings
- **Next Steps**: Recommended actions (Hypotheses, Next Steps, Clarifications)

### 📄 Advanced PDF Viewer
- **Click-to-View**: Click any citation to open the PDF viewer
- **Page Navigation**: Navigate to the exact page referenced in citations
- **Text Highlighting**: Automatically highlights cited text (based on character positions)
- **Zoom Controls**: Zoom in/out for better readability
- **Inline Display**: PDFs open in a modal overlay for seamless workflow

### 🎨 Modern UI/UX
- Real-time processing updates with Server-Sent Events (SSE)
- Responsive design with Tailwind CSS
- Smooth animations and transitions
- Dark mode optimized

## Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Running the Application

```bash
# Start the server
uvicorn app.main:app --reload

# Access at http://localhost:8000
```

## PDF Viewer Setup

The application automatically:
1. Saves uploaded PDFs to the `pdfs/` directory
2. Serves PDFs via the `/pdfs/{filename}` endpoint
3. Renders PDFs using PDF.js with citation highlighting

### Backend Citation Format

Citations should include:
```python
{
  "source_id": "paper.pdf",
  "page": 5,
  "char_start": 120,
  "char_end": 450,
  "quote": "Excerpt from the paper...",
  "chunk_id": "paper.pdf:p0005:c0001",
  "chunk_text": "Full context..."
}
```

## Project Structure

```
├── app/
│   ├── main.py              # FastAPI application
│   ├── vectorstore.py       # Vector store utilities
│   ├── components/          # Reusable components
│   ├── static/
│   │   └── style.css        # Custom styles
│   └── templates/
│       ├── base.html        # Base template with PDF.js
│       ├── index.html       # Upload form
│       └── result.html      # Results dashboard with PDF viewer
├── pdfs/                    # Uploaded PDF storage (gitignored)
├── requirements.txt
└── README.md
```

## Technology Stack

- **Backend**: FastAPI, Python
- **Frontend**: HTML, Tailwind CSS, HTMX
- **PDF Rendering**: PDF.js
- **Real-time Updates**: Server-Sent Events (SSE)

## Usage

1. **Upload PDFs**: Select one or more research papers
2. **Ask Question**: Enter your research query
3. **View Results**: Explore Key Insights, Challenges, and Next Steps
4. **Click Citations**: Click any citation to view the source PDF with highlighting
5. **Navigate PDFs**: Use page controls and zoom to explore the document

## Citation Highlighting

The PDF viewer automatically:
- Opens to the cited page
- Highlights the relevant text based on character positions
- Displays a pulsing yellow highlight for easy identification
- Shows citation context in the modal

## Future Enhancements

- [ ] Multi-file citation cross-referencing
- [ ] Annotation and note-taking in PDFs
- [ ] Export reports with embedded citations
- [ ] Advanced search within PDFs
- [ ] Collaborative review features

## License

MIT License
