"""
scraper.py — ASCENT Registration Scraper
Logs into Unstop, scrapes registrations from all events,
detects new registrants, and triggers the email pipeline.

Usage:
    python scraper.py              # scrape + send emails
    python scraper.py --dry-run    # scrape only, no emails
"""

import json
import os
import sys
import time
from datetime import datetime
from playwright.sync_api import sync_playwright
from events import EVENTS

# ── CONFIG ────────────────────────────────────────────────────
UNSTOP_EMAIL    = os.environ.get("UNSTOP_EMAIL", "")
UNSTOP_PASSWORD = os.environ.get("UNSTOP_PASSWORD", "")
PROCESSED_FILE  = "processed.json"  # tracks who we've already emailed
OUTPUT_CSV      = "new_registrants.csv"

BASE_URL = "https://unstop.com/manage/opportunity/{event_id}/profiles/all-registrations"
LOGIN_URL = "https://unstop.com/"


def load_processed() -> dict:
    """Load the set of already-processed registrant emails per event."""
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE, "r") as f:
            return json.load(f)
    return {}


def save_processed(data: dict):
    """Save processed registrants back to file."""
    with open(PROCESSED_FILE, "w") as f:
        json.dump(data, f, indent=2)


def login(page):
    """Log into Unstop."""
    print("🔐 Logging into Unstop...")
    page.goto(LOGIN_URL, wait_until="networkidle", timeout=30000)
    
    # Click login/signup button (may vary — adjust selector if needed)
    try:
        # Try clicking the login button on the homepage
        login_btn = page.locator("text=Login").first
        if login_btn.is_visible(timeout=5000):
            login_btn.click()
            page.wait_for_timeout(2000)
    except:
        pass
    
    # Look for the email/login form
    # Unstop might use Google OAuth or email/password
    # Adjust these selectors based on actual login flow
    try:
        # Try email/password login
        email_input = page.locator('input[type="email"], input[placeholder*="email" i], input[name="email"]').first
        email_input.fill(UNSTOP_EMAIL)
        
        password_input = page.locator('input[type="password"]').first
        password_input.fill(UNSTOP_PASSWORD)
        
        submit_btn = page.locator('button[type="submit"], button:has-text("Login"), button:has-text("Sign In")').first
        submit_btn.click()
        
        page.wait_for_timeout(5000)
        print("✅ Logged in!")
    except Exception as e:
        print(f"⚠️  Login form not found with standard selectors.")
        print(f"   Error: {e}")
        print(f"   You may need to adjust selectors in scraper.py login()")
        print(f"   Current URL: {page.url}")
        # Take screenshot for debugging
        page.screenshot(path="debug_login.png")
        raise


def scrape_event_registrations(page, event: dict) -> list:
    """
    Navigate to an event's registrations page and scrape all entries.
    Returns list of dicts: [{name, email, team_name, college, status}, ...]
    """
    event_id = event["id"]
    event_name = event["name"]
    url = BASE_URL.format(event_id=event_id)
    
    print(f"\n📋 Scraping: {event_name} (ID: {event_id})")
    page.goto(url, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(3000)  # let dynamic content load
    
    registrants = []
    
    # Check if there are registrations
    try:
        # Look for the count indicator like "All (4)"
        count_text = page.locator("text=/All \\(\\d+\\)/").first.text_content(timeout=5000)
        total = int(count_text.split("(")[1].split(")")[0])
        print(f"   Found {total} registration(s)")
        
        if total == 0:
            return []
    except:
        print("   Could not determine registration count, attempting to scrape anyway...")
    
    # Scrape registration rows
    # Based on the screenshot, each row contains:
    # - Team/participant name
    # - Leader name  
    # - Email
    # - College
    # - Status
    
    # The registrations are in a list/table structure
    # Each entry seems to be in a card-like row with avatar, details, status
    
    # Strategy: get all visible rows, then handle pagination if needed
    page_num = 0
    while True:
        page_num += 1
        
        # Find all registration row elements
        # These selectors may need adjustment based on actual DOM
        rows = page.locator('[class*="registration"], [class*="participant"], tr, [class*="profile-card"], [class*="team-row"]').all()
        
        if not rows and page_num == 1:
            # Try a more generic approach: find all email-like text on page
            print("   Using fallback email extraction...")
            content = page.content()
            import re
            emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.]+', content)
            # Filter out Unstop's own emails
            emails = [e for e in emails if 'unstop.com' not in e and 'emails.unstop' not in e]
            emails = list(set(emails))  # deduplicate
            
            for email in emails:
                registrants.append({
                    "email": email,
                    "name": email.split("@")[0].replace(".", " ").title(),
                    "team_name": "",
                    "college": "",
                    "event_id": event_id,
                    "event_name": event_name,
                })
            break
        
        # Try to extract structured data from each row
        # Look for email patterns within each row
        for row in rows:
            try:
                text = row.text_content()
                import re
                email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', text)
                if email_match and 'unstop.com' not in email_match.group():
                    email = email_match.group()
                    
                    # Try to extract name (usually appears before email)
                    lines = [l.strip() for l in text.split('\n') if l.strip()]
                    name = ""
                    team_name = ""
                    college = ""
                    
                    for i, line in enumerate(lines):
                        if '@' in line:
                            # The line before email is usually the name
                            if i > 0:
                                name = lines[i-1]
                            # The line after email is usually college
                            if i + 1 < len(lines):
                                college = lines[i+1]
                            # Team name might be 2 lines before email
                            if i > 1:
                                team_name = lines[i-2]
                            break
                    
                    if not name:
                        name = email.split("@")[0].replace(".", " ").title()
                    
                    registrants.append({
                        "email": email.lower().strip(),
                        "name": name,
                        "team_name": team_name,
                        "college": college,
                        "event_id": event_id,
                        "event_name": event_name,
                    })
            except:
                continue
        
        # Check for pagination / "Load More" / next page
        try:
            next_btn = page.locator('button:has-text("Next"), [class*="next"], [aria-label="Next"]').first
            if next_btn.is_visible(timeout=2000):
                next_btn.click()
                page.wait_for_timeout(2000)
                continue
        except:
            pass
        
        # Check for infinite scroll
        prev_count = len(registrants)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(2000)
        # If no new entries appeared after scroll, we're done
        new_rows = page.locator('[class*="registration"], [class*="participant"]').all()
        if len(new_rows) <= len(rows):
            break
    
    # Deduplicate by email
    seen = set()
    unique = []
    for r in registrants:
        if r["email"] not in seen:
            seen.add(r["email"])
            unique.append(r)
    
    print(f"   ✅ Scraped {len(unique)} unique registrant(s)")
    return unique


def find_new_registrants(all_registrants: list, processed: dict) -> list:
    """Compare scraped data with processed records to find new entries."""
    new = []
    for r in all_registrants:
        event_id = r["event_id"]
        email = r["email"]
        
        if event_id not in processed:
            processed[event_id] = []
        
        if email not in processed[event_id]:
            new.append(r)
            processed[event_id].append(email)
    
    return new


def save_new_to_csv(new_registrants: list):
    """Save new registrants to a CSV for the email sender pipeline."""
    import csv
    
    file_exists = os.path.exists(OUTPUT_CSV)
    
    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "timestamp", "name", "email", "team_name", 
            "college", "event_id", "event_name"
        ])
        if not file_exists:
            writer.writeheader()
        
        for r in new_registrants:
            r["timestamp"] = datetime.now().isoformat()
            writer.writerow(r)


def main():
    dry_run = "--dry-run" in sys.argv
    
    if not UNSTOP_EMAIL or not UNSTOP_PASSWORD:
        print("❌ Set UNSTOP_EMAIL and UNSTOP_PASSWORD environment variables!")
        print("   export UNSTOP_EMAIL='your@email.com'")
        print("   export UNSTOP_PASSWORD='your_password'")
        sys.exit(1)
    
    if not EVENTS:
        print("❌ No events configured! Edit events.py")
        sys.exit(1)
    
    processed = load_processed()
    all_new = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = context.new_page()
        
        # Login once
        login(page)
        
        # Scrape each event
        for event in EVENTS:
            try:
                registrants = scrape_event_registrations(page, event)
                new = find_new_registrants(registrants, processed)
                
                if new:
                    print(f"   🆕 {len(new)} NEW registrant(s)!")
                    all_new.extend(new)
                else:
                    print(f"   — No new registrants")
                    
            except Exception as e:
                print(f"   ❌ Error scraping {event['name']}: {e}")
                page.screenshot(path=f"debug_{event['id']}.png")
                continue
        
        browser.close()
    
    # Save processed state
    save_processed(processed)
    
    if not all_new:
        print(f"\n✅ Done! No new registrations across {len(EVENTS)} event(s).")
        return
    
    # Save new registrants to CSV
    save_new_to_csv(all_new)
    print(f"\n📄 Saved {len(all_new)} new registrant(s) to {OUTPUT_CSV}")
    
    if dry_run:
        print("🏃 Dry run — skipping email sending.")
        print("\nNew registrants:")
        for r in all_new:
            print(f"  • {r['name']} ({r['email']}) — {r['event_name']}")
        return
    
    # Trigger email pipeline for each new registrant
    print(f"\n📧 Sending emails to {len(all_new)} new registrant(s)...")
    
    try:
        from ticket_generator import generate_ticket_image
        from email_sender import send_registration_email
        from share_generator import generate_share_page

        for r in all_new:
            registrant = {
                "name": r["name"],
                "email": r["email"],
                "registration_id": f"REG-{r['event_id']}-{r['email'].split('@')[0][:8]}",
                "event_name": r["event_name"],
                "date_time": "17:05:2026 :: 10:00",
            }

            try:
                ticket_path = generate_ticket_image(registrant)
                share_url = generate_share_page(registrant)
                send_registration_email(registrant, ticket_path, share_url)
                print(f"  ✅ {r['name']} ({r['email']}) — {r['event_name']}")
                time.sleep(1.5)  # rate limit
            except Exception as e:
                print(f"  ❌ Failed: {r['email']} — {e}")

    except ImportError:
        print("⚠️  ticket_generator, email_sender, or share_generator not found.")
        print("   New registrants saved to CSV. Process manually or integrate your pipeline.")
    
    print(f"\n✅ Done! Processed {len(all_new)} new registrant(s) across {len(EVENTS)} event(s).")


if __name__ == "__main__":
    main()
