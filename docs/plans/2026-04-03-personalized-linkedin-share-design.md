# Personalized LinkedIn Share System — Design

## Problem
LinkedIn ignores the deprecated `shareArticle?summary=` parameter. We need a working share flow where each registrant gets a personalized LinkedIn preview card showing their ticket.

## Solution
Pre-generate a personalized poster PNG + static HTML page (with OG tags) per registrant. Host on GitHub Pages. LinkedIn crawler fetches the static HTML, reads `og:image`, displays the personalized ticket as the preview card.

## Flow
```
Scraper finds new registrant
  → Generate ticket PNG (existing)
  → Generate share poster PNG (same ticket template → 1200x630)
  → Generate static HTML with OG meta tags pointing to the PNG
  → Send email with personalized LinkedIn share URL
  → Commit share/ files + processed.json to repo
  → GitHub Pages serves share/ folder
```

## File Structure
```
Email_Sender/
├── share/                              ← GitHub Pages serves this
│   ├── REG20052-test-user.html
│   ├── REG20052-test-user.png
│   └── ...per registrant
├── share_generator.py                  ← NEW
├── scraper.py
├── email_sender.py
├── ticket_generator.py
└── .github/workflows/scrape.yml
```

## New: share_generator.py
- `generate_share_page(registrant)` reuses `templates/ticket.html` via Playwright
- Screenshots at 1200x630 (LinkedIn OG image recommended size)
- Saves PNG to `share/{reg_id}-{slugified_name}.png`
- Creates HTML at `share/{reg_id}-{slugified_name}.html` with hardcoded OG tags
- Returns the full GitHub Pages URL for use in the email

## Changes to Existing Files

### email_sender.py
- `build_linkedin_share_url(share_url)` accepts a per-registrant share page URL
- Share text includes the personal URL instead of a generic one
- `send_registration_email(registrant, ticket_image_path, share_url)` passes the URL through

### scraper.py
- Calls `generate_share_page()` between ticket generation and email sending
- Passes the returned share URL to the email sender

### .github/workflows/scrape.yml
- Also commits `share/` folder
- GitHub Pages enabled on the repo (sauhard74/Email_Sender)

## URLs
- GitHub Pages base: `https://sauhard74.github.io/Email_Sender/`
- Share page: `https://sauhard74.github.io/Email_Sender/share/REG20052-test-user.html`
- OG image: `https://sauhard74.github.io/Email_Sender/share/REG20052-test-user.png`
- LinkedIn share: `https://www.linkedin.com/feed/?shareActive=true&text={encoded_text}`
