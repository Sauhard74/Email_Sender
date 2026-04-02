# ASCENT 2026 — Automated Registration Scraper

Scrapes registrations from all ASCENT events on Unstop every hour, detects new registrants, generates personalized tickets, and sends emails with LinkedIn share buttons. Fully automated via GitHub Actions.

## How it works

```
Every hour (GitHub Actions cron):
  → Playwright logs into Unstop
  → Loops through all 15 event pages
  → Scrapes registrant data (name, email, college)
  → Compares with processed.json (already emailed)
  → New registrants → generate ticket → send email
  → Updates processed.json (committed to repo)
```

## Setup (one-time, 10 min)

### 1. Fork or clone this repo

### 2. Add your events to `events.py`

Get each event's ID from its Unstop URL:
```
unstop.com/manage/opportunity/{EVENT_ID}/profiles/all-registrations
```

### 3. Add GitHub Secrets

Go to: **Repo → Settings → Secrets and variables → Actions → New repository secret**

| Secret | Value |
|--------|-------|
| `UNSTOP_EMAIL` | Your Unstop login email |
| `UNSTOP_PASSWORD` | Your Unstop password |
| `SMTP_EMAIL` | Gmail address for sending emails |
| `SMTP_PASSWORD` | Gmail App Password ([generate here](https://myaccount.google.com/apppasswords)) |

### 4. Enable GitHub Actions

Go to: **Repo → Actions → Enable workflows**

### 5. Test manually

Go to: **Actions → ASCENT Registration Scraper → Run workflow**

Watch the logs to verify it logs in and scrapes correctly.

## Files

| File | Purpose |
|------|---------|
| `scraper.py` | Main script — login, scrape, detect new, trigger emails |
| `events.py` | Your 15 event IDs and names |
| `processed.json` | Tracks who's been emailed (auto-updated) |
| `new_registrants.csv` | Append-only log of all new registrants |
| `.github/workflows/scrape.yml` | GitHub Actions cron config |

## Local testing

```bash
pip install -r requirements.txt
playwright install chromium

export UNSTOP_EMAIL="your@email.com"
export UNSTOP_PASSWORD="your_password"

# Dry run (scrape only, no emails)
python scraper.py --dry-run

# Full run
python scraper.py
```

## Integrating with your team's email sender

The scraper auto-imports `ticket_generator.py` and `email_sender.py` if they exist in the same directory. Copy them from [bharadwaj-13/Email_Sender](https://github.com/bharadwaj-13/Email_Sender) into this repo.

## Adjusting scraper selectors

Unstop may change their page layout. If scraping breaks:
1. Run locally with `headless=False` in `scraper.py` to see the browser
2. Check `debug_*.png` screenshots saved on errors
3. Adjust CSS selectors in `scrape_event_registrations()`

## Notes

- GitHub Actions free tier: 2,000 minutes/month (plenty for hourly runs)
- The scraper handles pagination and infinite scroll
- `processed.json` prevents duplicate emails across runs
- Each event's registrants are tracked separately
