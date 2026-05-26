"""Shared Streamlit theme for the TradeNexus dashboard."""

APP_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;600;700;800&display=swap');

:root {
    --bg: #06101f;
    --panel: rgba(8, 17, 34, 0.92);
    --panel-2: rgba(10, 23, 46, 0.95);
    --border: rgba(70, 188, 255, 0.18);
    --border-strong: rgba(255, 78, 205, 0.25);
    --text: #e6eef9;
    --muted: #8da5c3;
    --cyan: #2de2e6;
    --blue: #62b0ff;
    --pink: #ff4ecd;
    --green: #3ee38f;
    --amber: #ffbf69;
    --red: #ff6b81;
}

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background:
        radial-gradient(circle at top left, rgba(45, 226, 230, 0.08), transparent 28%),
        radial-gradient(circle at top right, rgba(255, 78, 205, 0.10), transparent 24%),
        linear-gradient(180deg, #040b17 0%, #08101d 38%, #091223 100%);
    color: var(--text);
}

.block-container {
    padding-top: 1.1rem;
    padding-bottom: 2rem;
}

section[data-testid="stSidebar"] {
    background:
        radial-gradient(circle at top, rgba(45, 226, 230, 0.08), transparent 28%),
        linear-gradient(180deg, #08101a 0%, #0c1526 100%);
    border-right: 1px solid rgba(98, 176, 255, 0.16);
}

section[data-testid="stSidebar"] * {
    color: var(--text) !important;
}

.sidebar-brand {
    padding: 0.75rem 0 0.25rem 0;
}

.sidebar-kicker {
    color: var(--cyan);
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    font-weight: 700;
}

.sidebar-title {
    font-family: 'Outfit', sans-serif;
    font-size: 1.45rem;
    font-weight: 800;
    color: #ffffff;
    margin: 0.15rem 0;
}

.sidebar-copy {
    color: var(--muted);
    font-size: 0.82rem;
    line-height: 1.5;
}

.sidebar-section-title {
    color: #d6e6ff;
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.11em;
    margin-bottom: 0.55rem;
}

.source-node {
    background: rgba(10, 19, 36, 0.72);
    border: 1px solid rgba(98, 176, 255, 0.14);
    border-radius: 10px;
    padding: 0.55rem 0.75rem;
    margin-bottom: 0.45rem;
}

.source-node strong {
    display: block;
    color: #eef4ff;
    font-size: 0.82rem;
    margin-bottom: 0.12rem;
}

.source-node span {
    color: var(--muted);
    font-size: 0.76rem;
    line-height: 1.45;
}

.terminal-shell {
    border: 1px solid rgba(98, 176, 255, 0.18);
    background:
        linear-gradient(180deg, rgba(5, 12, 25, 0.98) 0%, rgba(6, 14, 30, 0.94) 100%);
    border-radius: 18px;
    overflow: hidden;
    box-shadow: 0 24px 60px rgba(0, 0, 0, 0.35);
    margin-bottom: 1.4rem;
}

.terminal-shell-compact {
    border-radius: 14px;
}

.macro-topline {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: center;
    padding: 0.55rem 0.95rem;
    border-bottom: 1px solid rgba(98, 176, 255, 0.14);
    background: linear-gradient(90deg, rgba(9, 18, 34, 0.98), rgba(14, 24, 47, 0.96));
}

.macro-topline-left,
.macro-topline-right {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    flex-wrap: wrap;
}

.brand-led {
    width: 10px;
    height: 10px;
    border-radius: 999px;
    background: linear-gradient(180deg, var(--pink), var(--cyan));
    box-shadow: 0 0 18px rgba(255, 78, 205, 0.5);
}

.macro-app-name {
    font-family: 'Outfit', sans-serif;
    font-size: 1.05rem;
    font-weight: 700;
    color: #f8fbff;
}

.macro-app-tag {
    color: var(--muted);
    font-size: 0.78rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}

.status-badge {
    display: inline-flex;
    align-items: center;
    padding: 0.2rem 0.55rem;
    border-radius: 8px;
    border: 1px solid rgba(98, 176, 255, 0.18);
    background: rgba(255, 255, 255, 0.02);
    color: #dfeaf8;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 700;
}

.status-badge.pink {
    color: #ffd7f3;
    border-color: rgba(255, 78, 205, 0.24);
    background: rgba(255, 78, 205, 0.08);
}

.shell-topbar {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: center;
    padding: 0.8rem 1rem;
    border-bottom: 1px solid rgba(98, 176, 255, 0.16);
    background: linear-gradient(90deg, rgba(13, 25, 48, 0.96), rgba(14, 22, 40, 0.96));
}

.shell-brand {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
}

.shell-kicker {
    color: var(--cyan);
    font-size: 0.7rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    font-weight: 700;
}

.shell-title {
    font-family: 'Outfit', sans-serif;
    font-size: 1.45rem;
    font-weight: 800;
    color: #ffffff;
    line-height: 1;
}

.shell-status {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
    align-items: center;
    justify-content: flex-end;
}

.terminal-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    background: rgba(45, 226, 230, 0.08);
    border: 1px solid rgba(45, 226, 230, 0.2);
    border-radius: 999px;
    padding: 0.28rem 0.65rem;
    color: #dffcff;
    font-size: 0.76rem;
    font-weight: 600;
}

.terminal-chip.pink {
    background: rgba(255, 78, 205, 0.08);
    border-color: rgba(255, 78, 205, 0.22);
    color: #ffd8f5;
}

.market-ticker {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
    padding: 0.65rem 1rem;
    border-bottom: 1px solid rgba(98, 176, 255, 0.14);
    background: rgba(7, 17, 33, 0.92);
}

.ticker-item {
    font-family: 'Outfit', sans-serif;
    font-size: 0.82rem;
    padding: 0.26rem 0.55rem;
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.02);
    color: #dbe9ff;
}

.ticker-item span {
    color: var(--green);
}

.ticker-item.down span {
    color: var(--red);
}

.command-ribbon {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    margin: 0.8rem 1rem 0.65rem 1rem;
    padding: 0.8rem 1rem;
    border-radius: 12px;
    border: 1px solid rgba(98, 176, 255, 0.2);
    background: linear-gradient(90deg, rgba(10, 18, 34, 0.94), rgba(10, 24, 48, 0.92));
}

.command-label {
    font-family: 'Outfit', sans-serif;
    font-size: 0.82rem;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--muted);
    white-space: nowrap;
}

.command-value {
    color: #f4fbff;
    font-size: 0.92rem;
    letter-spacing: 0.03em;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.command-console {
    box-shadow: inset 0 0 0 1px rgba(45, 226, 230, 0.04);
}

.command-prompt::before {
    content: ">_";
    color: var(--cyan);
    margin-right: 0.7rem;
    font-weight: 800;
}

.desk-nav {
    display: flex;
    gap: 0.55rem;
    flex-wrap: wrap;
    padding: 0 1rem 0.75rem 1rem;
}

.desk-button {
    display: inline-flex;
    align-items: center;
    padding: 0.42rem 0.72rem;
    border-radius: 9px;
    border: 1px solid rgba(98, 176, 255, 0.14);
    background: rgba(7, 16, 31, 0.82);
    color: #c9d9ef;
    font-size: 0.78rem;
    font-weight: 700;
}

.desk-button.active {
    border-color: rgba(45, 226, 230, 0.26);
    background: rgba(45, 226, 230, 0.09);
    color: #dcfeff;
}

.terminal-summary-row {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.75rem;
    padding: 0 1rem 1rem 1rem;
}

.terminal-summary-card {
    background: linear-gradient(180deg, rgba(8, 17, 34, 0.96), rgba(10, 20, 40, 0.98));
    border: 1px solid rgba(98, 176, 255, 0.14);
    border-radius: 12px;
    padding: 0.78rem 0.9rem;
}

.terminal-summary-label {
    color: var(--muted);
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
}

.terminal-summary-value {
    margin-top: 0.22rem;
    font-family: 'Outfit', sans-serif;
    font-size: 1.22rem;
    font-weight: 700;
    color: #fbfdff;
}

.terminal-summary-sub {
    margin-top: 0.22rem;
    font-size: 0.76rem;
    font-weight: 600;
}

.terminal-summary-sub.cyan { color: var(--cyan); }
.terminal-summary-sub.pink { color: var(--pink); }
.terminal-summary-sub.green { color: var(--green); }
.terminal-summary-sub.amber { color: var(--amber); }

.hero-grid {
    display: grid;
    grid-template-columns: minmax(0, 2fr) minmax(260px, 1.1fr);
    gap: 1rem;
    padding: 0 1rem 1rem 1rem;
}

.hero-panel {
    background: linear-gradient(180deg, rgba(10, 21, 42, 0.86), rgba(10, 18, 34, 0.88));
    border: 1px solid rgba(98, 176, 255, 0.16);
    border-radius: 16px;
    padding: 1.1rem 1.2rem;
    min-height: 100%;
}

.hero-grid-compact {
    padding-top: 0;
}

.hero-panel-note {
    display: flex;
    align-items: center;
}

.hero-copy h1 {
    font-family: 'Outfit', sans-serif;
    font-size: 2.35rem;
    line-height: 1.05;
    margin: 0 0 0.55rem 0;
    color: #ffffff;
}

.hero-copy h1 span {
    color: var(--cyan);
    text-shadow: 0 0 18px rgba(45, 226, 230, 0.15);
}

.hero-copy p {
    color: var(--muted);
    font-size: 0.98rem;
    line-height: 1.6;
    margin: 0;
    max-width: 50rem;
}

.hero-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
    margin-top: 1rem;
}

.hero-badge {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(98, 176, 255, 0.16);
    border-radius: 999px;
    padding: 0.28rem 0.65rem;
    font-size: 0.76rem;
    font-weight: 600;
    color: #d7e8ff;
}

.metric-strip {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.7rem;
}

.metric-tile {
    background: linear-gradient(180deg, rgba(8, 17, 34, 0.96), rgba(10, 20, 40, 0.98));
    border: 1px solid rgba(98, 176, 255, 0.14);
    border-radius: 14px;
    padding: 0.8rem 0.9rem;
}

.metric-caption {
    color: var(--muted);
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 0.35rem;
}

.metric-number {
    font-family: 'Outfit', sans-serif;
    font-size: 1.35rem;
    font-weight: 700;
    color: #f5fbff;
}

.metric-delta {
    margin-top: 0.25rem;
    font-size: 0.78rem;
    font-weight: 600;
}

.metric-delta.cyan { color: var(--cyan); }
.metric-delta.pink { color: var(--pink); }
.metric-delta.green { color: var(--green); }
.metric-delta.amber { color: var(--amber); }
.metric-delta.red { color: var(--red); }

.kpi-card {
    background: linear-gradient(180deg, rgba(8, 19, 38, 0.92), rgba(10, 17, 30, 0.98));
    border: 1px solid rgba(98, 176, 255, 0.16);
    border-radius: 14px;
    padding: 1rem 1.1rem;
    min-height: 100%;
}

.kpi-label {
    font-size: 0.72rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-weight: 600;
    margin-bottom: 0.4rem;
}

.kpi-value {
    font-family: 'Outfit', sans-serif;
    font-size: 1.72rem;
    font-weight: 700;
    color: var(--cyan);
    line-height: 1.05;
}

.kpi-sub {
    font-size: 0.8rem;
    color: var(--green);
    margin-top: 0.35rem;
}

.kpi-sub.negative {
    color: var(--red);
}

.section-intro {
    margin: 0.2rem 0 1rem 0;
    padding: 1rem 1.05rem;
    border-radius: 16px;
    border: 1px solid rgba(98, 176, 255, 0.12);
    background: linear-gradient(180deg, rgba(7, 15, 28, 0.78), rgba(7, 14, 26, 0.54));
}

.section-kicker {
    color: var(--cyan);
    font-size: 0.73rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.14em;
}

.section-title {
    font-family: 'Outfit', sans-serif;
    font-size: 1.45rem;
    font-weight: 700;
    color: #ffffff;
    margin-top: 0.22rem;
}

.section-copy {
    color: var(--muted);
    font-size: 0.92rem;
    line-height: 1.55;
    margin-top: 0.28rem;
}

.panel-shell {
    margin: 0 0 0.65rem 0;
    padding: 0.9rem 1rem;
    border-radius: 14px;
    border: 1px solid rgba(98, 176, 255, 0.13);
    background: linear-gradient(180deg, rgba(7, 16, 31, 0.82), rgba(6, 12, 22, 0.76));
}

.panel-title-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 0.85rem;
}

.panel-title {
    font-family: 'Outfit', sans-serif;
    color: #f7fbff;
    font-size: 1.02rem;
    font-weight: 700;
}

.panel-subtitle {
    color: var(--muted);
    font-size: 0.8rem;
    line-height: 1.5;
    margin-top: 0.15rem;
}

.panel-tag {
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--cyan);
    background: rgba(45, 226, 230, 0.08);
    border: 1px solid rgba(45, 226, 230, 0.18);
    border-radius: 999px;
    padding: 0.22rem 0.52rem;
    white-space: nowrap;
}

.news-feed {
    border: 1px solid rgba(98, 176, 255, 0.12);
    border-radius: 14px;
    background: linear-gradient(180deg, rgba(9, 18, 35, 0.9), rgba(7, 13, 24, 0.88));
    overflow: hidden;
}

.news-row {
    display: grid;
    grid-template-columns: 56px minmax(0, 1fr);
    gap: 0.7rem;
    padding: 0.75rem 0.9rem;
    border-bottom: 1px solid rgba(98, 176, 255, 0.08);
}

.news-row:last-child {
    border-bottom: none;
}

.news-time {
    font-family: 'Outfit', sans-serif;
    color: var(--muted);
    font-size: 0.78rem;
}

.news-copy {
    color: #dfeaf8;
    font-size: 0.84rem;
    line-height: 1.48;
}

.news-copy strong,
.insight-box strong {
    color: #f5fbff;
    font-weight: 700;
}

.inline-code {
    display: inline-block;
    padding: 0.02rem 0.35rem;
    border-radius: 6px;
    background: rgba(98, 176, 255, 0.1);
    border: 1px solid rgba(98, 176, 255, 0.12);
    color: #dffcff;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 0.82em;
}

.source-tree {
    display: flex;
    flex-direction: column;
    gap: 0.8rem;
    min-height: 100%;
}

.tree-group {
    border: 1px solid rgba(98, 176, 255, 0.12);
    border-radius: 12px;
    background: linear-gradient(180deg, rgba(8, 16, 31, 0.9), rgba(6, 13, 24, 0.92));
    padding: 0.8rem 0.9rem;
}

.tree-group-title {
    font-family: 'Outfit', sans-serif;
    color: #f7fbff;
    font-size: 0.92rem;
    font-weight: 700;
    margin-bottom: 0.45rem;
}

.tree-item {
    position: relative;
    padding-left: 1rem;
    margin: 0.24rem 0;
    color: var(--muted);
    font-size: 0.82rem;
    line-height: 1.45;
}

.tree-item::before {
    content: "›";
    position: absolute;
    left: 0;
    color: var(--cyan);
    font-weight: 700;
}

.matrix-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.8rem;
}

.matrix-card {
    border-radius: 12px;
    border: 1px solid rgba(98, 176, 255, 0.14);
    padding: 0.95rem 1rem;
    min-height: 100%;
    background: linear-gradient(180deg, rgba(8, 16, 31, 0.92), rgba(10, 18, 36, 0.95));
}

.matrix-card.cyan {
    background: linear-gradient(180deg, rgba(8, 48, 56, 0.56), rgba(8, 20, 35, 0.94));
    border-color: rgba(45, 226, 230, 0.16);
}

.matrix-card.pink {
    background: linear-gradient(180deg, rgba(60, 12, 44, 0.62), rgba(20, 12, 26, 0.96));
    border-color: rgba(255, 78, 205, 0.2);
}

.matrix-card.green {
    background: linear-gradient(180deg, rgba(12, 53, 32, 0.6), rgba(12, 20, 20, 0.96));
    border-color: rgba(62, 227, 143, 0.2);
}

.matrix-card.amber {
    background: linear-gradient(180deg, rgba(61, 39, 10, 0.54), rgba(25, 16, 10, 0.95));
    border-color: rgba(255, 191, 105, 0.18);
}

.matrix-card-kicker {
    color: rgba(232, 241, 255, 0.72);
    font-size: 0.72rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-weight: 700;
}

.matrix-card-title {
    margin-top: 0.28rem;
    font-family: 'Outfit', sans-serif;
    color: #ffffff;
    font-size: 1rem;
    font-weight: 700;
}

.matrix-card-value {
    margin-top: 0.3rem;
    color: #f4fbff;
    font-size: 1.15rem;
    font-weight: 800;
}

.matrix-card-copy {
    margin-top: 0.32rem;
    color: rgba(223, 234, 248, 0.82);
    font-size: 0.8rem;
    line-height: 1.48;
}

.terminal-note {
    padding: 0.8rem 0.95rem;
    border-radius: 12px;
    border: 1px solid rgba(255, 78, 205, 0.14);
    background: linear-gradient(180deg, rgba(29, 12, 33, 0.42), rgba(13, 17, 31, 0.7));
    color: #ebd7ff;
    font-size: 0.84rem;
    line-height: 1.55;
}

.insight-box {
    background: linear-gradient(180deg, rgba(10, 18, 35, 0.96), rgba(12, 22, 42, 0.92));
    border-left: 3px solid var(--cyan);
    border-radius: 0 12px 12px 0;
    padding: 1rem 1rem;
    margin: 0.75rem 0 1rem 0;
}

.insight-box.warning {
    border-left-color: var(--amber);
    background: linear-gradient(180deg, rgba(36, 24, 8, 0.76), rgba(19, 14, 8, 0.9));
}

.insight-box.success {
    border-left-color: var(--green);
    background: linear-gradient(180deg, rgba(8, 32, 20, 0.68), rgba(8, 18, 16, 0.92));
}

.insight-box p, .insight-box li {
    color: var(--text);
    margin: 0.18rem 0;
    font-size: 0.9rem;
}

.section-header {
    font-family: 'Outfit', sans-serif;
    font-size: 1.05rem;
    font-weight: 700;
    color: #f0f6ff;
    border-bottom: 1px solid rgba(98, 176, 255, 0.16);
    padding-bottom: 0.45rem;
    margin: 1.3rem 0 0.9rem 0;
}

.source-pill {
    display: inline-block;
    background: rgba(45, 226, 230, 0.08);
    border: 1px solid rgba(45, 226, 230, 0.18);
    color: #c8fbff;
    border-radius: 999px;
    padding: 0.16rem 0.55rem;
    font-size: 0.7rem;
    font-weight: 700;
    margin-right: 0.35rem;
}

.attr-badge {
    font-size: 1rem;
    font-weight: 700;
    padding: 0.3rem 0.8rem;
    border-radius: 999px;
    display: inline-block;
    margin-top: 0.45rem;
}

.attr-high {
    background: rgba(62, 227, 143, 0.12);
    color: var(--green);
    border: 1px solid rgba(62, 227, 143, 0.28);
}

.attr-medium {
    background: rgba(255, 191, 105, 0.12);
    color: var(--amber);
    border: 1px solid rgba(255, 191, 105, 0.28);
}

.attr-low {
    background: rgba(255, 107, 129, 0.12);
    color: var(--red);
    border: 1px solid rgba(255, 107, 129, 0.28);
}

.stTabs [data-baseweb="tab-list"] {
    background: rgba(7, 14, 27, 0.9);
    border: 1px solid rgba(98, 176, 255, 0.12);
    border-radius: 14px;
    padding: 0.25rem;
    gap: 0.35rem;
}

.stTabs [data-baseweb="tab"] {
    border-radius: 10px;
    color: var(--muted);
    font-weight: 700;
    font-size: 0.88rem;
    padding: 0.55rem 0.9rem;
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(90deg, rgba(39, 86, 176, 0.95), rgba(98, 176, 255, 0.62)) !important;
    color: #f7fbff !important;
    box-shadow: 0 0 0 1px rgba(98, 176, 255, 0.14);
}

.stButton > button {
    border-radius: 10px;
    font-weight: 700;
}

.stButton > button[kind="primary"] {
    background: linear-gradient(90deg, #1f7ae0 0%, #31c4ff 100%);
    border: none;
    color: white;
    box-shadow: 0 10px 24px rgba(41, 137, 255, 0.24);
}

.stButton > button[kind="primary"]:hover {
    background: linear-gradient(90deg, #2690ff 0%, #38dbff 100%);
}

[data-testid="stAppDeployButton"] {
    display: none !important;
}

.stDataFrame,
[data-testid="stTable"] {
    border: 1px solid rgba(98, 176, 255, 0.12) !important;
    border-radius: 12px !important;
}

hr {
    border-color: rgba(98, 176, 255, 0.12) !important;
}

.stCaption, .caption {
    color: var(--muted) !important;
    font-size: 0.8rem !important;
}

.streamlit-expanderHeader {
    background: rgba(9, 19, 37, 0.82) !important;
    border: 1px solid rgba(98, 176, 255, 0.13) !important;
    border-radius: 10px !important;
    color: #dce8fb !important;
}

.stSelectbox > div > div,
.stTextInput > div > div,
.stNumberInput > div > div,
.stTextArea textarea {
    background: rgba(8, 17, 34, 0.92) !important;
    border-color: rgba(98, 176, 255, 0.18) !important;
    color: var(--text) !important;
    border-radius: 10px !important;
}

.stSlider [data-baseweb="slider"] {
    padding-top: 0.55rem;
}

label, .stMarkdown, p, div {
    color: inherit;
}

@media (max-width: 980px) {
    .hero-grid {
        grid-template-columns: 1fr;
    }

    .metric-strip {
        grid-template-columns: 1fr;
    }

    .terminal-summary-row,
    .matrix-grid {
        grid-template-columns: 1fr;
    }

    .macro-topline {
        flex-direction: column;
        align-items: flex-start;
    }
}
</style>
"""
