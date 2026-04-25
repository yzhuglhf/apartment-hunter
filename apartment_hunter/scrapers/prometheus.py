import re

from playwright.sync_api import Page, sync_playwright

from apartment_hunter.scrapers.utils import parse_promo

URL = "https://prometheusapartments.com/ca/sunnyvale-apartments/oak-umber"
COORDS = (37.3688, -122.0363)  # Oak Umber, Sunnyvale

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
window.chrome = {runtime: {}};
const _origQuery = navigator.permissions.query.bind(navigator.permissions);
navigator.permissions.query = (p) =>
    p.name === 'notifications'
        ? Promise.resolve({state: Notification.permission})
        : _origQuery(p);
"""


def scrape() -> list[dict]:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome",
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        ctx = browser.new_context(
            user_agent=_USER_AGENT,
            viewport={"width": 1280, "height": 900},
            locale="en-US",
        )
        page = ctx.new_page()
        page.add_init_script(_STEALTH_JS)
        page.goto(URL, wait_until="load", timeout=30_000)
        page.wait_for_timeout(4000)
        units = _collect_all_plans(page)
        property_promo = _scrape_specials(page)
        for u in units:
            u["promotion"] = u["promotion"] or property_promo
        browser.close()
    return units


def _scrape_specials(page: Page) -> str | None:
    specials_url = URL.rstrip("/") + "/specials/"
    try:
        page.goto(specials_url, wait_until="load", timeout=10_000)
        page.wait_for_timeout(1500)
        text = page.evaluate("() => document.body.innerText")
        return parse_promo(text)
    except Exception:
        return None


def _collect_all_plans(page: Page) -> list[dict]:
    seen, units = set(), []

    item_count = page.evaluate(
        "() => document.querySelectorAll('li.accordionItem').length"
    )

    for i in range(item_count):
        page.evaluate(f"""() => {{
            const items = document.querySelectorAll('li.accordionItem');
            items[{i}]?.querySelector('button.accordionItemButton')?.click();
        }}""")
        page.wait_for_timeout(700)

        data = page.evaluate(f"""() => {{
            const item = document.querySelectorAll('li.accordionItem')[{i}];
            if (!item) return null;
            const heading = item.querySelector('.accordionItemButton')?.innerText?.trim() || '';
            const bodies = [...item.querySelectorAll('.apartmentAccBody')];
            const promoEls = [...item.querySelectorAll(
                '[class*="promo" i],[class*="special" i],[class*="offer" i],[class*="badge" i]'
            )];
            return {{
                heading,
                promo: promoEls.map(e => e.innerText.trim()).filter(t => t).join(' ') || '',
                units: bodies.map(b => b.innerText.trim()),
            }};
        }}""")

        if not data:
            continue

        heading = data["heading"]
        plan_name = heading.splitlines()[0].strip() if heading.splitlines() else "—"
        bed_m = re.search(r"(\d+)\s*Bed", heading)
        bath_m = re.search(r"(\d+(?:\.\d+)?)\s*Bath", heading)
        sqft_m = re.search(r"([\d,]+)\s*sq\.?\s*ft", heading, re.IGNORECASE)

        def to_int(m, group=1):
            return int(m.group(group).replace(",", "").split(".")[0]) if m else None

        plan_promo = parse_promo(data.get("promo", "") + " " + heading)

        for unit_text in data["units"]:
            unit_m = re.search(r"Apartment\s+(\w+)", unit_text)
            floor_m = re.search(r"Floor\s+(\d+)", unit_text)
            price_m = re.search(r"\$([\d,]+)/\d+mo", unit_text)
            avail_m = re.search(r"Available\s+[^\n]+", unit_text)

            unit_id = unit_m.group(1) if unit_m else unit_text[:20]
            if unit_id in seen:
                continue
            seen.add(unit_id)

            unit_promo = parse_promo(unit_text) or plan_promo

            units.append({
                "source": "Prometheus",
                "floorplan": plan_name,
                "unit": unit_id,
                "floor": to_int(floor_m),
                "address": "Oak Umber, Sunnyvale CA",
                "url": URL,
                "availability": avail_m.group(0).strip() if avail_m else "—",
                "bedrooms": to_int(bed_m),
                "bathrooms": to_int(bath_m),
                "sqft": to_int(sqft_m),
                "base_rent": to_int(price_m),
                "total_rent": None,
                "a_c": False,
                "promotion": unit_promo,
                "coords": COORDS,
            })

    return units
