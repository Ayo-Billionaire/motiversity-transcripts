#!/usr/bin/env python3
"""Email Ayo when a transcribe run ends: count transcripts against the feed, list gaps. Usage: notify.py [--dry]"""
import json, os, sys, urllib.request
from pathlib import Path
from extract_cloud import episodes

eps = episodes()
have = {p.stem for p in (Path(__file__).parent / "transcripts").glob("*.txt") if p.stat().st_size > 0}
missing = [e["slug"] for e in eps if e["slug"] not in have]
done = len(eps) - len(missing)
conclusion = os.environ.get("CONCLUSION", "unknown")
run_url = os.environ.get("RUN_URL", "")
if not missing:
    subject = f"Goal Billionaire transcripts: all {len(eps)} done"
    lead = f"All {len(eps)} episodes are transcribed and saved in the repo."
else:
    subject = f"Goal Billionaire transcripts: {done} of {len(eps)} done, {len(missing)} missing"
    lead = f"{done} of {len(eps)} episodes are saved. {len(missing)} are missing (run result: {conclusion}). Rerun the transcribe workflow to fill the gaps; it skips finished episodes."
body = lead + f"\n\nRun: {run_url}\nRepo: https://github.com/Ayo-Billionaire/goal-billionaire-transcripts\n"
if missing:
    body += "\nMissing:\n" + "\n".join(missing[:60]) + ("\n..." if len(missing) > 60 else "") + "\n"
print(subject, "\n", body)
if "--dry" in sys.argv:
    sys.exit(0)
req = urllib.request.Request("https://api.resend.com/emails", method="POST", data=json.dumps({
    "from": "Transcripts <transcripts@send.noqodepro.com>", "to": ["adesinaokiki2003@gmail.com"],
    "subject": subject, "text": body}).encode(),
    headers={"Authorization": "Bearer " + os.environ["RESEND_API_KEY"], "Content-Type": "application/json", "User-Agent": "goal-billionaire-notify/1.0"})
print(urllib.request.urlopen(req, timeout=30).read().decode())
