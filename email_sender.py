"""
email_sender.py
Sends a beautifully formatted email with:
  - The ticket PNG as an inline image
  - A LinkedIn share button (opens LinkedIn with personalized ticket preview)
"""

import smtplib
import urllib.parse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
import os

# ── CONFIG ────────────────────────────────────────────────────
SMTP_HOST     = "smtp.gmail.com"
SMTP_PORT     = 587
SENDER_EMAIL  = os.environ.get("SMTP_EMAIL", "ascent_events@sst.scaler.com")
SENDER_PASS   = os.environ.get("SMTP_PASSWORD", "Test@1234")
SENDER_NAME   = "ASCENT Team"
# ─────────────────────────────────────────────────────────────


def build_linkedin_share_url(share_url: str) -> str:
    """Return the share page URL — it handles mobile vs desktop redirect."""
    return share_url


def build_email_html(registrant: dict, linkedin_url: str) -> str:
    """Build the HTML body of the email."""
    name = registrant["name"]
    event = registrant["event_name"]
    reg_id = registrant["registration_id"]

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: Arial, sans-serif; background: #0d0d0d; color: #fff; margin: 0; padding: 0; }}
  .container {{ max-width: 640px; margin: 0 auto; padding: 40px 20px; }}
  .header {{ text-align: center; margin-bottom: 32px; }}
  .header h1 {{ font-size: 36px; letter-spacing: 4px; color: #fff; margin: 0; }}
  .header p {{ color: #888; letter-spacing: 2px; font-size: 12px; margin-top: 4px; }}
  .greeting {{ font-size: 16px; color: #ccc; margin-bottom: 20px; line-height: 1.6; }}
  .ticket-section {{ text-align: center; margin: 24px 0; }}
  .ticket-section img {{ width: 100%; max-width: 560px; border-radius: 10px; }}
  .reg-id {{ text-align: center; color: #666; font-family: monospace; font-size: 13px; margin-top: 8px; }}
  .divider {{ border: none; border-top: 1px solid #222; margin: 32px 0; }}
  .linkedin-section {{ text-align: center; margin: 28px 0; }}
  .linkedin-section p {{ color: #aaa; font-size: 14px; margin-bottom: 16px; line-height: 1.5; }}
  .linkedin-btn {{
    display: inline-block;
    background: #0077B5;
    color: white;
    text-decoration: none;
    padding: 14px 32px;
    border-radius: 6px;
    font-size: 15px;
    font-weight: bold;
    letter-spacing: 1px;
  }}
  .share-preview {{
    background: #1a1a1a;
    border: 1px solid #333;
    border-radius: 8px;
    padding: 16px 20px;
    margin: 16px auto;
    max-width: 500px;
    text-align: left;
    font-size: 13px;
    color: #aaa;
    line-height: 1.8;
    word-wrap: break-word;
    white-space: normal;
  }}
  .hashtags {{ color: #0077B5; }}
  .copy-hint {{ color: #666; font-size: 11px; margin-top: 8px; }}
  .footer {{ text-align: center; color: #444; font-size: 11px; margin-top: 40px; line-height: 1.8; }}
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <h1>⋆ ASCENT</h1>
    <p>ESCAPE THE ORDINARY</p>
  </div>

  <div class="greeting">
    <p>Hey <strong style="color:white">{name}</strong> 👋</p>
    <p>Welcome aboard! Your registration for <strong style="color:white">{event}</strong> is confirmed.
    Find your entry ticket below - save it or screenshot it for the event.</p>
  </div>

  <!-- Ticket image (inline, attached as CID) -->
  <div class="ticket-section">
    <img src="cid:ticket_image" alt="Your ASCENT Ticket" />
    <div class="reg-id">Registration ID: {reg_id}</div>
  </div>

  <hr class="divider">

  <!-- LinkedIn Share Section -->
  <div class="linkedin-section">
    <p>
      🎉 Tell your network you're in! Your personalized ticket will show up as the preview card.
    </p>

    <a href="{linkedin_url}" class="linkedin-btn">
      Share on LinkedIn →
    </a>

    <p class="copy-hint">Copy-paste this as your caption:</p>

    <div class="share-preview">
      🚀 Just registered for ASCENT 2026 — Escape the Ordinary!<br><br>
      Excited to be part of Scaler School of Technology's biggest fest.<br><br>
      📅 17th May 2026 | Bengaluru<br><br>
      Don't miss out — register now on Unstop!<br><br>
      <span class="hashtags">#ASCENT2026 #ScalerSchoolOfTechnology #EscapeTheOrdinary #TechFest</span>
    </div>
  </div>

  <hr class="divider">

  <div class="footer">
    <p>ASCENT 2026 &nbsp;|&nbsp; Powered by Scaler School of Technology</p>
    <p>ascent.scaler.com &nbsp;|&nbsp; ascent_events@sst.scaler.com</p>
  </div>

</div>
</body>
</html>
"""


def send_registration_email(registrant: dict, ticket_image_path: str, share_url: str = "https://ascent.scaler.com"):
    """Send the confirmation email with ticket + LinkedIn share button."""

    linkedin_url = build_linkedin_share_url(share_url)

    # Build MIME message with alternative + related structure for inline images
    msg = MIMEMultipart("related")
    msg["Subject"] = f"🎟️ Your ASCENT Ticket is Ready, {registrant['name'].split()[0]}!"
    msg["From"]    = f"{SENDER_NAME} <{SENDER_EMAIL}>"
    msg["To"]      = registrant["email"]

    # Attach HTML body
    html_body = build_email_html(registrant, linkedin_url)
    msg_alternative = MIMEMultipart("alternative")
    msg.attach(msg_alternative)
    msg_alternative.attach(MIMEText(html_body, "html"))

    # Attach ticket image as inline (CID reference in the HTML)
    if os.path.exists(ticket_image_path):
        with open(ticket_image_path, "rb") as f:
            img = MIMEImage(f.read(), name=os.path.basename(ticket_image_path))
            img.add_header("Content-ID", "<ticket_image>")
            img.add_header("Content-Disposition", "inline", filename="ascent_ticket.png")
            msg.attach(img)

        # Also attach as a downloadable file
        with open(ticket_image_path, "rb") as f:
            attachment = MIMEBase("application", "octet-stream")
            attachment.set_payload(f.read())
            encoders.encode_base64(attachment)
            attachment.add_header(
                "Content-Disposition",
                f"attachment; filename=ASCENT_Ticket_{registrant['registration_id']}.png"
            )
            msg.attach(attachment)
    else:
        print(f"  ⚠️ Warning: Ticket image not found at {ticket_image_path}")

    # Send via Gmail SMTP
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASS)
            server.send_message(msg)
            print(f"  → Email delivered to {registrant['email']} ✅")
    except Exception as e:
        print(f"  ✗ Email failed: {e}")
