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

## Intelligence layer (APIs)

If we want to build a powerful Intelligence Layer using publicly available or free-tier APIs (avoiding expensive commercial licenses like ZoomInfo or Panjiva), there are several excellent open data sources we can leverage for the import/export sector.
Here are the best publicly available APIs categorized by the intelligence they provide:

### 1. Global Trade & Tariff Intelligence

**UN Comtrade API**: The gold standard for global trade data. It offers a free public tier that allows you to query import and export volumes, trade values (in USD), and trade flows between specific countries using HS (Harmonized System) codes. This could automatically populate the "Trade Volume" or market demand charts in your app.

**World Bank WITS (World Integrated Trade Solution) API**: Completely free and open. It provides detailed data on bilateral trade, tariff rates, and non-tariff measures.
ITA (International Trade Administration) APIs: Provided by the US Government (free to use). They offer several useful endpoints for B2B exporters:
Tariff Search: Look up tariffs for specific HS codes.

**Consolidated Screening List (CSL)**: Crucial for compliance. You can use this to automatically screen generated leads to ensure they aren't on any international sanctions or embargo lists.

### 2. Company Verification & Firmographics

**OpenCorporates API**: The largest open database of companies in the world. They have a free/public-benefit tier that can be used to verify if a generated lead is a legally registered entity, retrieve their incorporation date, active status, and registered address.

**UK Companies House API (and similar regional registries)**: 100% free and open REST API. If you search for leads in the UK, this API can pull their exact financial filings, officer names (for direct contacts), and incorporation status without paying a dime. Many EU countries and some US states have similar open registries.

### 3. Financial Health & Scale

**SEC EDGAR REST API**: Completely free. If the lead is a publicly traded company (or a subsidiary of one) in the US, you can programmatically pull their exact revenue, employee count, and risk factors from their most recent 10-K filings.

**Yahoo Finance API (Community/Free Tiers)**: Useful for pulling market capitalization or recent financial news for larger corporate leads to gauge their buying power.

### 4. Market Sentiment & Supply Chain Disruption

**The GDELT Project**: A massive, free, open dataset that monitors global news, events, and sentiment in real-time. It can be queried to detect if there are supply chain disruptions, port strikes, or economic booms in the user's specific target region.

**Google News RSS / Media RSS**: By programmatically parsing RSS feeds for the target product ("Lithium-ion batteries") in the target region, the intelligence layer can surface real-time market opportunities or competitor news right on the dashboard.

### How we could implement this right now:
Since we are already using Gemini as our primary reasoning engine, we can use the Function Calling (Tools) feature to give Gemini access to these public APIs.
For example, we could build a tool that:
Takes the HS Code for the user's product.
Calls the UN Comtrade API to fetch exactly how many millions of dollars of that product are imported into their target region annually.
Calls the ITA Screening API to automatically flag any lead that might be under trade sanctions.

## Consulting

To elevate the market intelligence from a "rapid AI summary" to a Consulting-Grade Deep Dive (similar to what firms like McKinsey or Gartner provide), the platform would need to transition from single-prompt generation to a Multi-Agent, Data-Backed Research Pipeline.
Here are the key areas you would need to focus on:

### 1. Hard Quantitative Data Integration (API Layer)

Consulting reports are heavily backed by statistics. Instead of relying solely on an LLM's pre-trained knowledge, the agents would need tools to query real-time statistical databases:

- **Trade Flows**: Integrating with the UN Comtrade API or World Bank API to show exact historical import/export volumes and values for the specific HS Code in that region.

- **Demand Seasonality**: Using the Google Trends API to chart consumer interest over the last 5 years.

- **Financial Health**: Using APIs like Alpha Vantage or Clearbit to analyze the revenue growth of key competitors in the region.

### 2. Multi-Agent Research Topologies

Instead of a single AI call generating the whole report, you would build a "Virtual Consulting Team" where multiple specialized agents run in parallel:

- **The Economist Agent**: Queries trade APIs, calculates Total Addressable Market (TAM), and projects growth scenarios (Bull vs. Bear cases).

- **The Regulatory Agent**: Specifically searches official government customs databases to find exact tariff percentages, certification requirements (like CE, FCC, or ISO), and recent legislative changes.
  
- **The Supply Chain Agent**: Analyzes shipping routes, calculates precise landed costs, and identifies logistical bottlenecks (e.g., typical delays at specific ports).

- **The Lead Consultant Agent**: Merges all these sub-reports into one cohesive, executive-ready narrative.

### 3. Agentic Competitor Teardowns

Consulting reports tell you exactly who you are fighting. You could introduce a tool that allows the AI to:

- Identify the top 3 local competitors.

- Visit and scrape their actual websites/e-commerce stores.

- Extract their exact pricing, feature lists, and warranty terms.

- Generate a comparative matrix (SWOT Analysis) showing exactly where your product wins or loses against them.

### 4. Supply Chain & Landed Cost Modeling

A major part of market entry is the financial model. You could build algorithms that take:

- Your FOB Price + Estimated Freight (via an API like Freightos) + Actual Import Duty (via customs APIs) + Local Taxes = Total Landed Cost.

- The AI would then compare this Landed Cost against the local retail price to calculate the exact profit margins a distributor could expect, which is the ultimate data point needed to close a B2B deal.

### 5. Interactive & Exportable Visualizations

Consulting reports are visually compelling. The frontend would need to render complex data structures:

- Dynamic line charts for historical import growth.

- Scatter plots mapping competitors by Price vs. Quality.

- The ability to export these dynamically generated charts into a branded, 20-page PDF presentation deck, complete with executive summaries and citations for every data point.
Next Steps:
If you wanted to start building towards this today, the highest-value first step would be Multi-Agent Research—chaining multiple Google Grounding searches together focusing specifically on Competitor Pricing and exact Trade Volumes, before synthesizing the final output.
