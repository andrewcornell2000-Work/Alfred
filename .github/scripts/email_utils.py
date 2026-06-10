"""Shared Resend email helper for Alfred GitHub Actions workflows."""

import os
import requests

OWNER_EMAIL = "andrewcornell2000@gmail.com"
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")


def send_alfred_email(subject: str, body: str) -> bool:
    """Send a plain-text email to Andrew via Resend. Returns True if sent."""
    if not RESEND_API_KEY:
        print("[Email] RESEND_API_KEY not set in GitHub Secrets — skipping")
        return False
    try:
        payload = {
            "from": "Alfred <onboarding@resend.dev>",
            "to": [OWNER_EMAIL],
            "subject": subject,
            "text": body,
        }
        print(f"[Email] Sending to {OWNER_EMAIL}: {subject}")
        r = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=15,
        )
        print(f"[Email] Response: {r.status_code} — {r.text}")
        if r.ok:
            print(f"[Email] SUCCESS — sent to {OWNER_EMAIL}")
            return True
        print(f"[Email] FAILED: {r.status_code} {r.text}")
    except Exception as e:
        print(f"[Email] ERROR: {e}")
    return False
