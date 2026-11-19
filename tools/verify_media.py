#!/usr/bin/env python3
"""Verify the integrity of original PNG, MP4, and source-archive assets."""
from pathlib import Path
import csv,hashlib,sys
root=Path(__file__).resolve().parents[1]
with (root/'MANIFEST.csv').open(newline='') as f: rows=list(csv.DictReader(f))
fail=[]
for r in rows:
 p=root/r['path']
 if not p.is_file(): fail.append('missing: '+r['path']);continue
 digest=hashlib.sha256(p.read_bytes()).hexdigest()
 if digest!=r['sha256']:fail.append('hash mismatch: '+r['path'])
print(f'Checked {len(rows)} original artifacts; failures: {len(fail)}')
for s in fail:print(s,file=sys.stderr)
sys.exit(bool(fail))
