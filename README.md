# Trade Nexus CLI

A standalone Python CLI that replicates all Gemini-powered intelligence from the **Trade Nexus AI Sales Agent** web app — no browser, no Firebase, pure terminal.

---

## Setup

### 1. Install dependencies

```bash
cd tradenexus-cli
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and set GEMINI_API_KEY=your_key
```

---

## Commands

| Command | Description |
|---|---|
| `python main.py analyze-markets` | Find top 9 export regions for your product |
| `python main.py market-report` | Full market intelligence report (with Google Search) |
| `python main.py search-leads` | Multi-vector 4-squad lead discovery |
| `python main.py verify-lead` | Verify a company's legitimacy via Google Search + Maps |
| `python main.py prospect` | Interactive SDR chat assistant for a specific lead |
| `python main.py extract-context <files>` | Analyse product PDFs/images → Strategic Memory |
| `python main.py sessions list` | List all saved sessions |
| `python main.py sessions show <id>` | Show session details and leads |
| `python main.py sessions export <id>` | Export leads to CSV or JSON |
| `python main.py info` | Show current model config and API key status |

---

## Typical Workflow

```bash
# Step 1: Analyse your product documents for strategic context
python main.py extract-context catalogue.pdf spec_sheet.png
# → Creates session e.g. "abc12345"

# Step 2: Discover top export markets
python main.py analyze-markets --session abc12345 --continent Asia

# Step 3: Get a detailed market report for a specific region
python main.py market-report --session abc12345 --region "Vietnam"

# Step 4: Search for leads in that region
python main.py search-leads --session abc12345 --export-csv leads.csv

# Step 5: Verify a specific company
python main.py verify-lead --session abc12345

# Step 6: Open SDR assistant to draft outreach for a lead
python main.py prospect --session abc12345
```

---

## Session Persistence

Sessions are saved to `~/.tradenexus/sessions/<id>.json`.  
Each session stores your product config, strategic context, discovered leads, and region suggestions.  
Use `--session <id>` on any command to carry context across steps.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | *(required)* | Google Gemini API key |
| `GEMINI_DEFAULT_MODEL` | `gemma-4-31b-it` | Model for generation/analysis |
| `GEMINI_GROUNDING_MODEL` | `gemma-4-31b-it` | Model for Google Search grounding |
| `GEMINI_THINKING_BUDGET` | `0` (disabled) | Thinking token budget (0=off, -1=dynamic) |

---

## Architecture

```
tradenexus-cli/
├── main.py                  # Typer CLI entry point
├── requirements.txt
├── .env.example
└── tradenexus/
    ├── config.py            # Env config (port of TS getAiClient())
    ├── models.py            # Dataclasses (port of types.ts)
    ├── gemini_service.py    # All AI functions (port of geminiService.ts)
    ├── output.py            # Rich terminal display helpers
    ├── session.py           # Local JSON session persistence
    └── utils.py             # JSON extraction, grounding helpers
```
