import os
import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def build_html(sections: list[dict], max_price: int) -> str:
    today = date.today().strftime("%B %d, %Y")
    body = ""

    for sec in sections:
        title = sec["title"]
        if not sec["rows"]:
            body += f'<p style="color:#888;font-style:italic">{title}: no units found</p>\n'
            continue

        ths = "".join(
            f'<th style="padding:8px 14px;text-align:left;white-space:nowrap">{c}</th>'
            for c in sec["cols"]
        )
        trs = ""
        for i, row in enumerate(sec["rows"]):
            bg = "#f7f7f7" if i % 2 else "#ffffff"
            tds = "".join(
                f'<td style="padding:8px 14px;border-bottom:1px solid #e0e0e0">{v}</td>'
                for v in row
            )
            trs += f'<tr style="background:{bg}">{tds}</tr>\n'

        body += f"""
<h3 style="margin:28px 0 8px;color:#1a1a2e;border-left:4px solid #e94560;padding-left:10px">{title}</h3>
<div style="overflow-x:auto">
  <table style="border-collapse:collapse;width:100%;font-size:14px">
    <thead><tr style="background:#1a1a2e;color:#fff">{ths}</tr></thead>
    <tbody>{trs}</tbody>
  </table>
</div>
"""

    return f"""<!DOCTYPE html>
<html>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#222;max-width:980px;margin:24px auto;padding:0 16px">
  <h2 style="color:#1a1a2e;margin-bottom:4px">Apartment Report &mdash; {today}</h2>
  <p style="color:#666;margin-top:0">Units with base rent &le; ${max_price:,}/mo</p>
  {body}
  <hr style="margin-top:40px;border:none;border-top:1px solid #e0e0e0">
  <p style="color:#bbb;font-size:12px">Sent by apartment-hunter</p>
</body>
</html>"""


def send(html: str, to: str, subject: str) -> None:
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER", "")
    password = os.environ.get("SMTP_PASSWORD", "")

    if not all([user, password, to]):
        raise ValueError("Set SMTP_USER, SMTP_PASSWORD, and ALERT_EMAIL in .env")

    msg = MIMEMultipart("alternative")
    # Resend requires a real sender address; default to their sandbox address
    from_addr = os.environ.get("SMTP_FROM") or (
        "onboarding@resend.dev" if user == "resend" else user
    )
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to
    msg.attach(MIMEText(html, "html"))

    if port == 465:
        # SSL (Resend, some providers)
        import ssl
        with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context()) as smtp:
            smtp.login(user, password)
            smtp.sendmail(from_addr, to, msg.as_string())
    else:
        # STARTTLS (Gmail port 587, etc.)
        with smtplib.SMTP(host, port) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(user, password)
            smtp.sendmail(from_addr, to, msg.as_string())
