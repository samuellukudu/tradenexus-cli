#!/usr/bin/env python3
"""
Trade Nexus CLI — main.py
Entry point for all CLI commands.

Usage:
  python main.py --help
  python main.py analyze-markets
  python main.py market-report
  python main.py search-leads
  python main.py verify-lead
  python main.py prospect
  python main.py extract-context
  python main.py sessions list
  python main.py sessions export <id> --output leads.csv
"""

from __future__ import annotations
import base64
import json
import sys
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.live import Live
from rich.text import Text
from rich.panel import Panel
from rich.rule import Rule

from tradenexus.config import DEFAULT_MODEL, GROUNDING_MODEL, THINKING_BUDGET
from tradenexus.models import (
    ChatMessage, ProductDetails, ProductAsset, StrategicContext,
    Lead, ProductRole, ProductApplication, CountryApplicationMap
)
from tradenexus.core.context import extract_search_strategy_from_assets
from tradenexus.core.markets import analyze_markets, generate_market_report
from tradenexus.core.leads import search_for_leads, verify_lead
from tradenexus.core.prospecting import generate_prospecting_message
from tradenexus.core.application import (
    classify_product_role,
    generate_application_map_generator,
    search_application_lane_generator,
    qualify_leads,
    allocate_lead_budget,
)
from tradenexus import session as sess
from tradenexus import output as out

app = typer.Typer(
    name="trade-nexus",
    help="[bold cyan]Trade Nexus CLI[/] — AI-powered B2B lead generation & market intelligence.",
    rich_markup_mode="rich",
    no_args_is_help=True,
)
sessions_app = typer.Typer(help="Manage saved sessions.")
app.add_typer(sessions_app, name="sessions")

console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _spin(label: str):
    """Context manager that shows a spinner while work runs."""
    return Live(Text(f"⏳ {label}", style="cyan"), refresh_per_second=8, transient=True)


def _prompt_product(session_id: Optional[str] = None) -> ProductDetails:
    """Interactive product configuration. Falls back to session if provided."""
    if session_id:
        try:
            product = sess.get_product_from_session(session_id)
            console.print(f"[dim]Using product from session [bold]{session_id}[/]: {product.name}[/]")
            return product
        except FileNotFoundError:
            console.print(f"[yellow]Session '{session_id}' not found. Entering product details manually.[/]")

    console.print(Panel("[bold cyan]Product Configuration[/]", border_style="cyan"))
    name = Prompt.ask("[cyan]Product name[/]")
    description = Prompt.ask("[cyan]Product description[/]", default="")
    supplier_country = Prompt.ask("[cyan]Supplier country[/]", default="China")
    target_region = Prompt.ask("[cyan]Target region / market[/]", default="Southeast Asia")
    target_lead_count = int(Prompt.ask("[cyan]Number of leads to find[/]", default="20"))

    return ProductDetails(
        name=name,
        description=description or None,
        supplier_country=supplier_country,
        target_region=target_region,
        target_lead_count=target_lead_count,
    )


def _load_file_as_asset(file_path: str) -> ProductAsset:
    path = Path(file_path)
    if not path.exists():
        console.print(f"[red]File not found: {file_path}[/]")
        raise typer.Exit(1)
    ext = path.suffix.lower()
    mime_map = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg", ".webp": "image/webp"}
    mime = mime_map.get(ext, "application/octet-stream")
    data = base64.b64encode(path.read_bytes()).decode("utf-8")
    return ProductAsset(data=data, mime_type=mime, file_name=path.name)


# ---------------------------------------------------------------------------
# analyze-markets
# ---------------------------------------------------------------------------

@app.command("analyze-markets")
def cmd_analyze_markets(
    session: Optional[str] = typer.Option(None, "--session", "-s", help="Session ID to load product from."),
    continent: Optional[str] = typer.Option(None, "--continent", "-c", help="Filter by continent (e.g. Asia, Europe)."),
    countries: Optional[str] = typer.Option(None, "--countries", help="Comma-separated list of target countries."),
    save: bool = typer.Option(True, help="Save results to session."),
):
    """Find the top 9 export markets for your product using AI + trade data."""
    product = _prompt_product(session)
    country_list = [c.strip() for c in countries.split(",")] if countries else []

    console.print(Rule("[cyan]Analyzing Markets[/]", style="cyan"))
    with _spin("AI is analyzing global trade data..."):
        suggestions = analyze_markets(
            product_name=product.name,
            product_description=product.description or "",
            continent=continent,
            countries=country_list or None,
            pre_computed_context=product.strategic_context,
            supplier_country=product.supplier_country or "China",
        )

    out.print_region_suggestions(suggestions)

    if save:
        if not session:
            session = sess.create_session(product)
            console.print(f"[dim]Created session [bold]{session}[/][/]")
        sess.save_suggestions(session, suggestions)
        console.print(f"[green]✓ Results saved to session [bold]{session}[/][/]")


# ---------------------------------------------------------------------------
# market-report
# ---------------------------------------------------------------------------

@app.command("market-report")
def cmd_market_report(
    region: Optional[str] = typer.Option(None, "--region", "-r", help="Target region/country for the report."),
    session: Optional[str] = typer.Option(None, "--session", "-s", help="Session ID to load product from."),
):
    """Generate a full market intelligence report for a specific region."""
    product = _prompt_product(session)
    if not region:
        region = Prompt.ask("[cyan]Target region[/]", default=product.target_region or "Germany")

    console.print(Rule(f"[cyan]Market Report — {region}[/]", style="cyan"))
    with _spin(f"AI is researching {region} with Google Search grounding..."):
        try:
            report = generate_market_report(product, region)
        except Exception as e:
            console.print(f"[red]Failed to generate report: {e}[/]")
            raise typer.Exit(1)

    out.print_market_report(report)


# ---------------------------------------------------------------------------
# search-leads
# ---------------------------------------------------------------------------

@app.command("search-leads")
def cmd_search_leads(
    session: Optional[str] = typer.Option(None, "--session", "-s", help="Session ID to load/save."),
    export_csv: Optional[str] = typer.Option(None, "--export-csv", help="Auto-export leads to this CSV path."),
    export_json: Optional[str] = typer.Option(None, "--export-json", help="Auto-export leads to this JSON path."),
):
    """
    Run the multi-vector 4-squad lead discovery engine.
    Finds verified B2B leads with Google Maps confirmation.
    """
    product = _prompt_product(session)

    console.print(Rule("[cyan]Lead Discovery — Multi-Vector Search[/]", style="cyan"))
    console.print(
        f"[dim]Launching 4 territory squads for [bold]{product.name}[/] "
        f"in [bold]{product.target_region}[/] | Target: {product.target_lead_count} leads[/]"
    )

    with _spin("AI agents are scouting territory squads in parallel..."):
        try:
            leads = search_for_leads(product)
        except Exception as e:
            console.print(f"[red]Search failed: {e}[/]")
            raise typer.Exit(1)

    if not leads:
        console.print("[yellow]No verified leads found. Try expanding the target region.[/]")
        return

    out.print_leads_table(leads)

    if not session:
        session = sess.create_session(product)
        console.print(f"[dim]Created session [bold]{session}[/][/]")
    sess.save_leads(session, leads)
    console.print(f"[green]✓ {len(leads)} leads saved to session [bold]{session}[/][/]")

    if export_csv:
        sess.export_leads_csv(session, export_csv)
        console.print(f"[green]✓ Exported to CSV: {export_csv}[/]")

    if export_json:
        Path(export_json).write_text(json.dumps([l.to_dict() for l in leads], indent=2))
        console.print(f"[green]✓ Exported to JSON: {export_json}[/]")

    console.print(Rule("[cyan]Top Leads — Detailed View[/]", style="cyan"))
    for i, lead in enumerate(leads[:3], 1):
        out.print_lead_card(lead, index=i)


# ---------------------------------------------------------------------------
# verify-lead
# ---------------------------------------------------------------------------

@app.command("verify-lead")
def cmd_verify_lead(
    session: Optional[str] = typer.Option(None, "--session", "-s", help="Session ID to load product from."),
):
    """Verify the legitimacy of a specific company via Google Search + Maps."""
    product = _prompt_product(session)

    console.print(Panel("[bold cyan]Lead Verification[/]", border_style="cyan"))
    company_name = Prompt.ask("[cyan]Company name to verify[/]")
    region = Prompt.ask("[cyan]Company region[/]", default=product.target_region or "")
    website = Prompt.ask("[cyan]Website (optional)[/]", default="")
    address = Prompt.ask("[cyan]Address (optional)[/]", default="")

    from tradenexus.models import Lead, LeadStatus
    import uuid
    dummy_lead = Lead(
        id=str(uuid.uuid4()),
        company_name=company_name,
        region=region,
        status=LeadStatus.DISCOVERED,
        confidence_score=0,
        website=website or None,
        address=address or None,
    )

    with _spin(f"Verifying {company_name} via Google Search..."):
        try:
            result = verify_lead(dummy_lead, product)
        except Exception as e:
            console.print(f"[red]Verification failed: {e}[/]")
            raise typer.Exit(1)

    out.print_verification_result(company_name, result)

    if result.get("_sources"):
        console.print("[dim]Search sources:[/]")
        for url in result["_sources"][:5]:
            console.print(f"  [dim]• {url}[/]")


# ---------------------------------------------------------------------------
# prospect (interactive REPL chat)
# ---------------------------------------------------------------------------

@app.command("prospect")
def cmd_prospect(
    session: Optional[str] = typer.Option(None, "--session", "-s", help="Session ID to load product from."),
):
    """
    Interactive SDR assistant — chat about a specific lead.
    The AI drafts outreach messages, researches hooks, and advises on strategy.
    Type 'exit' or 'quit' to end the session.
    """
    product = _prompt_product(session)

    console.print(Panel("[bold cyan]Prospecting Assistant[/]", border_style="cyan"))
    company_name = Prompt.ask("[cyan]Company name[/]")
    region = Prompt.ask("[cyan]Company region[/]", default=product.target_region or "")
    website = Prompt.ask("[cyan]Website (optional)[/]", default="")

    from tradenexus.models import Lead, LeadStatus
    import uuid
    lead = Lead(
        id=str(uuid.uuid4()),
        company_name=company_name,
        region=region,
        status=LeadStatus.DISCOVERED,
        confidence_score=80,
        website=website or None,
    )

    history: list[ChatMessage] = []
    console.print(
        f"\n[green]✓ SDR Assistant ready for [bold]{company_name}[/].[/] "
        f"Type [bold]exit[/] to quit.\n"
    )

    while True:
        user_input = Prompt.ask("[bold white]You[/]")
        if user_input.strip().lower() in ("exit", "quit", "q"):
            console.print("[dim]Ending prospect session.[/]")
            break

        history.append(ChatMessage(role="user", content=user_input, timestamp=time.time()))

        with _spin("AI is crafting a response..."):
            try:
                reply = generate_prospecting_message(history, lead, product.strategic_context)
            except Exception as e:
                console.print(f"[red]Error: {e}[/]")
                continue

        history.append(ChatMessage(role="model", content=reply, timestamp=time.time()))
        console.print(Panel(reply, title="[bold cyan]AI Assistant[/]", border_style="cyan", padding=(1, 2)))


# ---------------------------------------------------------------------------
# extract-context
# ---------------------------------------------------------------------------

@app.command("extract-context")
def cmd_extract_context(
    files: Optional[list[str]] = typer.Argument(None, help="Local file paths to product catalogues (PDF/image)."),
    session: Optional[str] = typer.Option(None, "--session", "-s", help="Session ID to save context to."),
):
    """
    Analyse product catalogues / spec sheets and extract a Strategic Memory Object.
    Accepts local PDF or image files as arguments.

    Example: python main.py extract-context catalogue.pdf spec_sheet.png
    """
    if not files:
        console.print("[yellow]No files provided. Pass file paths as arguments.[/]")
        console.print("  Example: [bold]python main.py extract-context catalogue.pdf[/]")
        raise typer.Exit(1)

    assets: list[ProductAsset] = []
    for f in files:
        asset = _load_file_as_asset(f)
        assets.append(asset)
        console.print(f"[dim]Loaded: {asset.file_name} ({asset.mime_type})[/]")

    product_name = Prompt.ask("[cyan]Product name (for context)[/]")
    product = ProductDetails(name=product_name, assets=assets)

    console.print(Rule("[cyan]Extracting Strategic Context[/]", style="cyan"))
    with _spin("AI is analysing your product documents..."):
        try:
            ctx = extract_search_strategy_from_assets(product)
        except Exception as e:
            console.print(f"[red]Extraction failed: {e}[/]")
            raise typer.Exit(1)

    out.print_strategic_context(ctx)

    if session:
        sess.save_strategic_context(session, ctx)
        console.print(f"[green]✓ Strategic context saved to session [bold]{session}[/][/]")
    else:
        save = Confirm.ask("Save to a new session?", default=True)
        if save:
            product.strategic_context = ctx
            new_session = sess.create_session(product)
            sess.save_strategic_context(new_session, ctx)
            console.print(f"[green]✓ Saved to session [bold]{new_session}[/][/]")


# ---------------------------------------------------------------------------
# sessions subcommands
# ---------------------------------------------------------------------------

@sessions_app.command("list")
def cmd_sessions_list():
    """List all saved sessions."""
    from rich.table import Table
    from rich import box
    sessions = sess.list_sessions()
    if not sessions:
        console.print("[yellow]No sessions found.[/]")
        return

    table = Table(title="[bold cyan]Saved Sessions[/]", box=box.ROUNDED, border_style="cyan")
    table.add_column("ID", style="bold")
    table.add_column("Name")
    table.add_column("Product")
    table.add_column("Leads", justify="right")
    table.add_column("Created")

    for s in sessions:
        created = time.strftime("%Y-%m-%d %H:%M", time.localtime(s["created_at"]))
        table.add_row(s["id"], s["name"], s["product"], str(s["leads_count"]), created)
    console.print(table)


@sessions_app.command("export")
def cmd_sessions_export(
    session_id: str = typer.Argument(..., help="Session ID to export."),
    output: str = typer.Option("leads.csv", "--output", "-o", help="Output file path (.csv or .json)."),
):
    """Export leads from a session to CSV or JSON."""
    if output.endswith(".json"):
        data = sess.load_session(session_id)
        Path(output).write_text(json.dumps(data.get("leads", []), indent=2))
        console.print(f"[green]✓ Exported JSON to {output}[/]")
    else:
        sess.export_leads_csv(session_id, output)
        console.print(f"[green]✓ Exported CSV to {output}[/]")


@sessions_app.command("show")
def cmd_sessions_show(session_id: str = typer.Argument(..., help="Session ID to inspect.")):
    """Show details and leads from a session."""
    data = sess.load_session(session_id)
    console.print(Panel(
        f"[bold]ID:[/] {data['id']}\n"
        f"[bold]Name:[/] {data.get('name', '?')}\n"
        f"[bold]Product:[/] {data.get('product', {}).get('name', '?')}\n"
        f"[bold]Leads:[/] {len(data.get('leads', []))}\n"
        f"[bold]Suggestions:[/] {len(data.get('suggestions', []))}",
        title="[bold cyan]Session Details[/]",
        border_style="cyan",
    ))
    leads = data.get("leads", [])
    if leads:
        from rich.table import Table
        from rich import box
        table = Table(box=box.MINIMAL, show_header=True)
        table.add_column("Company")
        table.add_column("Region")
        table.add_column("Score")
        table.add_column("Email")
        for l in leads:
            table.add_row(l.get("companyName", "?"), l.get("region", "?"),
                          str(l.get("confidenceScore", 0)) + "%", l.get("contactEmail") or "—")
        console.print(table)


# ---------------------------------------------------------------------------
# discover (async / streaming)
# ---------------------------------------------------------------------------

def _lead_from_dict(d: dict) -> Lead:
    from tradenexus.models import LeadStatus
    return Lead(
        id=d.get("id", ""),
        company_name=d.get("companyName") or d.get("company_name") or "Unknown",
        region=d.get("region", ""),
        status=LeadStatus(d.get("status", "DISCOVERED")),
        confidence_score=d.get("confidenceScore") or d.get("confidence_score") or 0,
        website=d.get("website"),
        summary=d.get("summary"),
        contact_email=d.get("contactEmail") or d.get("contact_email"),
        phone_number=d.get("phoneNumber") or d.get("phone_number"),
        address=d.get("address"),
        source_url=d.get("sourceUrl") or d.get("source_url"),
        google_maps_url=d.get("googleMapsUrl") or d.get("google_maps_url"),
        search_vector=d.get("searchVector") or d.get("search_vector"),
        verification_status=d.get("verificationStatus") or d.get("verification_status"),
        verification_notes=d.get("verificationNotes") or d.get("verification_notes"),
        sources=d.get("sources") or [],
        application_id=d.get("applicationId") or d.get("application_id"),
        application=d.get("application"),
        buyer_type=d.get("buyerType") or d.get("buyer_type"),
        search_lane=d.get("searchLane") or d.get("search_lane"),
    )


async def async_discover(
    session_id: Optional[str],
    country: Optional[str],
    limit: Optional[int],
    save: bool,
    export_csv: Optional[str],
    export_json: Optional[str],
):
    product = _prompt_product(session_id)

    if not country:
        country = Prompt.ask("[cyan]Target country for discovery[/]", default=product.target_region or "Germany")

    lead_target = limit or product.target_lead_count or 20

    console.print(Rule(f"[cyan]Application-Led Discovery — {country}[/]", style="cyan"))
    console.print(
        f"[dim]Initializing discovery flow for [bold]{product.name}[/] "
        f"in [bold]{country}[/] | Target: {lead_target} leads[/]"
    )

    # 1. Classify product role
    with _spin(f"Classifying product role for '{product.name}'..."):
        try:
            product_role = await classify_product_role(product, product.strategic_context)
            product.product_role = product_role
        except Exception as e:
            console.print(f"[red]Product role classification failed: {e}[/]")
            raise typer.Exit(1)

    console.print(Panel(
        f"[bold cyan]Role:[/] {product_role.role}\n"
        f"[bold cyan]Reseller Types:[/] {', '.join(product_role.reseller_types) or '—'}\n"
        f"[bold cyan]Operator Types:[/] {', '.join(product_role.operator_types) or '—'}\n"
        f"[bold cyan]Maintainer Types:[/] {', '.join(product_role.maintainer_types) or '—'}",
        title=f"[bold green]✓ Product Role Classified[/]",
        border_style="green",
        expand=False,
    ))

    # 2. Generate application map
    console.print(Rule(f"[cyan]Discovering Market Lanes in {country}[/]", style="cyan"))
    
    app_map = None
    log_messages = []
    
    from rich.console import Group
    from rich.spinner import Spinner
    
    status_spinner = Spinner("dots", style="cyan")
    status_text = Text("Connecting to AI analyst...", style="bold white")
    
    def render_map_panel():
        lines = [Text.assemble(status_spinner.render(time.time()), " ", status_text), Rule(style="dim")]
        for m in log_messages[-6:]:
            lines.append(Text(f"• {m}", style="dim"))
        return Panel(Group(*lines), title="[bold cyan]Application Mapping Stream[/]", border_style="cyan")

    with Live(render_map_panel(), refresh_per_second=10) as live:
        try:
            generator = generate_application_map_generator(
                product=product,
                country=country,
                product_role=product_role,
                context=product.strategic_context,
                supplier_country=product.supplier_country
            )
            async for chunk in generator:
                data = json.loads(chunk)
                status = data.get("status")
                msg = data.get("message")
                
                log_messages.append(msg)
                
                if status == "starting":
                    status_text = Text(msg, style="bold white")
                elif status == "researching":
                    status_text = Text(msg, style="bold yellow")
                    status_spinner.style = "yellow"
                elif status == "extracting":
                    status_text = Text(msg, style="bold magenta")
                    status_spinner.style = "magenta"
                elif status == "complete":
                    status_text = Text(msg, style="bold green")
                    status_spinner.style = "green"
                    app_map = CountryApplicationMap.from_dict(data["result"])
                
                live.update(render_map_panel())
        except Exception as e:
            console.print(f"[red]Application map generation failed: {e}[/]")
            raise typer.Exit(1)

    if not app_map or not app_map.applications:
        console.print("[yellow]No applications identified for this country/product combination.[/]")
        return

    # Print applications table
    from rich.table import Table
    from rich import box
    
    table = Table(
        title=f"[bold cyan]Discovered Application Lanes for {country}[/]",
        box=box.ROUNDED,
        border_style="cyan",
        header_style="bold white",
        show_lines=True
    )
    table.add_column("Lane #", justify="center", style="bold", width=8)
    table.add_column("Application Name", style="bold green")
    table.add_column("Buyer Types", style="dim")
    table.add_column("Priority Score", justify="right", style="bold magenta")
    
    for idx, app_item in enumerate(app_map.applications, 1):
        table.add_row(
            str(idx),
            app_item.name,
            ", ".join(app_item.buyer_types),
            f"{app_item.priority_score:.2f}"
        )
    console.print(table)

    # 3. Budget allocation
    budget = allocate_lead_budget(app_map.applications, lead_target)
    
    # 4. Search lanes
    console.print(Rule("[cyan]Searching Lead Candidates per Lane[/]", style="cyan"))
    
    all_discovered_leads = []
    
    for idx, application in enumerate(app_map.applications, 1):
        lane_budget = budget.get(application.id, 0)
        if lane_budget == 0:
            continue
            
        console.print(f"\n[bold yellow]Lane {idx}/{len(app_map.applications)}:[/] Searching [bold green]\"{application.name}\"[/] (Target: {lane_budget} leads)")
        
        lane_leads = []
        log_messages = []
        status_spinner = Spinner("dots", style="cyan")
        status_text = Text("Deploying lead discovery agent...", style="bold white")
        
        def render_lane_panel():
            lines = [Text.assemble(status_spinner.render(time.time()), " ", status_text), Rule(style="dim")]
            for m in log_messages[-6:]:
                lines.append(Text(f"• {m}", style="dim"))
            return Panel(Group(*lines), title=f"[bold cyan]Discovery Stream: {application.name}[/]", border_style="cyan")
            
        with Live(render_lane_panel(), refresh_per_second=10) as live:
            try:
                generator = search_application_lane_generator(product, application, lane_budget)
                async for chunk in generator:
                    data = json.loads(chunk)
                    status = data.get("status")
                    msg = data.get("message")
                    
                    log_messages.append(msg)
                    
                    if status == "starting":
                        status_text = Text(msg, style="bold white")
                    elif status == "searching":
                        status_text = Text(msg, style="bold yellow")
                        status_spinner.style = "yellow"
                    elif status == "filtering":
                        status_text = Text(msg, style="bold magenta")
                        status_spinner.style = "magenta"
                    elif status == "complete":
                        status_text = Text(msg, style="bold green")
                        status_spinner.style = "green"
                        lane_leads = [_lead_from_dict(l) for l in data["result"]]
                    
                    live.update(render_lane_panel())
            except Exception as e:
                console.print(f"[red]Lane search failed: {e}. Continuing...[/]")
                continue
                
        if not lane_leads:
            console.print("[dim]No leads discovered in this lane.[/]")
            continue
            
        # 5. Qualification
        with _spin(f"Auditing and screening {len(lane_leads)} leads for fit..."):
            try:
                report = await qualify_leads(lane_leads, application, product.name)
                qualified_lane_leads = []
                for lead in lane_leads:
                    q = next((ql for ql in report.qualifications if ql.lead_id == lead.id), None)
                    if q and q.result in ("qualified", "uncertain"):
                        lead.verification_notes = f"Qualified: {'; '.join(q.matched_signals)}"
                        qualified_lane_leads.append(lead)
                
                console.print(f"[green]✓ Qualified {len(qualified_lane_leads)}/{len(lane_leads)} leads[/] [dim]({report.rejected} rejected by auditor)[/]")
                all_discovered_leads.extend(qualified_lane_leads)
            except Exception as e:
                console.print(f"[red]Qualification failed: {e}. Keeping all candidates.[/]")
                all_discovered_leads.extend(lane_leads)

    if not all_discovered_leads:
        console.print("[yellow]No qualified leads found.[/]")
        return
        
    # Deduplicate against session leads
    existing_leads = []
    if session_id:
        try:
            session_data = sess.load_session(session_id)
            existing_leads = [_lead_from_dict(l) for l in session_data.get("leads", [])]
        except Exception:
            pass
            
    existing_websites = {l.website.lower().replace("https://", "").replace("http://", "").rstrip("/") for l in existing_leads if l.website}
    existing_names = {l.company_name.lower().strip() for l in existing_leads}
    
    unique_new_leads = []
    for lead in all_discovered_leads:
        clean_website = lead.website.lower().replace("https://", "").replace("http://", "").rstrip("/") if lead.website else None
        clean_name = lead.company_name.lower().strip()
        if (clean_website and clean_website in existing_websites) or clean_name in existing_names:
            continue
        unique_new_leads.append(lead)
        if clean_website:
            existing_websites.add(clean_website)
        existing_names.add(clean_name)
        
    if not unique_new_leads:
        console.print("[yellow]All discovered leads are already in the session.[/]")
        return
        
    console.print(Rule("[cyan]Discover Complete — Results[/]", style="cyan"))
    out.print_leads_table(unique_new_leads)
    
    if save:
        if not session_id:
            session_id = sess.create_session(product)
            console.print(f"[dim]Created new session [bold]{session_id}[/][/]")
            
        combined_leads = existing_leads + unique_new_leads
        sess.save_leads(session_id, combined_leads)
        console.print(f"[green]✓ Saved {len(unique_new_leads)} new leads to session [bold]{session_id}[/] (Total: {len(combined_leads)} leads)[/]")
        
    if export_csv:
        if not session_id:
            session_id = sess.create_session(product)
            sess.save_leads(session_id, unique_new_leads)
        sess.export_leads_csv(session_id, export_csv)
        console.print(f"[green]✓ Exported to CSV: {export_csv}[/]")
        
    if export_json:
        Path(export_json).write_text(json.dumps([l.to_dict() for l in unique_new_leads], indent=2))
        console.print(f"[green]✓ Exported to JSON: {export_json}[/]")

    console.print(Rule("[cyan]Top Leads — Detailed View[/]", style="cyan"))
    for i, lead in enumerate(unique_new_leads[:3], 1):
        out.print_lead_card(lead, index=i)


@app.command("discover")
def cmd_discover(
    session: Optional[str] = typer.Option(None, "--session", "-s", help="Session ID to load product from."),
    country: Optional[str] = typer.Option(None, "--country", "-c", help="Target country for lead discovery."),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Number of leads to find."),
    save: bool = typer.Option(True, help="Save results to session."),
    export_csv: Optional[str] = typer.Option(None, "--export-csv", help="Auto-export leads to this CSV path."),
    export_json: Optional[str] = typer.Option(None, "--export-json", help="Auto-export leads to this JSON path."),
):
    """
    Run the async Application-Led Lead Discovery flow.
    Decomposes product's market application lanes and streams candidate leads.
    """
    import asyncio
    asyncio.run(async_discover(session, country, limit, save, export_csv, export_json))


# ---------------------------------------------------------------------------
# info command
# ---------------------------------------------------------------------------

@app.command("info")
def cmd_info():
    """Show current configuration (models, API key status)."""
    from tradenexus.config import get_api_key
    try:
        key = get_api_key()
        key_display = f"[green]✓ Set ({key[:8]}...)[/]"
    except EnvironmentError:
        key_display = "[red]✗ NOT SET[/]"

    console.print(Panel(
        f"[bold]API Key:[/] {key_display}\n"
        f"[bold]Default Model:[/] {DEFAULT_MODEL}\n"
        f"[bold]Grounding Model:[/] {GROUNDING_MODEL}\n"
        f"[bold]Thinking Budget:[/] {'Disabled' if THINKING_BUDGET <= 0 else str(THINKING_BUDGET)}\n"
        f"[bold]Sessions dir:[/] ~/.tradenexus/sessions/",
        title="[bold cyan]Trade Nexus CLI — Configuration[/]",
        border_style="cyan",
    ))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app()
