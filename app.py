"""
ASCENT 2026 — Dashboard + API
Run: python app.py
"""

import csv
import hashlib
import io
import os
import threading
import time
import urllib.parse
import uuid
from flask import Flask, request, jsonify, session, redirect, url_for, render_template_string, send_from_directory
from events import EVENTS

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "ascent-2026-secret-key")

DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "ascent2026")
PAGES_BASE = "https://sauhard74.github.io/Email_Sender"

# In-memory job store
jobs = {}


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
  .error { color: #ff4444; background: #1a0000; border: 1px solid #440000; padding: 12px 16px; border-radius: 8px; margin-bottom: 16px; font-size: 14px; }
  .success { color: #44ff44; background: #001a00; border: 1px solid #004400; padding: 12px 16px; border-radius: 8px; margin-bottom: 16px; font-size: 14px; }
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

</body>
</html>
"""

PROCESSING_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Processing — ASCENT 2026</title>
<meta http-equiv="refresh" content="3;url=/job/{{ job_id }}">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0a; color: #fff; display: flex; justify-content: center; align-items: center; min-height: 100vh; text-align: center; }
  .card { background: #141414; border: 1px solid #222; border-radius: 12px; padding: 48px; max-width: 500px; }
  h1 { font-size: 28px; letter-spacing: 3px; margin-bottom: 8px; }
  .event { color: #0077B5; font-size: 16px; margin-bottom: 24px; }
  .status { color: #ffaa00; font-size: 18px; margin-bottom: 8px; }
  .detail { color: #888; font-size: 14px; margin-bottom: 24px; }
  .progress { color: #ccc; font-size: 14px; }
  .spinner { display: inline-block; width: 24px; height: 24px; border: 3px solid #333; border-top-color: #0077B5; border-radius: 50%; animation: spin 0.8s linear infinite; margin-bottom: 16px; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .done { color: #44ff44; }
</style>
</head>
<body>
<div class="card">
  <h1>ASCENT</h1>
  <p class="event">{{ event_name }}</p>

  {% if status == 'processing' %}
  <div class="spinner"></div>
  <p class="status">Processing {{ total }} registrant(s)...</p>
  <p class="detail">{{ processed }} / {{ total }} done</p>
  <p class="progress">This page refreshes automatically.</p>
  {% elif status == 'done' %}
  <p class="status done">Done!</p>
  <p class="detail">Redirecting to results...</p>
  <meta http-equiv="refresh" content="0;url=/results/{{ job_id }}">
  {% elif status == 'error' %}
  <p class="status" style="color:#ff4444;">Error</p>
  <p class="detail">{{ error }}</p>
  <a href="/dashboard" style="color:#0077B5;">Back to Dashboard</a>
  {% endif %}
</div>
</body>
</html>
"""

RESULTS_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Results — ASCENT 2026</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0a; color: #fff; padding: 24px; }
  .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 32px; }
  .header h1 { font-size: 28px; letter-spacing: 3px; }
  .header a { color: #888; text-decoration: none; font-size: 13px; }
  .header a:hover { color: #fff; }
  .success { color: #44ff44; background: #001a00; border: 1px solid #004400; padding: 12px 16px; border-radius: 8px; margin-bottom: 16px; font-size: 14px; }
  .stats { color: #888; font-size: 14px; margin-bottom: 16px; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th { background: #1a1a1a; color: #888; text-align: left; padding: 10px 12px; border-bottom: 1px solid #333; letter-spacing: 1px; font-size: 11px; text-transform: uppercase; }
  td { padding: 10px 12px; border-bottom: 1px solid #1a1a1a; color: #ccc; max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  td a { color: #0077B5; text-decoration: none; }
  td a:hover { text-decoration: underline; }
  tr:hover td { background: #111; }
  .back { display: inline-block; margin-top: 24px; color: #0077B5; text-decoration: none; font-size: 14px; }
</style>
</head>
<body>
<div class="header">
  <h1>ASCENT Dashboard</h1>
  <a href="/logout">Logout</a>
</div>

{% if push_status %}
<div class="success">{{ push_status }}</div>
{% endif %}

<h2 style="color:#ccc; margin-bottom:16px;">Results</h2>
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
      <td><a href="{{ r.ticket_url }}" target="_blank">View</a></td>
      <td><a href="{{ r.share_url }}" target="_blank">View</a></td>
      <td><a href="{{ r.linkedin_url }}" target="_blank">Share</a></td>
    </tr>
    {% endfor %}
  </tbody>
</table>

<a href="/dashboard" class="back">Upload another CSV</a>

</body>
</html>
"""


# ── Background processing ────────────────────────────────────

def process_job(job_id, registrant_list, event_name):
    """Run in a background thread."""
    job = jobs[job_id]
    try:
        from batch_processor import process_batch
        from sheet_sync import sync_results_to_sheet

        results, push_status = process_batch(registrant_list, event_name, progress_callback=lambda: job.update({"processed": job["processed"] + 1}))

        sheet_status = sync_results_to_sheet(results, event_name)
        push_status = f"{push_status} | Sheet: {sheet_status}"

        job["results"] = results
        job["push_status"] = push_status
        job["status"] = "done"

    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)


# ── Serve files ──────────────────────────────────────────────

@app.route("/output/<path:filename>")
def serve_output(filename):
    return send_from_directory("output", filename)

@app.route("/share/<path:filename>")
def serve_share(filename):
    return send_from_directory("share", filename)


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

    error = None

    if request.method == "POST":
        event_name = request.form.get("event_name")
        csv_file = request.files.get("csv_file")

        if not event_name:
            error = "Please select an event."
        elif not csv_file or not csv_file.filename.endswith(".csv"):
            error = "Please upload a valid CSV file."
        else:
            try:
                stream = io.StringIO(csv_file.stream.read().decode("utf-8-sig"))
                reader = csv.DictReader(stream)

                rows = []
                for row in reader:
                    name = row.get("Candidate's Name", "").strip()
                    email = row.get("Candidate's Email", "").strip()
                    team_id = row.get("Team ID", "").strip()
                    if name and email:
                        rows.append({"name": name, "email": email, "team_id": team_id})

                if not rows:
                    error = "No valid rows found."
                else:
                    registrant_list = []
                    for row in rows:
                        email_hash = hashlib.md5(row["email"].encode()).hexdigest()[:6]
                        reg_id = f"{row['team_id']}-{email_hash}"
                        registrant_list.append({
                            "name": row["name"],
                            "email": row["email"],
                            "team_id": row["team_id"],
                            "registration_id": reg_id,
                            "event_name": event_name,
                            "date_time": "17:05:2026 :: 10:00",
                        })

                    # Create background job
                    job_id = str(uuid.uuid4())[:8]
                    jobs[job_id] = {
                        "status": "processing",
                        "event_name": event_name,
                        "total": len(registrant_list),
                        "processed": 0,
                        "results": None,
                        "push_status": None,
                        "error": None,
                    }

                    thread = threading.Thread(
                        target=process_job,
                        args=(job_id, registrant_list, event_name),
                    )
                    thread.start()

                    return redirect(f"/job/{job_id}")

            except Exception as e:
                error = f"Error: {e}"

    return render_template_string(DASHBOARD_HTML, events=EVENTS, error=error)


# ── Job status + results ─────────────────────────────────────

@app.route("/job/<job_id>")
def job_status(job_id):
    if not session.get("authenticated"):
        return redirect(url_for("login"))

    job = jobs.get(job_id)
    if not job:
        return redirect(url_for("dashboard"))

    return render_template_string(
        PROCESSING_HTML,
        job_id=job_id,
        status=job["status"],
        event_name=job["event_name"],
        total=job["total"],
        processed=job["processed"],
        error=job.get("error"),
    )

@app.route("/results/<job_id>")
def job_results(job_id):
    if not session.get("authenticated"):
        return redirect(url_for("login"))

    job = jobs.get(job_id)
    if not job or job["status"] != "done":
        return redirect(f"/job/{job_id}")

    return render_template_string(
        RESULTS_HTML,
        results=job["results"],
        event_name=job["event_name"],
        push_status=job["push_status"],
    )


# ── API status endpoint for AJAX polling ─────────────────────

@app.route("/api/job/<job_id>")
def api_job_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify({
        "status": job["status"],
        "processed": job["processed"],
        "total": job["total"],
    })


# ── Webhook (kept for future use) ───────────────────────────

@app.route("/webhook/register", methods=["POST"])
def handle_registration():
    from ticket_generator import generate_ticket_image
    from share_generator import generate_share_page

    data = request.get_json(force=True)
    name = data.get("name") or data.get("participant_name", "Participant")
    email = data.get("email") or data.get("email_address", "")
    registration_id = data.get("registration_id") or data.get("id", "REG000")
    event_name = data.get("opportunity_title") or data.get("event_name", "ASCENT")

    if not email:
        return jsonify({"error": "No email found in payload"}), 400

    registrant = {
        "name": name, "email": email, "registration_id": registration_id,
        "event_name": event_name, "date_time": "17:05:2026 :: 10:00",
    }

    ticket_path = generate_ticket_image(registrant)
    share_url = generate_share_page(registrant)
    return jsonify({"status": "success", "ticket_path": ticket_path, "share_url": share_url}), 200


if __name__ == "__main__":
    app.run(debug=True, port=8080)
