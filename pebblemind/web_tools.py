"""Web access tools for PebbleMind: fetch pages and search the web.

Deliberately dependency-light: httpx only (already a core dep), no API keys.
Web access is opt-in — PebbleMind's core value is fully-offline privacy, so
these tools are only registered when the user enables them in config
(tools.web_access: true) or calls them directly.
"""

import asyncio
import ipaddress
import logging
import re
import socket
from html import unescape
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus, urlparse

import httpx

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 PebbleMind/0.1"
)

_BLOCK_TAGS = re.compile(
    r"<(script|style|noscript|nav|header|footer|aside|svg|form|iframe)[^>]*>.*?</\1>",
    re.IGNORECASE | re.DOTALL,
)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t]+")
_PARA_RE = re.compile(r"\n\s*\n\s*")


def is_valid_url(url: str) -> bool:
    """SSRF guard: http(s) only, hostname required, no private/unroutable hosts.

    IP literals (IPv4/IPv6, IPv4-mapped forms) are parsed with `ipaddress`
    and must be globally routable — this rejects loopback, RFC1918,
    link-local, CGNAT, and `::ffff:127.0.0.1`-style forms that prefix
    matching misses. Hostnames are additionally resolved and re-checked by
    `web_fetch` (a name that resolves only to internal addresses is refused).
    """
    try:
        p = urlparse(url)
        if p.scheme not in ("http", "https") or not p.netloc:
            return False
        host = (p.hostname or "").lower().rstrip(".")
        if not host:
            return False
        try:
            addr = ipaddress.ip_address(host)
        except ValueError:
            # Name, not a literal — trailing-dot and *.localhost tricks.
            return not (host == "localhost" or host.endswith(".localhost"))
        return addr.is_global
    except Exception:
        return False


def _host_resolves_global(host: str) -> bool:
    """True only if every resolved address for `host` is globally routable."""
    try:
        infos = socket.getaddrinfo(host, None)
        addrs = {ipaddress.ip_address(info[4][0]) for info in infos}
        return bool(addrs) and all(a.is_global for a in addrs)
    except Exception:
        return False


def _strip_html(html: str, max_chars: int = 20000) -> str:
    html = _BLOCK_TAGS.sub(" ", html)
    text = _TAG_RE.sub(" ", html)
    text = unescape(text)
    text = _WS_RE.sub(" ", text)
    text = _PARA_RE.sub("\n\n", text)
    return text.strip()[:max_chars]


async def web_fetch(url: str, timeout: float = 15.0, max_chars: int = 20000) -> Dict[str, Any]:
    """Fetch a URL and return cleaned text + metadata.

    Redirects are followed manually so every hop is re-validated — a public
    page that redirects to an internal address is refused. Hostnames are
    resolved and checked (best-effort; connection-level rebinding races are
    out of scope for a dependency-light client).
    """
    if not is_valid_url(url):
        raise ValueError(f"Invalid or unsafe URL: {url!r}")
    async with httpx.AsyncClient(follow_redirects=False, timeout=timeout, headers={"User-Agent": USER_AGENT}) as client:
        for _ in range(5):
            if not is_valid_url(url):
                raise ValueError(f"Redirect to unsafe URL: {url!r}")
            host = (urlparse(url).hostname or "").lower().rstrip(".")
            try:
                ipaddress.ip_address(host)
            except ValueError:  # name — resolve and re-check every address
                if not await asyncio.to_thread(_host_resolves_global, host):
                    raise ValueError(f"Unsafe URL (host resolves internally): {url!r}")
            r = await client.get(url)
            if r.is_redirect:
                url = str(r.url.join(r.headers.get("location", "")))
                continue
            break
        else:
            raise ValueError("Too many redirects")
        r.raise_for_status()
    ctype = r.headers.get("content-type", "")
    if "html" in ctype:
        title_match = re.search(r"<title[^>]*>(.*?)</title>", r.text, re.IGNORECASE | re.DOTALL)
        title = unescape(title_match.group(1)).strip() if title_match else ""
        text = _strip_html(r.text, max_chars)
    else:
        title, text = "", r.text[:max_chars]
    return {"url": str(r.url), "status": r.status_code, "title": title, "content": text, "content_type": ctype}


async def web_search(
    query: str,
    num_results: int = 5,
    timeout: float = 15.0,
) -> List[Dict[str, str]]:
    """Search the web via DuckDuckGo HTML (no API key required).

    Returns list of {"title", "url", "snippet"} dicts, best-effort.
    """
    if not query or not query.strip():
        raise ValueError("Empty query")
    num_results = max(1, min(int(num_results), 10))
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout, headers={"User-Agent": USER_AGENT}) as client:
        r = await client.get(url)
        r.raise_for_status()

    results: List[Dict[str, str]] = []
    for m in re.finditer(
        r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?class="result__snippet"[^>]*>(.*?)</a>',
        r.text,
        re.IGNORECASE | re.DOTALL,
    ):
        href, title, snippet = m.group(1), m.group(2), m.group(3)
        # DDG wraps URLs like //duckduckgo.com/l/?uddg=<encoded>&rut=...
        uddg = re.search(r"[?&]uddg=([^&]+)", href)
        if uddg:
            from urllib.parse import unquote

            href = unquote(uddg.group(1))
        clean = lambda s: _WS_RE.sub(" ", unescape(_TAG_RE.sub("", s))).strip()  # noqa: E731
        if href.startswith("http"):
            results.append({"title": clean(title), "url": href, "snippet": clean(snippet)})
        if len(results) >= num_results:
            break
    if not results:
        raise RuntimeError("No results parsed (search engine layout may have changed)")
    return results


async def register_web_tools(tool_manager, config: Optional[Any] = None) -> bool:
    """Register web tools on a ToolManager if enabled. Returns True if registered."""
    enabled = bool(getattr(config, "web_access", False)) if config is not None else False
    if not enabled:
        return False

    async def _web_search(query: str, num_results: int = 5) -> List[Dict[str, str]]:
        return await web_search(query, num_results)

    async def _web_fetch(url: str) -> Dict[str, Any]:
        return await web_fetch(url)

    tool_manager.register_tool("web_search", _web_search)
    tool_manager.register_tool("web_fetch", _web_fetch)
    return True
