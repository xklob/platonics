#!/usr/bin/env python3
"""Reassemble original 4K/60fps single-form renders from binary Git chunks."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
specs=json.loads((ROOT/'media-parts/single-4k/manifest.json').read_text())['files']
for s in specs:
 dest=ROOT/s['path']
 data=b''.join((ROOT/part).read_bytes() for part in s['parts'])
 if len(data)!=s['size'] or hashlib.sha256(data).hexdigest()!=s['sha256']:
  raise SystemExit(f"Integrity check failed: {s['path']}")
 dest.parent.mkdir(parents=True,exist_ok=True)
 dest.write_bytes(data)
 print(f"Verified {dest.relative_to(ROOT)}, {len(data)} bytes")
