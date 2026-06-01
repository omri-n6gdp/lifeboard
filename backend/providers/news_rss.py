"""News panel: fetch a set of RSS/Atom feeds server-side, merge, newest first.
One bad feed is skipped rather than sinking the panel."""
import time

import feedparser
import httpx

from backend.envelope import ok, run_provider

ID, TITLE = "feeds_news", "News"


def _ts(entry):
    for k in ("published_parsed", "updated_parsed"):
        if entry.get(k):
            return time.mktime(entry[k])
    return 0.0


def items_from_feed_text(text, source=""):
    parsed = feedparser.parse(text)
    src = source or (parsed.feed.get("title", "") if parsed.feed else "")
    items = [{
        "title": e.get("title", "(untitled)"),
        "link": e.get("link", ""),
        "source": src,
        "ts": _ts(e),
    } for e in parsed.entries]
    items.sort(key=lambda i: i["ts"], reverse=True)
    return items


def merge_and_cap(items, max_items=12):
    return sorted(items, key=lambda i: i["ts"], reverse=True)[:max_items]


def provider(cfg):
    feeds = (cfg.get("news") or {}).get("feeds") or []
    max_items = (cfg.get("news") or {}).get("max_items", 12)

    def _do():
        all_items = []
        for url in feeds:
            try:
                r = httpx.get(url, timeout=10, follow_redirects=True,
                              headers={"User-Agent": "Lifeboard/1.0"})
                r.raise_for_status()
                all_items += items_from_feed_text(r.text)
            except Exception:
                continue  # one bad feed shouldn't sink the panel
        return ok(ID, TITLE, items=merge_and_cap(all_items, max_items))

    return run_provider(ID, TITLE, _do)
