"""
sheet_sync.py
Fetches existing data from Google Sheet, deduplicates, and pushes new rows.
Deduplication key: (email, event) — same person + same event = skip.
"""

import requests

SHEET_API = "https://script.google.com/macros/s/AKfycbzeqpN1pdpNWLZBtG_5FV553AejEKzGeD2auulZtO_uZKoMfrHNMd7skLl5qL7a_CS6/exec"


def fetch_existing() -> list:
    """Fetch all existing rows from the Google Sheet."""
    try:
        resp = requests.get(SHEET_API, timeout=30)
        data = resp.json()
        if data.get("success"):
            return data.get("data", [])
    except Exception as e:
        print(f"  ⚠️ Failed to fetch sheet: {e}")
    return []


def get_existing_keys(existing: list) -> set:
    """Build a set of (email, event) keys from existing sheet data."""
    keys = set()
    for row in existing:
        email = row.get("email", "").strip().lower()
        event = row.get("event", "").strip().lower()
        if email and event:
            keys.add((email, event))
    return keys


def push_to_sheet(rows: list) -> dict:
    """
    Push rows to the Google Sheet as a single batch POST.
    Each row: {"name", "event", "email", "utm", "image", "mail"}
    API expects an array payload.
    Returns {"pushed": N, "skipped": N, "errors": N}
    """
    # Fetch existing data for deduplication
    existing = fetch_existing()
    existing_keys = get_existing_keys(existing)

    # Filter out duplicates
    new_rows = []
    skipped = 0
    for row in rows:
        email = row.get("email", "").strip().lower()
        event = row.get("event", "").strip().lower()
        key = (email, event)

        if key in existing_keys:
            skipped += 1
        else:
            new_rows.append(row)
            existing_keys.add(key)  # prevent dupes within same batch

    if not new_rows:
        return {"pushed": 0, "skipped": skipped, "errors": 0}

    # Push all new rows in one batch POST
    try:
        resp = requests.post(SHEET_API, json=new_rows, timeout=60)
        result = resp.json()
        if result.get("success"):
            pushed = result.get("inserted", len(new_rows))
            return {"pushed": pushed, "skipped": skipped, "errors": 0}
        else:
            print(f"  ❌ Sheet API error: {result}")
            return {"pushed": 0, "skipped": skipped, "errors": len(new_rows)}
    except Exception as e:
        print(f"  ❌ Sheet push error: {e}")
        return {"pushed": 0, "skipped": skipped, "errors": len(new_rows)}


def sync_results_to_sheet(results: list, event_name: str) -> str:
    """
    Take processed results from batch_processor and push to Google Sheet.
    Returns a status message.
    """
    rows = []
    for r in results:
        rows.append({
            "name": r["name"],
            "event": event_name,
            "email": r["email"],
            "utm": r["share_url"],
            "ticket": r["ticket_url"],
            "email_sent": "No",
        })

    stats = push_to_sheet(rows)
    parts = []
    if stats["pushed"]:
        parts.append(f"{stats['pushed']} added to sheet")
    if stats["skipped"]:
        parts.append(f"{stats['skipped']} duplicates skipped")
    if stats["errors"]:
        parts.append(f"{stats['errors']} errors")

    return " | ".join(parts) if parts else "No rows to push"
