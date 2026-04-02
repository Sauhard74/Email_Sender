# ASCENT Mailer — Dry Run Guide
Complete step-by-step setup for the registration webhook + ticket emailer.

---

## FOLDER STRUCTURE
```
ascent_mailer/
├── app.py                 ← Flask server (webhook + /test endpoint)
├── ticket_generator.py    ← Generates QR code + renders ticket to PNG
├── email_sender.py        ← Sends email with ticket + LinkedIn share button
├── requirements.txt       ← All Python dependencies
├── templates/
│   └── ticket.html        ← The ASCENT ticket template (Jinja2)
└── output/                ← Generated QR codes + ticket PNGs land here
```

---

## STEP 1 — Prerequisites

Make sure you have Python 3.9+ installed.
```bash
python --version
```

---

## STEP 2 — Create a virtual environment

```bash
cd ascent_mailer
python -m venv venv

# Activate it:
# On Mac/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

---

## STEP 3 — Install dependencies

```bash
pip install -r requirements.txt
```

Then install Playwright's Chromium browser (used to screenshot the ticket):
```bash
playwright install chromium
```

---

## STEP 4 — Set up Gmail App Password

Your Gmail account needs an **App Password** (not your regular password).

1. Go to: https://myaccount.google.com/security
2. Make sure **2-Step Verification** is ON
3. Search for **"App Passwords"** → create one → select Mail + Other → name it "ASCENT Mailer"
4. Copy the 16-character password

Now open `email_sender.py` and fill in:
```python
SENDER_EMAIL = "your_actual_email@gmail.com"
SENDER_PASS  = "xxxx xxxx xxxx xxxx"   # the 16-char App Password
```

Also change the test email in `app.py` → `/test` route:
```python
"email": "your_test_email@gmail.com",   # where you want the test email sent
```

---

## STEP 5 — Run the server

```bash
python app.py
```

You should see:
```
 * Running on http://127.0.0.1:5000
 * Debug mode: on
```

---

## STEP 6 — DRY RUN (no Unstop needed)

Open your browser and go to:
```
http://localhost:5000/test
```

Or with curl:
```bash
curl http://localhost:5000/test
```

This will:
1. ✅ Generate a QR code PNG
2. ✅ Fill the ticket HTML template with fake data
3. ✅ Screenshot the ticket → save as PNG in /output
4. ✅ Send the email with the ticket + LinkedIn button to your test email

Expected response:
```json
{
  "status": "Dry run complete ✅",
  "ticket_saved_at": "/path/to/output/ticket_REG20045.png",
  "email_sent_to": "your_test_email@gmail.com"
}
```

Check your inbox — you should see the email within 30 seconds!

---

## STEP 7 — Test the webhook manually

Simulate what Unstop will send:
```bash
curl -X POST http://localhost:5000/webhook/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Priya Nair",
    "email": "your_test_email@gmail.com",
    "registration_id": "REG99001",
    "opportunity_title": "ASCENT Hackathon 2026"
  }'
```

Expected response:
```json
{
  "status": "success",
  "message": "Ticket sent to your_test_email@gmail.com"
}
```

---

## STEP 8 — Expose to internet (for real Unstop webhook)

Once local dry run works, expose your server using ngrok (free):

```bash
# Install ngrok: https://ngrok.com/download
ngrok http 5000
```

You'll get a URL like: `https://abc123.ngrok.io`

Set this as your webhook in Unstop:
```
https://abc123.ngrok.io/webhook/register
```

For production, deploy to **Railway** or **Render** (both free tier available).

---

## TROUBLESHOOTING

| Problem | Fix |
|---------|-----|
| `playwright install` fails | Run `pip install playwright` first, then `playwright install chromium` |
| Gmail auth error | Make sure 2FA is ON and you're using App Password, not your real password |
| QR code not showing in ticket | Check that the `output/` folder exists and has write permissions |
| Unstop field names don't match | Add a `print(data)` in the webhook handler to see the raw payload |

---

## HOW THE LINKEDIN SHARE WORKS

When the user clicks "Share on LinkedIn" in the email, it opens:
```
https://www.linkedin.com/shareArticle?mini=true&url=...&summary=...
```

This opens a LinkedIn dialog with the text pre-filled.
The user just clicks Post — no copying or typing needed.

To change the hashtags/text, edit `SHARE_TEXT` in `email_sender.py`.
