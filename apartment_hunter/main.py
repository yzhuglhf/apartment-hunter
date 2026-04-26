import os
import shutil
from datetime import date

import click
from dotenv import load_dotenv
from rich import box
from rich.console import Console
from rich.table import Table

from apartment_hunter import notifier
from apartment_hunter.scrapers import avalon, diridonwest, lynhaven, maxwell, prometheus
from apartment_hunter.scrapers.utils import calc_effective_rent

load_dotenv()

console = Console()


@click.command()
@click.option("--max-price", default=3100, show_default=True, help="Max base rent ($)")
@click.option("--email", "send_email", is_flag=True, default=False, help="Email the report")
@click.option("--setup-cron", is_flag=True, default=False, help="Print daily cron setup command")
def cli(max_price: int, send_email: bool, setup_cron: bool):
    """Scrape available apartments and optionally email a daily report."""

    if setup_cron:
        binary = shutil.which("apartment-hunter") or "apartment-hunter"
        entry = f'0 8 * * * {binary} --email >> ~/.apartment-hunter.log 2>&1'
        console.print("[bold]Add this line to your crontab ([cyan]crontab -e[/cyan]):[/bold]")
        console.print(f"\n  {entry}\n")
        console.print("Or run this to add it automatically:")
        console.print(f'  [dim](crontab -l 2>/dev/null; echo "{entry}") | crontab -[/dim]')
        return

    # ── Maxwell at Bascom ────────────────────────────────────────────────────
    console.print("[bold]Scraping Maxwell at Bascom...[/bold]")
    maxwell_units = maxwell.scrape()
    maxwell_under = [u for u in maxwell_units if (u["base_rent"] or 0) <= max_price]
    console.print(f"  {len(maxwell_units)} units found (floor 1 excluded), {len(maxwell_under)} under ${max_price:,}.")

    if maxwell_under:
        t = Table(title=f"Maxwell at Bascom — base rent ≤ ${max_price:,}/mo (floor 1 excluded)", box=box.ROUNDED)
        t.add_column("Floor Plan", style="bold")
        t.add_column("Unit", style="cyan")
        t.add_column("Floor")
        t.add_column("Base Rent", style="green")
        t.add_column("Eff. Rent", style="bright_green")
        t.add_column("Total /mo", style="yellow")
        t.add_column("Beds")
        t.add_column("Baths")
        t.add_column("Sq Ft")
        t.add_column("Available")
        t.add_column("Promotion", style="magenta")
        for u in sorted(maxwell_under, key=lambda x: x["base_rent"] or 0):
            eff = calc_effective_rent(u["base_rent"], u.get("promotion"), u.get("lease_months"))
            t.add_row(
                u["floorplan"], u["unit"],
                str(u.get("floor") or "—"),
                f"${u['base_rent']:,}" if u["base_rent"] else "—",
                f"${eff:,}" if eff else "—",
                f"${u['total_rent']:,}" if u["total_rent"] else "—",
                str(u["bedrooms"] or "—"), str(u["bathrooms"] or "—"),
                f"{u['sqft']:,}" if u["sqft"] else "—",
                u["availability"],
                u.get("promotion") or "—",
            )
        console.print(t)
    else:
        console.print(f"[yellow]No Maxwell units under ${max_price:,}.[/yellow]")

    # ── Prometheus Oak Umber ─────────────────────────────────────────────────
    console.print("\n[bold]Scraping Prometheus Oak Umber...[/bold]")
    prom_units = prometheus.scrape()
    prom_under = [u for u in prom_units if (u["base_rent"] or 0) <= max_price]
    console.print(f"  {len(prom_units)} units found (floor 1 excluded), {len(prom_under)} under ${max_price:,}.")

    if prom_under:
        t = Table(title=f"Prometheus Oak Umber — base rent ≤ ${max_price:,}/mo", box=box.ROUNDED)
        t.add_column("Floor Plan", style="bold")
        t.add_column("Unit", style="cyan")
        t.add_column("Floor")
        t.add_column("Base Rent", style="green")
        t.add_column("Eff. Rent", style="bright_green")
        t.add_column("Beds")
        t.add_column("Baths")
        t.add_column("Sq Ft")
        t.add_column("Available")
        t.add_column("Promotion", style="magenta")
        for u in sorted(prom_under, key=lambda x: x["base_rent"] or 0):
            eff = calc_effective_rent(u["base_rent"], u.get("promotion"), u.get("lease_months"))
            t.add_row(
                u["floorplan"], u.get("unit") or "—",
                str(u.get("floor") or "—"),
                f"${u['base_rent']:,}" if u["base_rent"] else "—",
                f"${eff:,}" if eff else "—",
                str(u["bedrooms"] or "—"), str(u["bathrooms"] or "—"),
                f"{u['sqft']:,}" if u["sqft"] else "—",
                u["availability"],
                u.get("promotion") or "—",
            )
        console.print(t)
    else:
        console.print(f"[yellow]No Prometheus plans under ${max_price:,}.[/yellow]")

    # ── Lyn Haven ────────────────────────────────────────────────────────────
    console.print("\n[bold]Scraping Lyn Haven...[/bold]")
    lyn_units = lynhaven.scrape()
    lyn_under = [u for u in lyn_units if (u["base_rent"] or 0) <= max_price]
    console.print(f"  {len(lyn_units)} units found (floor 1 excluded), {len(lyn_under)} under ${max_price:,}.")

    if lyn_under:
        t = Table(title=f"Lyn Haven — base rent ≤ ${max_price:,}/mo (floor 1 excluded)", box=box.ROUNDED)
        t.add_column("Floor Plan", style="bold")
        t.add_column("Unit", style="cyan")
        t.add_column("Floor")
        t.add_column("Base Rent", style="green")
        t.add_column("Eff. Rent", style="bright_green")
        t.add_column("Total /mo", style="yellow")
        t.add_column("Beds")
        t.add_column("Baths")
        t.add_column("Sq Ft")
        t.add_column("Available")
        t.add_column("Promotion", style="magenta")
        for u in sorted(lyn_under, key=lambda x: x["base_rent"] or 0):
            eff = calc_effective_rent(u["base_rent"], u.get("promotion"), u.get("lease_months"))
            t.add_row(
                u["floorplan"], u["unit"],
                str(u["floor"]) if u["floor"] else "—",
                f"${u['base_rent']:,}" if u["base_rent"] else "—",
                f"${eff:,}" if eff else "—",
                f"${u['total_rent']:,}" if u["total_rent"] else "—",
                str(u["bedrooms"] or "—"), str(u["bathrooms"] or "—"),
                f"{u['sqft']:,}" if u["sqft"] else "—",
                u["availability"],
                u.get("promotion") or "—",
            )
        console.print(t)
    else:
        console.print(f"[yellow]No Lyn Haven units under ${max_price:,}.[/yellow]")

    # ── Avalon Willow Glen ───────────────────────────────────────────────────
    console.print("\n[bold]Scraping Avalon Willow Glen...[/bold]")
    avalon_units = avalon.scrape()
    avalon_under = [u for u in avalon_units if (u["base_rent"] or 0) <= max_price]
    console.print(f"  {len(avalon_units)} units found, {len(avalon_under)} under ${max_price:,}.")

    if avalon_under:
        t = Table(title=f"Avalon Willow Glen — base rent ≤ ${max_price:,}/mo", box=box.ROUNDED)
        t.add_column("Floor Plan", style="bold")
        t.add_column("Unit", style="cyan")
        t.add_column("Floor")
        t.add_column("Base Rent", style="green")
        t.add_column("Eff. Rent", style="bright_green")
        t.add_column("Beds")
        t.add_column("Baths")
        t.add_column("Sq Ft")
        t.add_column("Lease")
        t.add_column("Available")
        t.add_column("Promotion", style="magenta")
        for u in sorted(avalon_under, key=lambda x: x["base_rent"] or 0):
            eff = calc_effective_rent(u["base_rent"], u.get("promotion"), u.get("lease_months"))
            t.add_row(
                u["floorplan"], u["unit"],
                str(u["floor"]) if u["floor"] else "—",
                f"${u['base_rent']:,}" if u["base_rent"] else "—",
                f"${eff:,}" if eff else "—",
                str(u["bedrooms"] or "—"), str(u["bathrooms"] or "—"),
                f"{u['sqft']:,}" if u["sqft"] else "—",
                f"{u.get('lease_months') or '—'}mo",
                u["availability"],
                u.get("promotion") or "—",
            )
        console.print(t)
    else:
        console.print(f"[yellow]No Avalon Willow Glen units under ${max_price:,}.[/yellow]")

    # ── Diridon West ─────────────────────────────────────────────────────────
    console.print("\n[bold]Scraping Diridon West...[/bold]")
    dw_units = diridonwest.scrape()
    dw_under = [u for u in dw_units if (u["base_rent"] or 0) <= max_price]
    console.print(f"  {len(dw_units)} units found (floor 1 excluded), {len(dw_under)} under ${max_price:,}.")

    if dw_under:
        t = Table(title=f"Diridon West — base rent ≤ ${max_price:,}/mo (floor 1 excluded)", box=box.ROUNDED)
        t.add_column("Floor Plan", style="bold")
        t.add_column("Unit", style="cyan")
        t.add_column("Floor")
        t.add_column("Base Rent", style="green")
        t.add_column("Eff. Rent", style="bright_green")
        t.add_column("Total /mo", style="yellow")
        t.add_column("Beds")
        t.add_column("Baths")
        t.add_column("Sq Ft")
        t.add_column("Available")
        t.add_column("Promotion", style="magenta")
        for u in sorted(dw_under, key=lambda x: x["base_rent"] or 0):
            eff = calc_effective_rent(u["base_rent"], u.get("promotion"), u.get("lease_months"))
            t.add_row(
                u["floorplan"], u["unit"],
                str(u.get("floor") or "—"),
                f"${u['base_rent']:,}" if u["base_rent"] else "—",
                f"${eff:,}" if eff else "—",
                f"${u['total_rent']:,}" if u["total_rent"] else "—",
                str(u["bedrooms"] or "—"), str(u["bathrooms"] or "—"),
                f"{u['sqft']:,}" if u["sqft"] else "—",
                u["availability"],
                u.get("promotion") or "—",
            )
        console.print(t)
    else:
        console.print(f"[yellow]No Diridon West units under ${max_price:,}.[/yellow]")

    # ── Email report ─────────────────────────────────────────────────────────
    if send_email:
        sections = [
            {
                "title": f"Maxwell at Bascom — ≤ ${max_price:,}/mo (floor 1 excluded)",
                "cols": ["Floor Plan", "Unit", "Floor", "Base Rent", "Eff. Rent", "Total /mo", "Beds", "Baths", "Sq Ft", "Available", "Promotion"],
                "rows": [
                    [u["floorplan"], u["unit"], str(u.get("floor") or "—"),
                     f"${u['base_rent']:,}" if u["base_rent"] else "—",
                     f"${calc_effective_rent(u['base_rent'], u.get('promotion'), u.get('lease_months')):,}" if calc_effective_rent(u["base_rent"], u.get("promotion"), u.get("lease_months")) else "—",
                     f"${u['total_rent']:,}" if u["total_rent"] else "—",
                     str(u["bedrooms"] or "—"), str(u["bathrooms"] or "—"),
                     f"{u['sqft']:,}" if u["sqft"] else "—",
                     u["availability"], u.get("promotion") or "—"]
                    for u in sorted(maxwell_under, key=lambda x: x["base_rent"] or 0)
                ],
            },
            {
                "title": f"Avalon Willow Glen — ≤ ${max_price:,}/mo",
                "cols": ["Floor Plan", "Unit", "Floor", "Base Rent", "Eff. Rent", "Beds", "Baths", "Sq Ft", "Lease", "Available", "Promotion"],
                "rows": [
                    [u["floorplan"], u["unit"], str(u["floor"]) if u["floor"] else "—",
                     f"${u['base_rent']:,}" if u["base_rent"] else "—",
                     f"${calc_effective_rent(u['base_rent'], u.get('promotion'), u.get('lease_months')):,}" if calc_effective_rent(u["base_rent"], u.get("promotion"), u.get("lease_months")) else "—",
                     str(u["bedrooms"] or "—"), str(u["bathrooms"] or "—"),
                     f"{u['sqft']:,}" if u["sqft"] else "—",
                     f"{u.get('lease_months') or '—'}mo",
                     u["availability"], u.get("promotion") or "—"]
                    for u in sorted(avalon_under, key=lambda x: x["base_rent"] or 0)
                ],
            },
            {
                "title": f"Prometheus Oak Umber — ≤ ${max_price:,}/mo",
                "cols": ["Floor Plan", "Unit", "Floor", "Base Rent", "Eff. Rent", "Beds", "Baths", "Sq Ft", "Available", "Promotion"],
                "rows": [
                    [u["floorplan"], u.get("unit") or "—", str(u.get("floor") or "—"),
                     f"${u['base_rent']:,}" if u["base_rent"] else "—",
                     f"${calc_effective_rent(u['base_rent'], u.get('promotion'), u.get('lease_months')):,}" if calc_effective_rent(u["base_rent"], u.get("promotion"), u.get("lease_months")) else "—",
                     str(u["bedrooms"] or "—"), str(u["bathrooms"] or "—"),
                     f"{u['sqft']:,}" if u["sqft"] else "—",
                     u["availability"], u.get("promotion") or "—"]
                    for u in sorted(prom_under, key=lambda x: x["base_rent"] or 0)
                ],
            },
            {
                "title": f"Lyn Haven — ≤ ${max_price:,}/mo (floor 1 excluded)",
                "cols": ["Floor Plan", "Unit", "Floor", "Base Rent", "Eff. Rent", "Total /mo", "Beds", "Baths", "Sq Ft", "Available", "Promotion"],
                "rows": [
                    [u["floorplan"], u["unit"], str(u["floor"]) if u["floor"] else "—",
                     f"${u['base_rent']:,}" if u["base_rent"] else "—",
                     f"${calc_effective_rent(u['base_rent'], u.get('promotion'), u.get('lease_months')):,}" if calc_effective_rent(u["base_rent"], u.get("promotion"), u.get("lease_months")) else "—",
                     f"${u['total_rent']:,}" if u["total_rent"] else "—",
                     str(u["bedrooms"] or "—"), str(u["bathrooms"] or "—"),
                     f"{u['sqft']:,}" if u["sqft"] else "—",
                     u["availability"], u.get("promotion") or "—"]
                    for u in sorted(lyn_under, key=lambda x: x["base_rent"] or 0)
                ],
            },
            {
                "title": f"Diridon West — ≤ ${max_price:,}/mo (floor 1 excluded)",
                "cols": ["Floor Plan", "Unit", "Floor", "Base Rent", "Eff. Rent", "Total /mo", "Beds", "Baths", "Sq Ft", "Available", "Promotion"],
                "rows": [
                    [u["floorplan"], u["unit"], str(u.get("floor") or "—"),
                     f"${u['base_rent']:,}" if u["base_rent"] else "—",
                     f"${calc_effective_rent(u['base_rent'], u.get('promotion'), u.get('lease_months')):,}" if calc_effective_rent(u["base_rent"], u.get("promotion"), u.get("lease_months")) else "—",
                     f"${u['total_rent']:,}" if u["total_rent"] else "—",
                     str(u["bedrooms"] or "—"), str(u["bathrooms"] or "—"),
                     f"{u['sqft']:,}" if u["sqft"] else "—",
                     u["availability"], u.get("promotion") or "—"]
                    for u in sorted(dw_under, key=lambda x: x["base_rent"] or 0)
                ],
            },
        ]

        to_addr = os.environ.get("ALERT_EMAIL", "")
        html = notifier.build_html(sections, max_price)
        subject = f"Apartment Report — {date.today().strftime('%b %d, %Y')}"
        try:
            notifier.send(html, to_addr, subject)
            console.print(f"\n[green]Report emailed to {to_addr}.[/green]")
        except Exception as e:
            console.print(f"\n[red]Email failed: {e}[/red]")
