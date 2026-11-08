"""python3 -I validate.py chunks/cXX.json out/cXX.ar.json  -> prints problems, exit 1 if any."""
import json, re, sys
src = json.load(open(sys.argv[1])); out = json.load(open(sys.argv[2]))
probs = []
missing = [k for k in src if k not in out]
extra = [k for k in out if k not in src]
for k in src:
    if k not in out: continue
    v = out[k]
    if not isinstance(v, str) or not v.strip(): probs.append(("empty", k)); continue
    n = len(re.findall(r"\{\}", k))
    plain = len(re.findall(r"\{\}", v)); idx = re.findall(r"\{(\d+)\}", v)
    if n and not ((plain == n and not idx) or (not plain and sorted(map(int, idx)) == list(range(n)))):
        probs.append(("placeholders", k))
    if not n and ("{}" in v or idx): probs.append(("stray placeholder", k))
print(f"{len(src)} keys, missing={len(missing)}, extra={len(extra)}, problems={len(probs)}")
for m in missing[:20]: print("MISSING:", m[:100])
for p in probs[:20]: print(p[0].upper() + ":", p[1][:100])
sys.exit(1 if missing or probs else 0)
