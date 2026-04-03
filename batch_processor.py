"""
batch_processor.py
Processes a list of registrants using a single browser instance.
Generates ticket PNGs + share pages, pushes everything to GitHub.
"""

import os
import re
import urllib.parse
import qrcode
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright
from github_push import push_share_files, push_file

OUTPUT_DIR = "output"
SHARE_DIR = "share"
TEMPLATE_DIR = "templates"
GITHUB_PAGES_BASE = "https://sauhard74.github.io/Email_Sender"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(SHARE_DIR, exist_ok=True)


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')


def _generate_qr(reg_id: str) -> str:
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=8, border=1)
    qr.add_data(f"https://ascent.scaler.com/")
    qr.make(fit=True)
    img = qr.make_image(fill_color="white", back_color="black")
    qr_path = os.path.join(OUTPUT_DIR, f"qr_{reg_id}.png")
    img.save(qr_path)
    return os.path.abspath(qr_path)


def _build_share_html(registrant: dict, filename: str) -> str:
    share_page_url = f"{GITHUB_PAGES_BASE}/share/{filename}.html"
    og_image_url = f"{GITHUB_PAGES_BASE}/share/{filename}.png"

    share_text = (
        "🚀 Just registered for ASCENT 2026 — Escape the Ordinary!\n\n"
        "Excited to be part of Scaler School of Technology's biggest fest.\n\n"
        "📅 17th May 2026 | Bengaluru\n\n"
        "Don't miss out — register now on Unstop!\n\n"
        "#ASCENT2026 #ScalerSchoolOfTechnology #EscapeTheOrdinary #TechFest\n\n"
        f"{share_page_url}"
    )
    encoded_text = urllib.parse.quote(share_text, safe='')
    linkedin_desktop_url = f"https://www.linkedin.com/feed/?shareActive=true&text={encoded_text}"
    encoded_share_url = urllib.parse.quote(share_page_url, safe='')
    linkedin_mobile_url = f"https://www.linkedin.com/sharing/share-offsite/?url={encoded_share_url}"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{registrant['name']} — ASCENT 2026</title>
  <meta property="og:title" content="{registrant['name']} is attending ASCENT 2026!" />
  <meta property="og:description" content="Escape the Ordinary — Scaler School of Technology's biggest tech fest. 17th May 2026, Bengaluru." />
  <meta property="og:image" content="{og_image_url}" />
  <meta property="og:image:width" content="1200" />
  <meta property="og:image:height" content="630" />
  <meta property="og:url" content="{share_page_url}" />
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="ASCENT 2026" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="{registrant['name']} is attending ASCENT 2026!" />
  <meta name="twitter:description" content="Escape the Ordinary — Scaler School of Technology's biggest tech fest." />
  <meta name="twitter:image" content="{og_image_url}" />
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, sans-serif; background: #0a0a0a; color: #fff; display: flex; justify-content: center; align-items: center; min-height: 100vh; text-align: center; padding: 20px; }}
    .status {{ color: #888; font-size: 16px; }}
  </style>
</head>
<body>
  <div><p class="status">Redirecting to LinkedIn...</p></div>
  <script>
    const isMobile = /Android|iPhone|iPad|iPod|webOS|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    if (isMobile) {{
      window.location.href = '{linkedin_mobile_url}';
    }} else {{
      window.location.href = '{linkedin_desktop_url}';
    }}
  </script>
</body>
</html>"""


def process_batch(registrants: list, event_name: str, progress_callback=None) -> list:
    """
    Process all registrants with a single browser instance.
    Returns list of result dicts with URLs.
    """
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template("ticket.html")
    results = []
    github_files = []  # files to push to GitHub

    with sync_playwright() as p:
        browser = p.chromium.launch()

        for registrant in registrants:
            reg_id = registrant["registration_id"]
            name_slug = slugify(registrant["name"])
            share_filename = f"{reg_id}-{name_slug}"

            # Generate QR code
            qr_path = _generate_qr(reg_id)

            # Render ticket HTML
            html_content = template.render(
                participant_name=registrant["name"].upper(),
                event_name=registrant["event_name"].upper(),
                date_time=registrant["date_time"],
                registration_id=reg_id,
                qr_code_path=f"file://{qr_path}",
            )

            # Save temp HTML
            html_path = os.path.abspath(os.path.join(OUTPUT_DIR, f"ticket_{reg_id}.html"))
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            # Screenshot ticket (reuse browser)
            ticket_png = os.path.abspath(os.path.join(OUTPUT_DIR, f"ticket_{reg_id}.png"))
            page = browser.new_page()
            page.goto(f"file://{html_path}")
            page.wait_for_load_state("networkidle")
            ticket_el = page.query_selector("#ticket")
            if ticket_el:
                ticket_el.screenshot(path=ticket_png)
            page.close()
            print(f"  → Ticket: {registrant['name']}")

            # Screenshot share poster (reuse browser)
            share_png = os.path.abspath(os.path.join(SHARE_DIR, f"{share_filename}.png"))
            page = browser.new_page(viewport={"width": 1200, "height": 630})
            page.goto(f"file://{html_path}")
            page.wait_for_load_state("networkidle")
            ticket_el = page.query_selector("#ticket")
            if ticket_el:
                ticket_el.screenshot(path=share_png)
            page.close()

            # Generate share HTML
            share_html_content = _build_share_html(registrant, share_filename)
            share_html_path = os.path.join(SHARE_DIR, f"{share_filename}.html")
            with open(share_html_path, "w", encoding="utf-8") as f:
                f.write(share_html_content)

            # Collect files to push
            github_files.append(f"{share_filename}.html")
            github_files.append(f"{share_filename}.png")

            # Build URLs
            ticket_github_url = f"{GITHUB_PAGES_BASE}/share/{share_filename}.png"
            share_url = f"{GITHUB_PAGES_BASE}/share/{share_filename}.html"
            encoded = urllib.parse.quote(share_url, safe='')
            linkedin_url = f"https://www.linkedin.com/sharing/share-offsite/?url={encoded}"

            results.append({
                "name": registrant["name"],
                "email": registrant["email"],
                "team_id": registrant.get("team_id", reg_id),
                "ticket_url": ticket_github_url,
                "share_url": share_url,
                "linkedin_url": linkedin_url,
            })

            print(f"  ✅ {registrant['name']} ({registrant['email']})")
            if progress_callback:
                progress_callback()

        browser.close()

    # Push all share files to GitHub in one go
    push_status = push_share_files(SHARE_DIR, github_files, event_name)

    return results, push_status
