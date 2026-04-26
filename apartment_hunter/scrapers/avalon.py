import re

from playwright.sync_api import Page, sync_playwright

from apartment_hunter.scrapers.utils import parse_promo

URL = "https://www.avaloncommunities.com/california/san-jose-apartments/avalon-willow-glen/"
COORDS = (37.3016, -121.8615)  # 3200 Rubino Dr, San Jose CA 95125

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def scrape() -> list[dict]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent=_USER_AGENT,
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.new_page()
        page.goto(URL, wait_until="load", timeout=30_000)
        page.wait_for_selector(".unit-item", timeout=15_000)
        page.wait_for_timeout(2000)
        _load_all(page)
        property_promo = _get_promo_text(page)
        units = [u for u in _collect_units(page, property_promo) if u.get("floor") != 1]
        browser.close()
    return units


def _load_all(page: Page):
    try:
        btn = page.locator("button:has-text('Load All')")
        if btn.count() > 0:
            btn.first.click()
            page.wait_for_timeout(3000)
    except Exception:
        pass


def _get_promo_text(page: Page) -> str | None:
    # Click the first specials-info button to reveal its tooltip text
    try:
        page.click('[data-ea-cta-link="specials-info"]', timeout=3_000)
        page.wait_for_timeout(600)
        tooltip = page.evaluate("""() => {
            const tips = [...document.querySelectorAll('[role="tooltip"]')];
            const tip = tips.find(t => !t.classList.contains('specials-tag'));
            return tip ? tip.innerText.trim() : '';
        }""")
        if tooltip:
            return parse_promo(tooltip) or tooltip
    except Exception:
        pass

    # Fallback: scan the full page body for a promo pattern
    try:
        return parse_promo(page.evaluate("() => document.body.innerText"))
    except Exception:
        return None


def _collect_units(page: Page, property_promo: str | None) -> list[dict]:
    raw = page.evaluate("""() =>
        [...document.querySelectorAll('.unit-item')].map(card => ({
            unit: (card.querySelector('.ant-card-meta-title')?.innerText || '').split('\\n')[0].trim(),
            desc: (card.querySelector('.description')?.innerText || '').trim(),
            price: (card.querySelector('.unit-price')?.innerText || '').trim(),
            term: (card.querySelector('.term-length')?.innerText || '').trim(),
            avail: (card.querySelector('.available-date')?.innerText || '').trim() || '—',
            hasSpecial: !!card.querySelector('.specials-tag'),
            url: card.querySelector('a.unit-item-details-title')?.href || '',
        }))
    """)
    return [u for r in raw if r["unit"] for u in [_parse(r, property_promo)] if u]


def _parse(raw: dict, property_promo: str | None) -> dict | None:
    unit = raw["unit"]

    # Unit format "001-40210": third digit of the second group is the floor
    floor_m = re.search(r"-\d\d(\d)", unit)
    floor = int(floor_m.group(1)) if floor_m else None

    desc = raw["desc"]
    bed_m = re.search(r"(\d+)\s*bed", desc, re.IGNORECASE)
    bath_m = re.search(r"(\d+(?:\.\d+)?)\s*bath", desc, re.IGNORECASE)
    sqft_m = re.search(r"([\d,]+)\s*sqft", desc, re.IGNORECASE)

    price_digits = re.sub(r"[^\d]", "", raw["price"])
    base_rent = int(price_digits) if price_digits else None

    term_m = re.search(r"(\d+)\s*mo", raw["term"])
    lease_months = int(term_m.group(1)) if term_m else 12

    def to_int(m, group=1):
        return int(m.group(group).replace(",", "").split(".")[0]) if m else None

    beds = to_int(bed_m)
    floorplan = f"{beds}BR" if beds else "—"

    return {
        "source": "Avalon Willow Glen",
        "floorplan": floorplan,
        "unit": unit,
        "floor": floor,
        "address": "3200 Rubino Dr, San Jose CA 95125",
        "url": raw["url"] or URL,
        "availability": raw["avail"],
        "bedrooms": beds,
        "bathrooms": to_int(bath_m),
        "sqft": to_int(sqft_m),
        "base_rent": base_rent,
        "total_rent": None,
        "a_c": False,
        "promotion": property_promo if raw["hasSpecial"] else None,
        "lease_months": lease_months,
        "coords": COORDS,
    }
