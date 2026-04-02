"""
share_generator.py
Generates a personalized LinkedIn share page for each registrant:
  1. Renders the ticket HTML template at 1200x630 via Playwright → PNG
  2. Creates a static HTML page with OG meta tags pointing to the PNG
  3. Returns the GitHub Pages URL for use in the email
"""

import os
import re
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright
from ticket_generator import generate_qr_code

SHARE_DIR = "share"
TEMPLATE_DIR = "templates"
GITHUB_PAGES_BASE = "https://sauhard74.github.io/Email_Sender/share"

os.makedirs(SHARE_DIR, exist_ok=True)


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')


def generate_share_page(registrant: dict) -> str:
    """
    Generate a personalized share poster PNG and static HTML page.
    Returns the full GitHub Pages URL for the share page.
    """
    reg_id = registrant["registration_id"]
    name_slug = slugify(registrant["name"])
    filename = f"{reg_id}-{name_slug}"

    png_path = os.path.join(SHARE_DIR, f"{filename}.png")
    html_page_path = os.path.join(SHARE_DIR, f"{filename}.html")

    # Step 1 — Generate QR code
    qr_path = generate_qr_code(reg_id)

    # Step 2 — Render ticket HTML template with registrant data
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template("ticket.html")

    ticket_html = template.render(
        participant_name=registrant["name"].upper(),
        event_name=registrant["event_name"].upper(),
        date_time=registrant["date_time"],
        registration_id=reg_id,
        qr_code_path=f"file://{qr_path}",
    )

    # Save rendered ticket HTML temporarily
    temp_html = os.path.abspath(os.path.join(SHARE_DIR, f"_temp_{filename}.html"))
    with open(temp_html, "w", encoding="utf-8") as f:
        f.write(ticket_html)

    # Step 3 — Screenshot at 1200x630 (LinkedIn OG image size)
    abs_png_path = os.path.abspath(png_path)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 630})
        page.goto(f"file://{temp_html}")
        page.wait_for_load_state("networkidle")

        ticket_el = page.query_selector("#ticket")
        if ticket_el:
            ticket_el.screenshot(path=abs_png_path)
        else:
            page.screenshot(path=abs_png_path)

        browser.close()

    # Clean up temp HTML
    os.remove(temp_html)

    # Step 4 — Create static HTML page with OG meta tags
    share_page_url = f"{GITHUB_PAGES_BASE}/{filename}.html"
    og_image_url = f"{GITHUB_PAGES_BASE}/{filename}.png"

    # Build the LinkedIn desktop URL with pre-filled caption
    share_text = (
        "🚀 Just registered for ASCENT 2026 — Escape the Ordinary!\n\n"
        "Excited to be part of Scaler School of Technology's biggest fest.\n\n"
        "📅 17th May 2026 | Bengaluru\n\n"
        "Don't miss out — register now on Unstop!\n\n"
        "#ASCENT2026 #ScalerSchoolOfTechnology #EscapeTheOrdinary #TechFest\n\n"
        f"{share_page_url}"
    )
    import urllib.parse
    encoded_text = urllib.parse.quote(share_text, safe='')
    linkedin_desktop_url = f"https://www.linkedin.com/feed/?shareActive=true&text={encoded_text}"
    encoded_share_url = urllib.parse.quote(share_page_url, safe='')
    linkedin_mobile_url = f"https://www.linkedin.com/sharing/share-offsite/?url={encoded_share_url}"

    og_html = f"""<!DOCTYPE html>
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
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #0a0a0a;
      color: #fff;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      text-align: center;
      padding: 20px;
    }}
    .container {{ max-width: 700px; }}
    h1 {{ font-size: 48px; letter-spacing: 6px; margin-bottom: 8px; }}
    .tagline {{ color: #888; font-size: 14px; letter-spacing: 3px; margin-bottom: 24px; }}
    .poster {{ width: 100%; max-width: 600px; border-radius: 12px; margin-bottom: 24px; }}
    .details {{ color: #ccc; font-size: 16px; line-height: 1.8; margin-bottom: 24px; }}
    .share-btn {{
      display: none;
      background: #0077B5;
      color: #fff;
      border: none;
      padding: 16px 40px;
      border-radius: 8px;
      font-size: 17px;
      font-weight: bold;
      letter-spacing: 1px;
      cursor: pointer;
      margin-top: 8px;
    }}
    .share-btn:active {{ background: #005f8f; }}
    .status {{ color: #888; font-size: 14px; margin-top: 16px; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>ASCENT</h1>
    <p class="tagline">ESCAPE THE ORDINARY</p>
    <img id="poster" src="{filename}.png" alt="{registrant['name']}'s ASCENT 2026 Ticket" class="poster" />
    <p class="details">
      <strong>{registrant['name']}</strong> is attending ASCENT 2026!<br>
      Scaler School of Technology's biggest tech fest<br>
      17th May 2026 &bull; Bengaluru
    </p>
    <button id="shareBtn" class="share-btn">Share on LinkedIn</button>
    <p class="status" id="status"></p>
  </div>

  <script>
    const isMobile = /Android|iPhone|iPad|iPod|webOS|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    const statusEl = document.getElementById('status');
    const shareBtn = document.getElementById('shareBtn');

    const shareText = '🚀 Just registered for ASCENT 2026 — Escape the Ordinary!\\n\\nExcited to be part of Scaler School of Technology\\'s biggest fest.\\n\\n📅 17th May 2026 | Bengaluru\\n\\nDon\\'t miss out — register now on Unstop!\\n\\n#ASCENT2026 #ScalerSchoolOfTechnology #EscapeTheOrdinary #TechFest';

    if (isMobile) {{
      // Mobile: show share button, use Web Share API on tap
      shareBtn.style.display = 'inline-block';

      shareBtn.addEventListener('click', async () => {{
        try {{
          const res = await fetch('{filename}.png');
          const blob = await res.blob();
          const file = new File([blob], 'ASCENT-2026-Ticket.png', {{ type: 'image/png' }});

          if (navigator.canShare && navigator.canShare({{ files: [file] }})) {{
            await navigator.share({{
              text: shareText,
              files: [file],
            }});
          }} else {{
            // Fallback: open LinkedIn share-offsite
            window.location.href = '{linkedin_mobile_url}';
          }}
        }} catch (e) {{
          if (e.name !== 'AbortError') {{
            // Share failed (not user cancel) — fallback
            window.location.href = '{linkedin_mobile_url}';
          }}
        }}
      }});
    }} else {{
      // Desktop: auto-redirect to LinkedIn with pre-filled caption
      statusEl.textContent = 'Redirecting to LinkedIn...';
      window.location.href = '{linkedin_desktop_url}';
    }}
  </script>
</body>
</html>"""

    with open(html_page_path, "w", encoding="utf-8") as f:
        f.write(og_html)

    print(f"  → Share page saved: {html_page_path}")
    print(f"  → Share poster saved: {png_path}")
    return share_page_url
