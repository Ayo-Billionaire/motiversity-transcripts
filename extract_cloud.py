#!/usr/bin/env python3
"""Cloud version of the Motivation Daily transcriber (GitHub Actions, faster-whisper on CPU).
Usage: extract_cloud.py START END [model]   (episode index range, END exclusive). Skips episodes that already have a .txt."""
import json, re, sys, time, urllib.request, html, tempfile
from pathlib import Path
import xml.etree.ElementTree as ET

FEED = "https://feeds.acast.com/public/shows/6114541c545d640012cfb625"
OUT = Path(__file__).parent / "transcripts"
UA = {"User-Agent": "Mozilla/5.0"}
ns = {"itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd"}

def episodes():
    root = ET.fromstring(urllib.request.urlopen(urllib.request.Request(FEED, headers=UA), timeout=60).read())
    eps = []
    for n, it in enumerate(root.iter("item")):
        enc = it.find("enclosure")
        if enc is None:
            continue
        title = html.unescape(it.findtext("title", "")).strip()
        eps.append({"n": n, "title": title, "date": it.findtext("pubDate", ""), "dur": it.findtext("itunes:duration", "", ns),
                    "url": enc.get("url"), "slug": f"{n:03d}-" + re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:70]})
    return eps

if __name__ == "__main__":
    start, end = int(sys.argv[1]), int(sys.argv[2])
    model_name = sys.argv[3] if len(sys.argv) > 3 else "small.en"
    OUT.mkdir(exist_ok=True)
    eps = episodes()
    if start == -1:  # plan mode: print episode count
        print(len(eps)); sys.exit(0)
    from faster_whisper import WhisperModel
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    for e in eps[start:end]:
        txt = OUT / f"{e['slug']}.txt"
        if txt.exists() and txt.stat().st_size > 0:
            continue
        t0 = time.time()
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3") as f:
                f.write(urllib.request.urlopen(urllib.request.Request(e["url"], headers=UA), timeout=180).read()); f.flush()
                segs, info = model.transcribe(f.name, language="en", beam_size=1, vad_filter=True, word_timestamps=True)
                rows = [{"start": s.start, "end": s.end, "text": s.text.strip(),
                         "words": [{"w": w.word, "s": w.start, "e": w.end} for w in (s.words or [])]} for s in segs]
            (OUT / f"{e['slug']}.json").write_text(json.dumps({"title": e["title"], "date": e["date"], "segments": rows}))
            txt.write_text(e["title"] + "\n\n" + " ".join(r["text"] for r in rows) + "\n")
            print(f"OK  {e['slug']}  {time.time()-t0:.0f}s  (audio {info.duration/60:.1f} min)", flush=True)
        except Exception as ex:
            print(f"FAIL {e['slug']}  {ex}", flush=True)
