# Rosti_Agentic_AI_for_Research

An advanced multi-agent AI system for research paper analysis with interactive PDF viewing and citation highlighting.

## Features

### 🤖 Multi-Agent Reasoning

- **Researcher Agent**: Extracts and analyzes claims from research papers
- **Reviewer Agent**: Validates and verifies claims with confidence scoring
- **Red Team Agent**: Identifies challenges, contradictions, and gaps
- **Synthesizer Agent**: Combines insights and proposes next steps
- **Debating**: Agents debate key points to enhance analysis quality

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

## License

MIT License
