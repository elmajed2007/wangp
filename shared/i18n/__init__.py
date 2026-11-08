"""WanGP Arabic UI localisation layer (runtime, non-invasive).

* Python side: translates component props sent to the browser (labels, info, placeholders,
  choice labels, Markdown/HTML values) in the Blocks config and in every update dict, plus
  gr.Info / gr.Warning / gr.Error messages. Choice *values* are never changed, so app logic
  keeps working with the original English values.
* Browser side: an ASGI middleware injects i18n.js + rtl.css into every HTML page
  (main Gradio UI, Deepy, Showrunner, Media Flow...). The script translates remaining text
  nodes and attributes live (MutationObserver) and switches the page to RTL.

Disable with the environment variable WANGP_UI_LANG=en.
"""
from __future__ import annotations

import json
import os
import re
from functools import lru_cache, wraps
from pathlib import Path

HERE = Path(__file__).parent
LANG = (os.environ.get("WANGP_UI_LANG") or "ar").strip().lower()
ENABLED = LANG not in ("", "en", "off", "0", "none")
_DICT_PATH = HERE / f"{LANG}.json"
_STRINGS: dict[str, str] = {}
_TEMPLATES: list[tuple[re.Pattern, str, str]] = []
_WS = re.compile(r"\s+")


def _load():
    if not ENABLED or not _DICT_PATH.exists():
        return
    data = json.loads(_DICT_PATH.read_text(encoding="utf-8"))
    for k, v in data.get("strings", {}).items():
        if v and v != k:
            _STRINGS[_WS.sub(" ", k).strip()] = v
    tpls = []
    for k, v in data.get("templates", {}).items():
        if not v or v == k:
            continue
        parts = k.split("{}")
        rx = "^" + "(.+?)".join(re.escape(p) for p in parts) + "$"
        anchor = max(parts, key=len)
        tpls.append((re.compile(rx, re.S), v, anchor))
    tpls.sort(key=lambda t: -len(t[2]))
    _TEMPLATES.extend(tpls)


def _fill(tpl: str, args: tuple) -> str:
    if re.search(r"\{\d+\}", tpl):
        return re.sub(r"\{(\d+)\}", lambda m: args[int(m.group(1))] if int(m.group(1)) < len(args) else m.group(0), tpl)
    it = iter(args)
    return re.sub(r"\{\}", lambda m: next(it, ""), tpl)


@lru_cache(maxsize=65536)
def _tr_core(text: str) -> str | None:
    n = _WS.sub(" ", text).strip()
    if not n:
        return None
    hit = _STRINGS.get(n)
    if hit is not None:
        return hit
    stripped = n.strip(" -•·|")
    if stripped != n and stripped in _STRINGS:
        return n.replace(stripped, _STRINGS[stripped])
    if len(n) < 800:
        for rx, tpl, anchor in _TEMPLATES:
            if anchor and anchor not in n:
                continue
            m = rx.match(n)
            if m:
                return _fill(tpl, tuple(tr(g) for g in m.groups()))
    return None


def tr(text):
    """Translate a plain UI string (whitespace around it is preserved)."""
    if not ENABLED or not isinstance(text, str) or not text.strip():
        return text
    res = _tr_core(text)
    if res is None:
        return text
    lead = text[: len(text) - len(text.lstrip())]
    trail = text[len(text.rstrip()):]
    return lead + res + trail


_TAG = re.compile(r"(<[^>]+>)")
_ATTR = re.compile(r'''\b(title|placeholder|aria-label|alt|data-tooltip)=("[^"]*"|'[^']*')''')
_MD_SPLIT = re.compile(r"(\*\*|__|`[^`]*`|\[[^\]]*\]\([^)]*\))")
_MD_LINE = re.compile(r"^(\s*(?:#{1,6}\s+|[-*+]\s+|\d+\.\s+|>\s*)?)(.*)$")


def _tr_line(line: str) -> str:
    whole = tr(line)
    if whole is not line and whole != line:
        return whole
    m = _MD_LINE.match(line)
    prefix, body = m.group(1), m.group(2)
    if prefix:
        t = tr(body)
        if t != body:
            return prefix + t
    pieces = _MD_SPLIT.split(body)
    if len(pieces) > 1:
        out = []
        for p in pieces:
            if _MD_SPLIT.fullmatch(p or ""):
                if p.startswith("[") and "](" in p:
                    label, url = p[1:].split("](", 1)
                    out.append("[" + tr(label) + "](" + url)
                else:
                    out.append(p)
            else:
                out.append(tr(p))
        return prefix + "".join(out)
    return line


def tr_rich(text):
    """Translate Markdown / HTML content piece by piece, keeping markup intact."""
    if not ENABLED or not isinstance(text, str) or not text.strip():
        return text
    whole = tr(text)
    if whole != text:
        return whole
    if "<" in text and _TAG.search(text):
        out = []
        for chunk in _TAG.split(text):
            if chunk.startswith("<") and chunk.endswith(">"):
                out.append(_ATTR.sub(lambda m: f'{m.group(1)}={m.group(2)[0]}{tr(m.group(2)[1:-1])}{m.group(2)[0]}', chunk))
            else:
                out.append("\n".join(_tr_line(l) for l in chunk.split("\n")) if chunk.strip() else chunk)
        return "".join(out)
    return "\n".join(_tr_line(l) for l in text.split("\n"))


def _tr_choices(choices):
    if not isinstance(choices, (list, tuple)):
        return choices
    out = []
    for c in choices:
        if isinstance(c, (list, tuple)) and len(c) == 2:
            out.append([tr(c[0]) if isinstance(c[0], str) else c[0], c[1]])
        elif isinstance(c, str):
            out.append([tr(c), c])
        else:
            out.append(c)
    return out


_RICH_TYPES = {"markdown", "html"}
_PROP_KEYS = ("label", "info", "placeholder")


def translate_props(ctype: str, props: dict) -> dict:
    """Return a translated shallow copy of a component's props (never mutates shared objects)."""
    if not ENABLED or not isinstance(props, dict):
        return props
    p = dict(props)
    for k in _PROP_KEYS:
        if isinstance(p.get(k), str):
            p[k] = tr_rich(p[k]) if k == "info" else tr(p[k])
    if "choices" in p and ctype in ("dropdown", "radio", "checkboxgroup"):
        p["choices"] = _tr_choices(p["choices"])
    if ctype in _RICH_TYPES and isinstance(p.get("value"), str):
        p["value"] = tr_rich(p["value"])
    return p


def _patch_config():
    from gradio import blocks

    original = blocks.Blocks.get_config_file
    if getattr(original, "_wangp_i18n", False):
        return

    @wraps(original)
    def get_config_file(self):
        config = original(self)
        try:
            comps = config.get("components", [])
            for i, c in enumerate(comps):
                comps[i] = dict(c, props=translate_props(c.get("type", ""), c.get("props", {})))
            if isinstance(config.get("title"), str):
                config["title"] = tr(config["title"])
        except Exception as exc:  # never break the UI because of translation
            print(f"[i18n] config translation skipped: {exc}")
        return config

    get_config_file._wangp_i18n = True
    blocks.Blocks.get_config_file = get_config_file

    original_update = blocks.postprocess_update_dict

    @wraps(original_update)
    def postprocess_update_dict(block, update_dict, postprocess=True):
        result = original_update(block, update_dict, postprocess)
        try:
            ctype = block.get_block_name() if hasattr(block, "get_block_name") else ""
            translated = translate_props(ctype, {k: v for k, v in result.items() if k in _PROP_KEYS or k == "choices" or (k == "value" and ctype in _RICH_TYPES)})
            result.update(translated)
        except Exception:
            pass
        return result

    blocks.postprocess_update_dict = postprocess_update_dict


def _patch_messages():
    import gradio as gr
    from gradio import helpers, exceptions

    for name in ("Info", "Warning", "Success"):
        fn = getattr(gr, name, None)
        if fn is None or getattr(fn, "_wangp_i18n", False):
            continue

        def make(fn):
            @wraps(fn)
            def wrapper(message="", *args, **kwargs):
                return fn(tr_rich(message) if isinstance(message, str) else message, *args, **kwargs)
            wrapper._wangp_i18n = True
            return wrapper

        w = make(fn)
        setattr(gr, name, w)
        if hasattr(helpers, name):
            setattr(helpers, name, w)

    err = exceptions.Error
    if not getattr(err.__init__, "_wangp_i18n", False):
        orig_init = err.__init__

        @wraps(orig_init)
        def __init__(self, message="Error raised.", *args, **kwargs):
            orig_init(self, tr_rich(message) if isinstance(message, str) else message, *args, **kwargs)

        __init__._wangp_i18n = True
        err.__init__ = __init__


# ---------------------------------------------------------------- browser assets
_ASSET_ROUTE = "/wangp-i18n/"
_SKIP_PREFIXES = ("/apps/r/", "/apps/lib/", "/wangp-i18n/", "/gradio_api/", "/file=", "/assets/", "/static/")


def _asset(name: str) -> tuple[bytes, str] | None:
    if name == "i18n.js":
        return (HERE / "i18n.js").read_bytes(), "application/javascript; charset=utf-8"
    if name == "rtl.css":
        return (HERE / "rtl.css").read_bytes(), "text/css; charset=utf-8"
    if name == "dict.json":
        return _DICT_PATH.read_bytes(), "application/json; charset=utf-8"
    return None


def _snippet() -> bytes:
    v = str(int(max((HERE / f).stat().st_mtime for f in ("i18n.js", "rtl.css", f"{LANG}.json"))))
    return (f'<link rel="stylesheet" href="{_ASSET_ROUTE}rtl.css?v={v}">'
            f'<script>window.WANGP_I18N_LANG={json.dumps(LANG)};window.WANGP_I18N_URL="{_ASSET_ROUTE}dict.json?v={v}";</script>'
            f'<script src="{_ASSET_ROUTE}i18n.js?v={v}"></script>').encode()


class I18nMiddleware:
    """Serves the i18n assets and injects them into every HTML page."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        path = scope.get("path", "")
        root = scope.get("root_path", "") or ""
        rel = path[len(root):] if root and path.startswith(root) else path
        if rel.startswith(_ASSET_ROUTE):
            found = _asset(rel[len(_ASSET_ROUTE):])
            if not found:
                return await self.app(scope, receive, send)
            body, ctype = found
            await send({"type": "http.response.start", "status": 200, "headers": [
                (b"content-type", ctype.encode()), (b"content-length", str(len(body)).encode()), (b"cache-control", b"public, max-age=86400")]})
            return await send({"type": "http.response.body", "body": body})
        if rel.startswith(_SKIP_PREFIXES) or scope.get("method") not in ("GET", "HEAD"):
            return await self.app(scope, receive, send)

        state = {"html": False, "start": None, "chunks": []}

        async def wrapped_send(message):
            if message["type"] == "http.response.start":
                headers = dict((k.lower(), v) for k, v in message.get("headers", []))
                ctype = headers.get(b"content-type", b"")
                enc = headers.get(b"content-encoding", b"")
                if ctype.startswith(b"text/html") and not enc:
                    state["html"], state["start"] = True, message
                    return
                return await send(message)
            if message["type"] == "http.response.body" and state["html"]:
                state["chunks"].append(message.get("body", b""))
                if message.get("more_body"):
                    return
                body = b"".join(state["chunks"])
                low = body[:4096].lower()
                idx = low.find(b"<head>")
                snip = _snippet()
                if idx >= 0:
                    body = body[: idx + 6] + snip + body[idx + 6:]
                elif b"<html" in low:
                    body = snip + body
                start = state["start"]
                start["headers"] = [(k, v) for k, v in start.get("headers", []) if k.lower() != b"content-length"] + [
                    (b"content-length", str(len(body)).encode())]
                await send(start)
                return await send({"type": "http.response.body", "body": body})
            return await send(message)

        return await self.app(scope, receive, wrapped_send)


def _patch_app():
    from gradio import routes

    original_create_app = routes.App.create_app
    if getattr(original_create_app, "_wangp_i18n", False):
        return

    @wraps(original_create_app)
    def create_app(*args, **kwargs):
        app = original_create_app(*args, **kwargs)
        try:
            app.add_middleware(I18nMiddleware)
        except Exception as exc:
            print(f"[i18n] middleware not installed: {exc}")
        return app

    create_app._wangp_i18n = True
    routes.App.create_app = staticmethod(create_app)


_installed = False


def install():
    global _installed
    if _installed or not ENABLED:
        return
    _installed = True
    _load()
    _patch_config()
    _patch_messages()
    _patch_app()
    print(f"[i18n] UI language: {LANG} ({len(_STRINGS)} strings, {len(_TEMPLATES)} templates)")
