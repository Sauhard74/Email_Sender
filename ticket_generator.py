"""
ticket_generator.py
Fills the HTML ticket template with registrant data and
renders it to a PNG image using Playwright (headless Chromium).

Install deps:
    pip install playwright jinja2 qrcode pillow
    playwright install chromium
"""

import os
import qrcode
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

OUTPUT_DIR = "output"
TEMPLATE_DIR = "templates"

os.makedirs(OUTPUT_DIR, exist_ok=True)


def generate_qr_code(registration_id: str) -> str:
    """Generate a QR code PNG for the registration ID and return its file path."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=8,
        border=1,
    )
    qr.add_data(f"https://ascent.scaler.com/")
    qr.make(fit=True)

    img = qr.make_image(fill_color="white", back_color="black")
    qr_path = os.path.join(OUTPUT_DIR, f"qr_{registration_id}.png")
    img.save(qr_path)
    return os.path.abspath(qr_path)


def generate_ticket_image(registrant: dict) -> str:
    """
    1. Generates QR code for the registrant.
    2. Renders the Jinja2 HTML ticket template with their details.
    3. Takes a screenshot with Playwright → returns path to the PNG.
    """
    reg_id = registrant["registration_id"]

    # Step 1 — QR code
    qr_path = generate_qr_code(reg_id)

    # Step 2 — Fill HTML template
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template("ticket.html")

    html_content = template.render(
        participant_name=registrant["name"].upper(),
        event_name=registrant["event_name"].upper(),
        date_time=registrant["date_time"],
        registration_id=reg_id,
        qr_code_path=f"file://{qr_path}",   # absolute path so browser can load it
    )

    # Save filled HTML temporarily
    html_path = os.path.abspath(os.path.join(OUTPUT_DIR, f"ticket_{reg_id}.html"))
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # Step 3 — Screenshot with Playwright
    ticket_png_path = os.path.abspath(os.path.join(OUTPUT_DIR, f"ticket_{reg_id}.png"))

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        # Load the HTML file
        page.goto(f"file://{html_path}")
        page.wait_for_load_state("networkidle")

        # Screenshot only the ticket element (fits exactly)
        ticket_element = page.query_selector("#ticket")
        ticket_element.screenshot(path=ticket_png_path)

        browser.close()

    print(f"  → Ticket PNG saved: {ticket_png_path}")
    return ticket_png_path
