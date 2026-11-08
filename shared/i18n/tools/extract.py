"""Extract UI-facing English strings from WanGP sources.
Usage: python3 -I extract.py <repo_root> <out.json>
"""
import ast, json, os, re, sys
from html.parser import HTMLParser

ROOT, OUT = sys.argv[1], sys.argv[2]
SKIP_DIRS = {"vendor", "third_party_licenses", "node_modules", "__pycache__", ".git", "templates", "lib"}
PY_DIRS = ["wgp.py", "shared", "plugins", "postprocessing", "models", "preprocessing", "installation"]
UI_KW = {"label", "info", "placeholder", "title", "description", "tooltip", "header", "button_text", "message", "hint", "help", "caption", "text", "submit_btn", "stop_btn", "show_label_text", "empty_text"}
VALUE_CALLEES = {"Markdown", "HTML", "Button", "DownloadButton", "UploadButton", "Label", "ClearButton"}
POS_CALLEES = VALUE_CALLEES | {"Tab", "TabItem", "Accordion", "Info", "Warning", "Error", "Group"}
DICT_KEYS = UI_KW | {"tip", "subtitle", "summary", "button", "status", "heading"}

strings = {}   # text -> set(sources)
templates = {} # template with {} -> sources

def looks_ui(s):
    t = s.strip()
    if len(t) < 2 or len(t) > 600: return False
    if not re.search(r"[A-Za-z]{2,}", t): return False
    if re.fullmatch(r"[\w.\-/\\:]+", t) and not re.fullmatch(r"[A-Z][a-z]+(?:[ -][A-Za-z]+)*:?", t):
        # identifiers/paths; keep simple capitalized words like 'Settings'
        if not re.fullmatch(r"[A-Z][a-zA-Z]+", t): return False
    if re.search(r"(^|\s)(def |import |return |function |const |let |var |=>|\(\)\s*\{)", t): return False
    if t.startswith(("#component", ".", "/", "http", "--", "{", "[", "<!--", "data:")): return False
    if re.search(r"[{};]\s*$", t) and "<" not in t: return False
    return True

class TextSeg(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.segs = []; self.skip = 0
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"): self.skip += 1
        for k, v in attrs:
            if k in ("title", "placeholder", "aria-label", "alt", "data-tooltip") and v: self.segs.append(v)
    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip: self.skip -= 1
    def handle_data(self, d):
        if not self.skip: self.segs.append(d)

MD = re.compile(r"\*\*|__|`|^#{1,6}\s*|^\s*[-*]\s+|\[([^\]]*)\]\([^)]*\)", re.M)

def segments(s):
    out = []
    if "<" in s and re.search(r"</?[a-zA-Z][^>]*>", s):
        p = TextSeg()
        try: p.feed(s)
        except Exception: pass
        out.extend(p.segs)
    else:
        out.append(s)
    res = []
    for seg in out:
        # whole string plus markdown-split pieces and lines
        res.append(seg)
        for line in seg.split("\n"):
            res.append(line)
            res.extend(re.split(r"\*\*|`|__", line))
            res.append(MD.sub(lambda m: m.group(1) or "", line))
    return res

def norm(s):
    return re.sub(r"\s+", " ", s).strip()

def add(s, src):
    for seg in segments(s):
        n = norm(seg)
        n = n.strip(" -•·|")
        if looks_ui(n): strings.setdefault(n, set()).add(src)

def add_tpl(node, src):
    parts = []
    for v in node.values:
        if isinstance(v, ast.Constant) and isinstance(v.value, str): parts.append(v.value.replace("{", "{{").replace("}", "}}"))
        else: parts.append("{}")
    t = "".join(parts)
    lit = re.sub(r"\{\}", "", t)
    if not re.search(r"[A-Za-z]{3,}", lit): return
    for seg in segments(t):
        n = norm(seg).strip(" -•·|")
        if "{}" in n and re.search(r"[A-Za-z]{3,}", n.replace("{}", "")) and looks_ui(n.replace("{}", "X")):
            templates.setdefault(n, set()).add(src)
        elif looks_ui(n) and "{}" not in n:
            strings.setdefault(n.replace("{{", "{").replace("}}", "}"), set()).add(src)

def take(node, src):
    if isinstance(node, ast.Constant) and isinstance(node.value, str): add(node.value, src)
    elif isinstance(node, ast.JoinedStr): add_tpl(node, src)
    elif isinstance(node, (ast.List, ast.Tuple)):
        for e in node.elts:
            if isinstance(e, ast.Tuple) and e.elts: take(e.elts[0], src)
            else: take(e, src)
    elif isinstance(node, ast.IfExp): take(node.body, src); take(node.orelse, src)
    elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add): take(node.left, src); take(node.right, src)
    elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("_", "t", "tr"):
        for a in node.args: take(a, src)

def callee(n):
    f = n.func
    return f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else "")

def scan_py(path):
    rel = os.path.relpath(path, ROOT)
    try: tree = ast.parse(open(path, encoding="utf-8").read())
    except Exception: return
    big_html = rel.startswith(("shared/gradio", "plugins", "wgp.py", "postprocessing", "shared/deepy/ui", "shared/deepy/gradio", "shared/notifications", "shared/utils/setting", "models/") ) and not rel.startswith(("models/", )) or rel.endswith(("_handler.py", "ui.py", "gradio_ui.py"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = callee(node)
            for kw in node.keywords:
                if kw.arg in UI_KW or kw.arg == "choices" or (kw.arg == "value" and name in VALUE_CALLEES):
                    take(kw.value, rel)
            if name in POS_CALLEES and node.args: take(node.args[0], rel)
            if name in ("update",) and node.args: pass
        elif isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and k.value in DICT_KEYS: take(v, rel)
        elif isinstance(node, (ast.List, ast.Tuple)):
            elts = node.elts
            if len(elts) >= 2 and all(isinstance(e, ast.Tuple) and len(e.elts) == 2 and isinstance(e.elts[0], (ast.Constant, ast.JoinedStr)) for e in elts):
                if all(isinstance(e.elts[0], ast.JoinedStr) or isinstance(e.elts[0].value, str) for e in elts):
                    for e in elts: take(e.elts[0], rel)
        elif isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and re.search(r"(label|title|html|markdown|md|msg|message|help|info|text|tooltip|caption|choices|desc)", t.id, re.I) for t in node.targets):
            take(node.value, rel)
        # html chunks anywhere in UI files
        if big_html and isinstance(node, ast.Constant) and isinstance(node.value, str) and re.search(r"<(div|span|button|p|b|li|h\d|label|summary|td|th|a|strong|small|option)\b", node.value):
            add(node.value, rel)
        if big_html and isinstance(node, ast.JoinedStr):
            lits = "".join(v.value for v in node.values if isinstance(v, ast.Constant))
            if re.search(r"<(div|span|button|p|b|li|h\d|label|summary|td|th|a|strong|small|option)\b", lits): add_tpl(node, rel)
        # strings returned by UI helper functions (dynamic labels) and dict.get defaults
        if big_html and isinstance(node, ast.Return) and node.value is not None:
            take(node.value, rel)
        if big_html and isinstance(node, ast.Call) and callee(node) == "get" and len(node.args) == 2:
            take(node.args[1], rel)
        if big_html and isinstance(node, ast.Assign) and isinstance(node.value, (ast.JoinedStr, ast.IfExp)):
            take(node.value, rel)
        if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call) and callee(node.exc) in ("Error", "gr.Error") and node.exc.args:
            take(node.exc.args[0], rel)

JS_STR = re.compile(r"""(?<![\w$])(?:'((?:[^'\\\n]|\\.)*)'|"((?:[^"\\\n]|\\.)*)"|`((?:[^`\\]|\\.)*)`)""", re.S)

def scan_js(path):
    rel = os.path.relpath(path, ROOT)
    src = open(path, encoding="utf-8", errors="ignore").read()
    if len(src) > 600000 or ".min." in path: return
    for m in JS_STR.finditer(src):
        s = m.group(1) or m.group(2) or m.group(3) or ""
        if m.group(3) is not None:
            s = re.sub(r"\$\{[^}]*\}", "{}", s)
        s = s.replace("\\n", "\n").replace("\\'", "'").replace('\\"', '"')
        if "<" in s:
            for seg in segments(s):
                n = norm(seg).strip(" -•·|")
                if "{}" in n:
                    if re.search(r"[A-Za-z]{3,}.*\s", n.replace("{}", "")) and looks_ui(n.replace("{}", "X")): templates.setdefault(n, set()).add(rel)
                elif looks_ui(n) and (" " in n or re.fullmatch(r"[A-Z][a-z]+", n)): strings.setdefault(n, set()).add(rel)
        else:
            n = norm(s)
            if "{}" in n:
                if re.search(r"[A-Z][a-z]+", n) and " " in n and looks_ui(n.replace("{}", "X")): templates.setdefault(n, set()).add(rel)
            elif looks_ui(n) and re.match(r"[A-Z0-9]", n) and (" " in n or re.fullmatch(r"[A-Z][a-z]{2,}", n)) and not re.search(r"[#$@]|\w\.\w", n):
                strings.setdefault(n, set()).add(rel)

def scan_html(path):
    rel = os.path.relpath(path, ROOT)
    add(open(path, encoding="utf-8", errors="ignore").read(), rel)

for top in PY_DIRS:
    p = os.path.join(ROOT, top)
    if os.path.isfile(p): scan_py(p); continue
    for dp, dns, fns in os.walk(p):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        for fn in fns:
            fp = os.path.join(dp, fn)
            if fn.endswith(".py"): scan_py(fp)
            elif fn.endswith(".js") and top in ("shared", "plugins", "models", "postprocessing"): scan_js(fp)
            elif fn.endswith(".html") and top in ("shared", "plugins"): scan_html(fp)

# model display names/descriptions
for fn in sorted(os.listdir(os.path.join(ROOT, "defaults"))):
    if fn.endswith(".json"):
        try: m = json.load(open(os.path.join(ROOT, "defaults", fn)))["model"]
        except Exception: continue
        if isinstance(m.get("description"), str): add(m["description"], "defaults/" + fn)

json.dump({"strings": {k: sorted(v) for k, v in sorted(strings.items())},
           "templates": {k: sorted(v) for k, v in sorted(templates.items())}}, open(OUT, "w"), ensure_ascii=False, indent=0)
print(len(strings), "strings,", len(templates), "templates")
