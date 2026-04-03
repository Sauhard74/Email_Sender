"""
ASCENT 2026 — Dashboard + API
Run: python app.py
"""

import csv
import hashlib
import io
import os
import subprocess
from flask import Flask, request, jsonify, session, redirect, url_for, render_template_string
from ticket_generator import generate_ticket_image
from share_generator import generate_share_page
from events import EVENTS
import urllib.parse

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "ascent-2026-secret-key")

DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "ascent2026")

# ── GitHub Pages base URL ────────────────────────────────────
PAGES_BASE = "https://sauhard74.github.io/Email_Sender"


# ── HTML Templates ───────────────────────────────────────────

LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ASCENT 2026 — Dashboard</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0a; color: #fff; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
  .card { background: #141414; border: 1px solid #222; border-radius: 12px; padding: 40px; width: 400px; text-align: center; }
  h1 { font-size: 32px; letter-spacing: 4px; margin-bottom: 4px; }
  .tagline { color: #666; font-size: 12px; letter-spacing: 2px; margin-bottom: 32px; }
  input { width: 100%; padding: 12px 16px; border: 1px solid #333; border-radius: 8px; background: #1a1a1a; color: #fff; font-size: 14px; margin-bottom: 16px; }
  input:focus { outline: none; border-color: #0077B5; }
  button { width: 100%; padding: 12px; background: #1a6fff; color: #fff; border: none; border-radius: 8px; font-size: 15px; font-weight: bold; cursor: pointer; }
  button:hover { background: #1558cc; }
  .error { color: #ff4444; font-size: 13px; margin-bottom: 12px; }
</style>
</head>
<body>
<div class="card">
  <h1>ASCENT</h1>
  <p class="tagline">ESCAPE THE ORDINARY</p>
  {% if error %}<p class="error">{{ error }}</p>{% endif %}
  <form method="POST">
    <input type="password" name="password" placeholder="Enter dashboard password" autofocus>
    <button type="submit">Login</button>
  </form>
</div>
</body>
</html>
"""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ASCENT 2026 — Dashboard</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0a; color: #fff; padding: 24px; }
  .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 32px; }
  .header h1 { font-size: 28px; letter-spacing: 3px; }
  .header a { color: #888; text-decoration: none; font-size: 13px; }
  .header a:hover { color: #fff; }
  .upload-card { background: #141414; border: 1px solid #222; border-radius: 12px; padding: 32px; max-width: 600px; margin-bottom: 32px; }
  .upload-card h2 { font-size: 18px; margin-bottom: 20px; color: #ccc; }
  label { display: block; color: #888; font-size: 13px; margin-bottom: 6px; letter-spacing: 1px; }
  select, input[type="file"] { width: 100%; padding: 10px 12px; border: 1px solid #333; border-radius: 8px; background: #1a1a1a; color: #fff; font-size: 14px; margin-bottom: 16px; }
  select:focus { outline: none; border-color: #0077B5; }
  button { padding: 12px 32px; background: #1a6fff; color: #fff; border: none; border-radius: 8px; font-size: 15px; font-weight: bold; cursor: pointer; }
  button:hover { background: #1558cc; }
  button:disabled { background: #333; cursor: not-allowed; }
  .results { margin-top: 32px; }
  .results h2 { font-size: 18px; margin-bottom: 16px; color: #ccc; }
  .stats { color: #888; font-size: 14px; margin-bottom: 16px; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th { background: #1a1a1a; color: #888; text-align: left; padding: 10px 12px; border-bottom: 1px solid #333; letter-spacing: 1px; font-size: 11px; text-transform: uppercase; }
  td { padding: 10px 12px; border-bottom: 1px solid #1a1a1a; color: #ccc; max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  td a { color: #0077B5; text-decoration: none; }
  td a:hover { text-decoration: underline; }
  tr:hover td { background: #111; }
  .error { color: #ff4444; background: #1a0000; border: 1px solid #440000; padding: 12px 16px; border-radius: 8px; margin-bottom: 16px; font-size: 14px; }
  .success { color: #44ff44; background: #001a00; border: 1px solid #004400; padding: 12px 16px; border-radius: 8px; margin-bottom: 16px; font-size: 14px; }
  .processing { color: #ffaa00; font-size: 14px; }
</style>
</head>
<body>
<div class="header">
  <h1>ASCENT Dashboard</h1>
  <a href="/logout">Logout</a>
</div>

<div class="upload-card">
  <h2>Upload Registrations</h2>
  <form method="POST" enctype="multipart/form-data">
    <label>EVENT</label>
    <select name="event_name" required>
      <option value="" disabled selected>Select event...</option>
      {% for event in events %}
      <option value="{{ event.name }}">{{ event.name }}</option>
      {% endfor %}
    </select>

    <label>UNSTOP CSV</label>
    <input type="file" name="csv_file" accept=".csv" required>

    <button type="submit">Process Registrations</button>
  </form>
</div>

{% if error %}
<div class="error">{{ error }}</div>
{% endif %}

{% if results %}
<div class="results">
  {% if push_status %}
  <div class="success">{{ push_status }}</div>
  {% endif %}

  <h2>Results</h2>
  <p class="stats">Processed {{ results|length }} registrant(s) for {{ event_name }}</p>

  <table>
    <thead>
      <tr>
        <th>#</th>
        <th>Name</th>
        <th>Email</th>
        <th>Team ID</th>
        <th>Ticket PNG</th>
        <th>Share Page</th>
        <th>LinkedIn Share</th>
      </tr>
    </thead>
    <tbody>
      {% for r in results %}
      <tr>
        <td>{{ loop.index }}</td>
        <td>{{ r.name }}</td>
        <td>{{ r.email }}</td>
        <td>{{ r.team_id }}</td>
        <td><a href="{{ r.ticket_path }}" target="_blank">View</a></td>
        <td><a href="{{ r.share_url }}" target="_blank">View</a></td>
        <td><a href="{{ r.linkedin_url }}" target="_blank">Share</a></td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
{% endif %}

</body>
</html>
"""


# ── Auth ─────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if request.form.get("password") == DASHBOARD_PASSWORD:
            session["authenticated"] = True
            return redirect(url_for("dashboard"))
        error = "Wrong password"
    return render_template_string(LOGIN_HTML, error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ── Dashboard ────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def index():
    if not session.get("authenticated"):
        return redirect(url_for("login"))
    return redirect(url_for("dashboard"))


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if not session.get("authenticated"):
        return redirect(url_for("login"))

    results = None
    error = None
    event_name = None
    push_status = None

    if request.method == "POST":
        event_name = request.form.get("event_name")
        csv_file = request.files.get("csv_file")

        if not event_name:
            error = "Please select an event."
        elif not csv_file or not csv_file.filename.endswith(".csv"):
            error = "Please upload a valid CSV file."
        else:
            try:
                # Parse CSV
                stream = io.StringIO(csv_file.stream.read().decode("utf-8-sig"))
                reader = csv.DictReader(stream)

                rows = []
                for row in reader:
                    name = row.get("Candidate's Name", "").strip()
                    email = row.get("Candidate's Email", "").strip()
                    team_id = row.get("Team ID", "").strip()

                    if name and email:
                        rows.append({
                            "name": name,
                            "email": email,
                            "team_id": team_id,
                        })

                if not rows:
                    error = "No valid rows found. Check CSV has 'Candidate's Name', 'Candidate's Email', 'Team ID' columns."
                else:
                    results = []
                    for row in rows:
                        # Make registration ID unique per person (team_id + email hash)
                        email_hash = hashlib.md5(row["email"].encode()).hexdigest()[:6]
                        reg_id = f"{row['team_id']}-{email_hash}"

                        registrant = {
                            "name": row["name"],
                            "email": row["email"],
                            "registration_id": reg_id,
                            "event_name": event_name,
                            "date_time": "17:05:2026 :: 10:00",
                        }

                        # Generate ticket + share page
                        ticket_path = generate_ticket_image(registrant)
                        share_url = generate_share_page(registrant)

                        # Build LinkedIn share URL
                        encoded = urllib.parse.quote(share_url, safe='')
                        linkedin_url = f"https://www.linkedin.com/sharing/share-offsite/?url={encoded}"

                        results.append({
                            "name": row["name"],
                            "email": row["email"],
                            "team_id": row["team_id"],
                            "ticket_path": ticket_path,
                            "share_url": share_url,
                            "linkedin_url": linkedin_url,
                        })

                        print(f"  ✅ {row['name']} ({row['email']})")

                    # Git push share/ to GitHub Pages
                    try:
                        subprocess.run(["git", "add", "share/"], check=True)
                        subprocess.run(
                            ["git", "commit", "-m", f"Add share pages: {event_name} ({len(results)} registrants)"],
                            check=True
                        )
                        subprocess.run(["git", "push"], check=True)
                        push_status = f"Pushed {len(results)} share pages to GitHub Pages."
                    except subprocess.CalledProcessError as e:
                        push_status = f"Git push warning: {e} — share pages generated but may need manual push."

            except Exception as e:
                error = f"Error processing CSV: {e}"

    return render_template_string(
        DASHBOARD_HTML,
        events=EVENTS,
        results=results,
        event_name=event_name,
        error=error,
        push_status=push_status,
    )


# ── Webhook (kept for future use) ───────────────────────────

@app.route("/webhook/register", methods=["POST"])
def handle_registration():
    data = request.get_json(force=True)

    name = data.get("name") or data.get("participant_name", "Participant")
    email = data.get("email") or data.get("email_address", "")
    registration_id = data.get("registration_id") or data.get("id", "REG000")
    event_name = data.get("opportunity_title") or data.get("event_name", "ASCENT")

    if not email:
        return jsonify({"error": "No email found in payload"}), 400

    registrant = {
        "name": name,
        "email": email,
        "registration_id": registration_id,
        "event_name": event_name,
        "date_time": "17:05:2026 :: 10:00",
    }

    ticket_path = generate_ticket_image(registrant)
    share_url = generate_share_page(registrant)

    return jsonify({
        "status": "success",
        "ticket_path": ticket_path,
        "share_url": share_url,
    }), 200


if __name__ == "__main__":
    app.run(debug=True, port=8080)
