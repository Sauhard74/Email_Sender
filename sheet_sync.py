"""
sheet_sync.py
Fetches existing data from Google Sheet, deduplicates, and pushes new rows.
Deduplication key: (email, event) — same person + same event = skip.
"""

import requests

SHEET_API = "https://script.google.com/macros/s/AKfycbydxlixisGuJUHvs_GJGc2SXJ5g6plYAO1dZkMx_NpDBU-6iQ4FQVJpKow-WWEEn7os/exec"


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
    Push a list of rows to the Google Sheet.
    Each row: {"name": ..., "event": ..., "email": ..., "utm": ...}
    Returns {"pushed": N, "skipped": N, "errors": N}
    """
    # Fetch existing data for deduplication
    existing = fetch_existing()
    existing_keys = get_existing_keys(existing)

    pushed = 0
    skipped = 0
    errors = 0

    for row in rows:
        email = row.get("email", "").strip().lower()
        event = row.get("event", "").strip().lower()
        key = (email, event)

        if key in existing_keys:
            skipped += 1
            continue

        try:
            resp = requests.post(SHEET_API, json=row, timeout=30)
            if resp.status_code == 200:
                pushed += 1
                existing_keys.add(key)  # prevent duplicates within same batch
            else:
                print(f"  ❌ Sheet push failed for {email}: {resp.status_code}")
                errors += 1
        except Exception as e:
            print(f"  ❌ Sheet push error for {email}: {e}")
            errors += 1

    return {"pushed": pushed, "skipped": skipped, "errors": errors}


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
