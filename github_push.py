"""
github_push.py
Push files to a GitHub repo via the GitHub API (no local git needed).
Used by the deployed dashboard to push share pages to GitHub Pages.
"""

import base64
import os
import requests

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO = "Sauhard74/Email_Sender"
API_BASE = f"https://api.github.com/repos/{REPO}"
BRANCH = "main"


def _headers():
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }


def push_file(file_path: str, repo_path: str, commit_message: str = "Add file") -> bool:
    """
    Push a single file to the GitHub repo.
    file_path: local path to the file
    repo_path: path in the repo (e.g., "share/REG0001-sauhard-gupta.png")
    """
    if not GITHUB_TOKEN:
        print(f"  ⚠️ No GITHUB_TOKEN set — skipping push for {repo_path}")
        return False

    with open(file_path, "rb") as f:
        content = base64.b64encode(f.read()).decode("utf-8")

    # Check if file already exists (need its SHA to update)
    url = f"{API_BASE}/contents/{repo_path}"
    resp = requests.get(url, headers=_headers(), params={"ref": BRANCH})
    sha = resp.json().get("sha") if resp.status_code == 200 else None

    payload = {
        "message": commit_message,
        "content": content,
        "branch": BRANCH,
    }
    if sha:
        payload["sha"] = sha

    resp = requests.put(url, headers=_headers(), json=payload)
    if resp.status_code in (200, 201):
        return True
    else:
        print(f"  ❌ GitHub push failed for {repo_path}: {resp.status_code} {resp.text[:200]}")
        return False


def push_share_files(share_dir: str, filenames: list, event_name: str) -> str:
    """
    Push multiple share files to GitHub.
    Returns a status message.
    """
    if not GITHUB_TOKEN:
        return "No GITHUB_TOKEN configured — share pages generated locally but not pushed to GitHub Pages."

    success = 0
    failed = 0

    for filename in filenames:
        local_path = os.path.join(share_dir, filename)
        repo_path = f"share/{filename}"
        msg = f"Add share page: {filename} ({event_name})"

        if push_file(local_path, repo_path, msg):
            success += 1
        else:
            failed += 1

    if failed == 0:
        return f"Pushed {success} share files to GitHub Pages."
    else:
        return f"Pushed {success} files, {failed} failed. Check logs."
