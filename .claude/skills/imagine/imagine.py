#!/usr/bin/env python3
"""Generates one image through the OpenRouter Image API and saves it.

Usage:
  imagine.py [--size 1024x1024|1536x1024|1024x1536] [--quality low|medium|high]
             [--model <openrouter image model>] [--out <path.png>]  < prompt.txt

The prompt comes from stdin, so it is never part of the program text.
The key comes from OPENROUTER_API_KEY and is never printed.
"""
import argparse
import base64
import datetime
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = "https://openrouter.ai/api/v1/images"


def main() -> int:
    p = argparse.ArgumentParser(description="Generate an image through OpenRouter")
    p.add_argument("--size", default="1024x1024", choices=["1024x1024", "1536x1024", "1024x1536"])
    p.add_argument("--quality", default="medium", choices=["low", "medium", "high"])
    p.add_argument("--model", default="google/gemini-3.1-flash-image")
    p.add_argument("--out")
    a = p.parse_args()

    prompt = sys.stdin.read().strip()
    if not prompt:
        print("ERROR: no prompt on stdin", file=sys.stderr)
        return 2
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        print("ERROR: OPENROUTER_API_KEY is not set", file=sys.stderr)
        return 2

    if a.out:
        out = Path(a.out).expanduser()
    else:
        slug = re.sub(r"[^a-z0-9]+", "-", prompt.lower())[:50].strip("-") or "image"
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        out = Path.home() / "Downloads" / f"{slug}-{stamp}.png"
    out.parent.mkdir(parents=True, exist_ok=True)

    req_body = {"model": a.model, "prompt": prompt, "output_format": "png", "n": 1}
    if a.model.startswith("openai/"):
        # gpt-image models take exact pixel sizes and a quality level.
        req_body.update(size=a.size, quality=a.quality)
    else:
        # Other providers reject pixel sizes, so send the same shape as an aspect ratio.
        req_body["aspect_ratio"] = {"1024x1024": "1:1", "1536x1024": "3:2", "1024x1536": "2:3"}[a.size]
    body = json.dumps(req_body).encode()
    req = urllib.request.Request(API, data=body, headers={"Authorization": f"Bearer {key}",
                                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        print(f"ERROR {e.code}: {e.read().decode()[:500]}", file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(f"ERROR: {e.reason}", file=sys.stderr)
        return 1

    items = data.get("data") or []
    if not items or "b64_json" not in items[0]:
        print(f"ERROR: no image in the response: {json.dumps(data)[:500]}", file=sys.stderr)
        return 1
    out.write_bytes(base64.b64decode(items[0]["b64_json"]))

    print(f"✅ Saved: {out}")
    cost = (data.get("usage") or {}).get("cost")
    if cost is not None:
        print(f"💲 Cost: ${cost}")
    if items[0].get("revised_prompt"):
        print(f"📝 Revised prompt: {items[0]['revised_prompt']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
