import re

from playwright.sync_api import Page, sync_playwright

from apartment_hunter.scrapers.utils import parse_promo

URL = "https://maxwellatbascom.com/floorplans/"
COORDS = (37.3098, -121.9498)  # S Bascom Ave, San Jose


def scrape() -> list[dict]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, wait_until="load", timeout=30_000)
        page.wait_for_timeout(4000)
        units = _collect_all_floors(page)
        property_promo = _scrape_specials(page)
        for u in units:
            u["promotion"] = u["promotion"] or property_promo
        browser.close()
    return units


def _scrape_specials(page: Page) -> str | None:
    try:
        page.goto("https://maxwellatbascom.com/", wait_until="load", timeout=15_000)
        page.wait_for_timeout(2000)
        promo = page.evaluate("""() => {
            const el = document.querySelector('.popdown__content-copy');
            if (!el) return '';
            const title = el.querySelector('.popdown__title-text')?.innerText?.trim() || '';
            const desc  = el.querySelector('.popdown__description p')?.innerText?.trim() || '';
            return [title, desc].filter(Boolean).join(': ');
        }""")
        if promo:
            return parse_promo(promo) or promo
    except Exception:
        pass
    return None


def _collect_all_floors(page: Page) -> list[dict]:
    seen, units = set(), []

    floor_count = page.evaluate("""() =>
        document.querySelectorAll('.jd-fp-map-embed__floors-item').length
    """)

    for i in range(floor_count):
        text = page.evaluate(f"""() => {{
            const btns = document.querySelectorAll('.jd-fp-map-embed__floors-item');
            return btns[{i}]?.innerText || '';
        }}""")
        if "--" in text:
            continue
        page.evaluate(f"""() => {{
            document.querySelectorAll('.jd-fp-map-embed__floors-item')[{i}]?.click();
        }}""")
        page.wait_for_timeout(800)
        for u in _read_units(page):
            if u["unit"] not in seen:
                seen.add(u["unit"])
                units.append(u)

    if not units:
        units = _read_units(page)

    return units


def _read_units(page: Page) -> list[dict]:
    raw = page.evaluate("""() =>
        [...document.querySelectorAll('[data-unit]')].map(el => ({
            unit: el.getAttribute('title') || '',
            url: 'https://maxwellatbascom.com' + el.getAttribute('href'),
            text: el.innerText.trim(),
            promo: [...el.querySelectorAll(
                '[class*="promo" i],[class*="special" i],[class*="offer" i],[class*="ribbon" i],[class*="badge" i]'
            )].map(p => p.innerText.trim()).filter(t => t).join(' ') || '',
        }))
    """)
    return [_parse(r) for r in raw if r["text"]]


def _parse(raw: dict) -> dict:
    lines = [l.strip() for l in raw["text"].splitlines() if l.strip()]
    floorplan = lines[0] if lines else "—"

    bed_m = re.search(r"(\d+)\s*bed", raw["text"], re.IGNORECASE)
    bath_m = re.search(r"(\d+(?:\.\d+)?)\s*bath", raw["text"], re.IGNORECASE)
    sqft_m = re.search(r"([\d,]+)\s*sq\.?\s*ft", raw["text"], re.IGNORECASE)
    base_m = re.search(r"\$([\d,]+)\s*Base Rent", raw["text"])
    total_m = re.search(r"\$([\d,.]+)\s*/mo", raw["text"])

    def to_int(m, group=1):
        return int(m.group(group).replace(",", "").split(".")[0]) if m else None

    avail = next((l for l in lines if re.match(r"^Avail", l, re.IGNORECASE)), "—")
    promo_text = raw.get("promo", "") + " " + raw["text"]
    promotion = parse_promo(promo_text)

    return {
        "source": "Maxwell",
        "floorplan": floorplan,
        "unit": raw["unit"],
        "address": "1 S Bascom Ave, San Jose, CA",
        "url": raw["url"],
        "availability": avail,
        "bedrooms": to_int(bed_m),
        "bathrooms": to_int(bath_m),
        "sqft": to_int(sqft_m),
        "base_rent": to_int(base_m),
        "total_rent": to_int(total_m),
        "a_c": bool(re.search(r"\bA/?C\b|air.{0,4}condition|central air", raw["text"], re.IGNORECASE)),
        "promotion": promotion,
        "coords": COORDS,
    }
