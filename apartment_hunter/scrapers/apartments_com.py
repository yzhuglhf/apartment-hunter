import re

from playwright.sync_api import Page, sync_playwright

URL = "https://www.apartments.com/under-3000"

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

_AC_RE = re.compile(r"\bA/?C\b|air.{0,4}condition|central air", re.IGNORECASE)


def scrape(max_price: int = 3000) -> list[dict]:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome",
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        ctx = browser.new_context(
            user_agent=_USER_AGENT,
            viewport={"width": 1280, "height": 800},
            locale="en-US",
        )
        page = ctx.new_page()
        page.add_init_script(_STEALTH_JS)

        page.goto(URL, wait_until="load", timeout=30_000)
        _dismiss_overlays(page)
        page.wait_for_timeout(4000)

        listings = _read_listings(page)

        # Filter by price first so we only visit detail pages we care about
        affordable = [u for u in listings if (u["base_rent"] or 0) <= max_price]

        for i, u in enumerate(affordable):
            print(f"  Checking amenities {i + 1}/{len(affordable)}: {u['floorplan'][:40]}...", end="\r")
            if u["url"]:
                u["a_c"] = _detail_has_ac(page, u["url"])

        if affordable:
            print()  # newline after the progress line

        browser.close()
    return affordable


def _dismiss_overlays(page: Page) -> None:
    for selector in [
        "button[id*='accept' i]",
        "button[aria-label*='accept' i]",
        "button[aria-label*='close' i]",
        "#cookie-consent-accept",
        ".modal-close-button",
    ]:
        try:
            btn = page.query_selector(selector)
            if btn and btn.is_visible():
                btn.click()
                page.wait_for_timeout(500)
        except Exception:
            pass


def _detail_has_ac(page: Page, url: str) -> bool:
    try:
        page.goto(url, wait_until="load", timeout=20_000)
        page.wait_for_timeout(1500)
        text = page.evaluate("() => document.body.innerText")
        return bool(_AC_RE.search(text))
    except Exception:
        return False


def _read_listings(page: Page) -> list[dict]:
    raw = page.evaluate("""() => {
        const SELECTORS = [
            'article[data-listingid]',
            'li[data-listingid]',
            'li.mortar-wrapper[data-listingid]',
            '.placard',
            '[data-listing-id]',
        ];
        let cards = [];
        for (const sel of SELECTORS) {
            cards = [...document.querySelectorAll(sel)];
            if (cards.length) break;
        }
        return cards.map(card => ({
            id: card.getAttribute('data-listingid') || card.getAttribute('data-listing-id') || '',
            title: (
                card.querySelector('.js-placardTitle, [class*="placardTitle" i], [class*="property-title" i]')
                    ?.innerText?.trim()
                || card.querySelector('a[class*="title" i], h2, h3')?.innerText?.trim()
                || ''
            ),
            address: (
                card.querySelector('[class*="address" i], address, [class*="location" i]')
                    ?.innerText?.trim() || ''
            ),
            url: card.querySelector('a[href]')?.href || '',
            text: card.innerText.trim(),
        }));
    }""")

    if not raw:
        title = page.title()
        print(f"  [apartments.com] page title: {title!r} — no listing cards matched")

    return [_parse(r) for r in raw if r.get("text")]


def _parse(raw: dict) -> dict:
    text = raw.get("text", "")

    prices = [int(m.replace(",", "")) for m in re.findall(r"\$([\d,]+)", text)]
    base_rent = min(prices) if prices else None

    bed_m = re.search(r"(\d+)\s*(?:bed|br)\b", text, re.IGNORECASE)
    bath_m = re.search(r"(\d+(?:\.\d+)?)\s*ba(?:th)?\b", text, re.IGNORECASE)
    sqft_m = re.search(r"([\d,]+)\s*sq\.?\s*ft", text, re.IGNORECASE)

    def to_int(m, group=1):
        return int(m.group(group).replace(",", "").split(".")[0]) if m else None

    avail = next(
        (l.strip() for l in text.splitlines() if re.search(r"avail|now|date", l, re.IGNORECASE)),
        "—",
    )

    return {
        "source": "Apartments.com",
        "floorplan": raw.get("title") or "—",
        "unit": raw.get("id") or "—",
        "address": raw.get("address") or "",
        "url": raw.get("url") or "",
        "availability": avail,
        "bedrooms": to_int(bed_m),
        "bathrooms": to_int(bath_m),
        "sqft": to_int(sqft_m),
        "base_rent": base_rent,
        "total_rent": None,
        "a_c": False,  # filled in by detail page check in scrape()
        "coords": None,
    }
