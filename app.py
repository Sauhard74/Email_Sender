"""
ASCENT - Unstop Registration Webhook Server
Run: python app.py
"""

from flask import Flask, request, jsonify
from ticket_generator import generate_ticket_image
from email_sender import send_registration_email
from share_generator import generate_share_page
import json

app = Flask(__name__)

# ── Health check ──────────────────────────────────────────────
@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "ASCENT mailer is running ✅"})


# ── Unstop Webhook Endpoint ───────────────────────────────────
@app.route("/webhook/register", methods=["POST"])
def handle_registration():
    """
    Unstop sends a POST request here every time someone registers.
    We parse the payload, generate a ticket, and email it to them.
    """
    data = request.get_json(force=True)
    print(f"\n📥 Webhook received:\n{json.dumps(data, indent=2)}")

    # ── Parse registrant info from Unstop payload ──
    # Adjust field names to match what Unstop actually sends you.
    # Print the raw payload first to confirm field names.
    name           = data.get("name") or data.get("participant_name", "Participant")
    email          = data.get("email") or data.get("email_address", "")
    registration_id = data.get("registration_id") or data.get("id", "REG000")
    event_name     = data.get("opportunity_title") or data.get("event_name", "ASCENT")

    if not email:
        return jsonify({"error": "No email found in payload"}), 400

    registrant = {
        "name": name,
        "email": email,
        "registration_id": registration_id,
        "event_name": event_name,
        "date_time": "17:05:2026 :: 10:00",   # hardcode or pull from your event config
    }

    print(f"✅ Processing registration for: {name} ({email})")

    # ── Generate ticket image ──
    ticket_path = generate_ticket_image(registrant)
    print(f"🎟️  Ticket generated: {ticket_path}")

    # ── Generate share page ──
    share_url = generate_share_page(registrant)
    print(f"🔗 Share page: {share_url}")

    # ── Send email ──
    send_registration_email(registrant, ticket_path, share_url)
    print(f"📧 Email sent to: {email}")

    return jsonify({"status": "success", "message": f"Ticket sent to {email}"}), 200


# ── Dry run endpoint (for testing without Unstop) ─────────────
@app.route("/test", methods=["GET"])
def test_run():
    """
    Hit this in your browser or with curl to do a full dry run:
    GET http://localhost:5000/test
    """
    fake_registrant = {
        "name": "Test User",
        "email": "syedzahurulhasan04@gmail.com",   # ← test email
        "registration_id": "REG20052",
        "event_name": "ASCENT 2026 Hackathon",
        "date_time": "17:05:2026 :: 10:00",
    }

    ticket_path = generate_ticket_image(fake_registrant)
    share_url = generate_share_page(fake_registrant)
    send_registration_email(fake_registrant, ticket_path, share_url)

    return jsonify({
        "status": "Dry run complete ✅",
        "ticket_saved_at": ticket_path,
        "share_page_url": share_url,
        "email_sent_to": fake_registrant["email"]
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
