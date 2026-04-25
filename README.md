# apartment-hunter

Scrapes available units from four Bay Area apartment properties and prints a filtered table in the terminal. Optionally emails a daily HTML report.

**Properties covered:**
- Maxwell at Bascom (San Jose)
- Prometheus Oak Umber (Sunnyvale)
- Lyn Haven (Sunnyvale)
- Diridon West (San Jose)

Shows base rent, effective rent after promotions, sq ft, availability, and lease concessions.

## Setup

```bash
pip install -e .
playwright install chromium
playwright install chrome   # needed for Prometheus (Cloudflare bypass)
```

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Email is sent via [Resend](https://resend.com) (free tier, 3k emails/month). Create an API key at resend.com and set `SMTP_PASSWORD` to it.

## Usage

```bash
# Print tables in terminal (default max $3,100/mo)
apartment-hunter

# Custom price cap
apartment-hunter --max-price 2800

# Also send email report
apartment-hunter --email

# Print the cron setup command (daily 8 AM)
apartment-hunter --setup-cron
```

## Scheduling

To install the daily cron job:

```bash
(crontab -l 2>/dev/null; echo '0 8 * * * apartment-hunter --email >> ~/.apartment-hunter.log 2>&1') | crontab -
```

To remove it:

```bash
crontab -l | grep -v 'apartment-hunter' | crontab -
```
