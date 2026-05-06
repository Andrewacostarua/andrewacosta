"""Email notification via Gmail SMTP with App Password."""

import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

TO_ADDRESS = "andrew@acostarua.com"

TIER_COLORS = {
    "homerun": "#F59E0B",
    "reach":   "#8B5CF6",
    "target":  "#3B82F6",
    "safety":  "#10B981",
}


def _build_html(new_jobs: list[dict]) -> str:
    date_str = datetime.utcnow().strftime("%B %d, %Y")
    rows = ""
    for job in new_jobs:
        color = TIER_COLORS.get(job.get("tier", ""), "#6B7280")
        rows += f"""
        <tr>
          <td style="padding:10px;border-bottom:1px solid #E5E7EB;">
            <span style="background:{color};color:white;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;text-transform:uppercase;">{job.get('tier','')}</span>
          </td>
          <td style="padding:10px;border-bottom:1px solid #E5E7EB;font-weight:600;">{job.get('firm','')}</td>
          <td style="padding:10px;border-bottom:1px solid #E5E7EB;">{job.get('title','')}</td>
          <td style="padding:10px;border-bottom:1px solid #E5E7EB;">{job.get('location','')}</td>
          <td style="padding:10px;border-bottom:1px solid #E5E7EB;">
            <a href="{job.get('url','')}" style="color:#3B82F6;text-decoration:none;">Apply →</a>
          </td>
        </tr>"""

    return f"""
    <html><body style="font-family:Arial,sans-serif;max-width:800px;margin:0 auto;color:#111827;">
      <div style="background:#1E3A5F;padding:20px 24px;border-radius:8px 8px 0 0;">
        <h2 style="color:white;margin:0;">🔔 {len(new_jobs)} New Analyst Role(s) Found</h2>
        <p style="color:#93C5FD;margin:4px 0 0;">{date_str}</p>
      </div>
      <div style="border:1px solid #E5E7EB;border-top:none;border-radius:0 0 8px 8px;padding:20px;">
        <table style="width:100%;border-collapse:collapse;">
          <thead>
            <tr style="text-align:left;color:#6B7280;font-size:12px;text-transform:uppercase;">
              <th style="padding:8px 10px;">Tier</th>
              <th style="padding:8px 10px;">Firm</th>
              <th style="padding:8px 10px;">Role</th>
              <th style="padding:8px 10px;">Location</th>
              <th style="padding:8px 10px;">Link</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
        <p style="margin-top:20px;color:#6B7280;font-size:12px;">
          Sent by your analyst-job-tracker. View your full dashboard at your GitHub Pages URL.
        </p>
      </div>
    </body></html>"""


def send_alert(new_jobs: list[dict], dry_run: bool = False) -> None:
    if not new_jobs:
        return

    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    subject  = f"🔔 {len(new_jobs)} New Analyst Role(s) Found — {date_str}"

    plain = "\n".join(
        f"{j.get('tier','').upper()} | {j['firm']} | {j['title']} | {j.get('url','')}"
        for j in new_jobs
    )

    if dry_run:
        print(f"[notifier] DRY RUN — Subject: {subject}")
        print(f"[notifier] To: {TO_ADDRESS}")
        print("[notifier] Plain text body:")
        print(plain)
        return

    gmail_address  = os.environ.get("GMAIL_ADDRESS")
    gmail_password = os.environ.get("GMAIL_APP_PASSWORD")

    if not gmail_address or not gmail_password:
        print("[notifier] GMAIL_ADDRESS or GMAIL_APP_PASSWORD not set — skipping email")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = gmail_address
    msg["To"]      = TO_ADDRESS

    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(_build_html(new_jobs), "html"))

    if dry_run:
        print(f"[notifier] DRY RUN — would send: {subject}")
        print(plain)
        return

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_address, gmail_password)
        server.sendmail(gmail_address, TO_ADDRESS, msg.as_string())
    print(f"[notifier] Email sent to {TO_ADDRESS}: {subject}")


if __name__ == "__main__":
    # Test send — set GMAIL_ADDRESS and GMAIL_APP_PASSWORD env vars first
    test_jobs = [{
        "id":     "test-001",
        "firm":   "Blue Owl Capital",
        "tier":   "target",
        "track":  "repe",
        "title":  "Analyst, Real Estate",
        "url":    "https://example.com/apply",
        "location": "New York, NY",
    }]
    send_alert(test_jobs, dry_run=False)
