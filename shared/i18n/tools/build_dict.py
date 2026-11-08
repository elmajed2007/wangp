"""Merge translated chunk files into shared/i18n/ar.json.
python3 -I build_dict.py <raw.json from extract.py> <dir with *.ar.json> <out ar.json> [existing ar.json to keep]"""
import json, sys, glob, os
raw = json.load(open(sys.argv[1]))
tpl_keys = set(raw["templates"])
merged = {}
if len(sys.argv) > 4 and os.path.exists(sys.argv[4]):
    old = json.load(open(sys.argv[4])); merged.update(old.get("strings", {})); merged.update(old.get("templates", {}))
for f in sorted(glob.glob(os.path.join(sys.argv[2], "*.ar.json"))):
    merged.update(json.load(open(f)))
out = {"strings": {}, "templates": {}}
for k, v in sorted(merged.items()):
    if not isinstance(v, str) or not v.strip() or v == k: continue
    (out["templates"] if (k in tpl_keys or "{}" in k) else out["strings"])[k] = v
json.dump(out, open(sys.argv[3], "w"), ensure_ascii=False, separators=(",", ":"))
print(len(out["strings"]), "strings", len(out["templates"]), "templates ->", sys.argv[3])
