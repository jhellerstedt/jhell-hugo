#!/usr/bin/env python3
"""
Fetch or read curated RSS 2.0 feeds, parse item descriptions into structured
fields, write data/papers.json for Hugo (site.Data.papers), and refresh
content/rss-browser/<id>.md stubs for human-readable /rss-browser/<id>/ pages.

Configuration (in order of precedence for URL):
  - Environment variable PAPERS_FEED_URL
  - config.yml → params.papersFeed.url

Local XML directory (when URL is empty):
  - Environment variable PAPERS_FEED_DIR (optional override)
  - config.yml → params.papersFeed.localDir (default: static/rss)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "data" / "papers.json"
FEED_SLUG_RE = re.compile(r"^[a-zA-Z0-9_-]+$")
FILTERED_RSS_PREFIX = re.compile(
    r"^\s*filtered\s+rss\s*[-–—:]\s*(.+)\s*$",
    re.IGNORECASE,
)
ARXIV_ABS_RE = re.compile(r"^https?://arxiv\.org/abs/([^/?#]+)")
OG_IMAGE_RE = re.compile(
    r'(?is)<meta\s+[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']'
)
TW_IMAGE_RE = re.compile(
    r'(?is)<meta\s+[^>]*name=["\']twitter:image["\'][^>]*content=["\']([^"\']+)["\']'
)


def feed_display_title(channel_title: str | None, feed_id: str) -> str:
    """
    UI label: drop 'Filtered RSS —' prefix, underscores → spaces, title-case words.
    """
    raw = (channel_title or "").strip() or (feed_id or "").strip()
    m = FILTERED_RSS_PREFIX.match(raw)
    if m:
        raw = m.group(1).strip()
    raw = re.sub(r"_+", " ", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw.title() if raw else "Feed"

RE_REL = re.compile(r"^reply\.relevance\s*=\s*(\d+)\s*$", re.I)
RE_IMP = re.compile(r"^reply\.impact\s*=\s*(\d+)\s*$", re.I)
RE_TOP = re.compile(
    r"^Highest\s+h-index\s+author\s+on\s+this\s+paper:\s*(.+?)\s*\(\s*h-index\s+(\d+)\s*\)\s*$",
    re.I,
)
RE_INST_COMB = re.compile(
    r"^Institution\s*\(\s*first\s*&\s*last\s+author\s*\)\s*:\s*(.+)\s*$", re.I
)
RE_INST_FIRST = re.compile(r"^First\s+author\s+institution\s*:\s*(.+)\s*$", re.I)
RE_INST_LAST = re.compile(r"^Last\s+author\s+institution\s*:\s*(.+)\s*$", re.I)
RE_ABSTRACT_PREFIX = re.compile(r"^\s*Abstract\s*[—\-:]\s*", re.I)


def strip_ns(tag: str) -> str:
    if tag.startswith("{") and "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def elem_text(el: ET.Element | None) -> str:
    if el is None:
        return ""
    parts: list[str] = []
    if el.text:
        parts.append(el.text)
    for child in el:
        parts.append(elem_text(child))
        if child.tail:
            parts.append(child.tail)
    return "".join(parts)


def norm_lines(raw: str) -> list[str]:
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    return text.split("\n")


def parse_description(raw: str) -> dict[str, Any]:
    """Parse RSS item description plain text into structured fields."""
    lines = norm_lines(raw)
    i = 0
    out: dict[str, Any] = {}

    def skip_blanks() -> None:
        nonlocal i
        while i < len(lines) and not lines[i].strip():
            i += 1

    if i < len(lines):
        m = RE_REL.match(lines[i].strip())
        if m:
            out["relevance"] = int(m.group(1))
            i += 1
    if i < len(lines):
        m = RE_IMP.match(lines[i].strip())
        if m:
            out["impact"] = int(m.group(1))
            i += 1

    skip_blanks()

    if i < len(lines):
        m = RE_TOP.match(lines[i].strip())
        if m:
            out["top_author_name"] = m.group(1).strip()
            out["top_author_h_index"] = int(m.group(2))
            i += 1
            skip_blanks()

    if i < len(lines) and RE_INST_COMB.match(lines[i].strip()):
        m = RE_INST_COMB.match(lines[i].strip())
        assert m
        out["single_institution"] = True
        out["first_institution"] = m.group(1).strip()
        i += 1
        skip_blanks()
    else:
        got_split = False
        if i < len(lines) and RE_INST_FIRST.match(lines[i].strip()):
            m = RE_INST_FIRST.match(lines[i].strip())
            assert m
            out["first_institution"] = m.group(1).strip()
            got_split = True
            i += 1
        if i < len(lines) and RE_INST_LAST.match(lines[i].strip()):
            m = RE_INST_LAST.match(lines[i].strip())
            assert m
            out["last_institution"] = m.group(1).strip()
            got_split = True
            i += 1
        # split affiliations: omit single_institution (templates treat non-true as split)

    skip_blanks()
    abstract = "\n".join(lines[i:]).strip()
    abstract = RE_ABSTRACT_PREFIX.sub("", abstract, count=1).strip()
    if abstract:
        out["abstract"] = abstract

    return out


def item_score(d: dict[str, Any]) -> tuple[int, int]:
    r = d.get("relevance")
    i = d.get("impact")
    return (
        int(r) if r is not None else -1,
        int(i) if i is not None else -1,
    )


def pick_featured(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not items:
        return None
    return max(items, key=item_score)

def _get_env_int(name: str, default: int) -> int:
    v = (os.environ.get(name) or "").strip()
    if not v:
        return default
    try:
        return int(v)
    except ValueError:
        return default


def _fetch_text(url: str, timeout_s: int = 20) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "jhell-hugo-papers-build/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        raw = resp.read()
    # Best-effort decode; HTML/xml from these sources is generally UTF-8.
    return raw.decode("utf-8", errors="replace")


def enrich_arxiv_authors(item: dict[str, Any], cache: dict[str, tuple[str, str, list[str]]]) -> None:
    """
    Populate first_author / last_author / authors[] for arxiv.org/abs/<id> links.
    Uses export.arxiv.org Atom API; cached per arXiv id.
    """
    link = (item.get("link") or "").strip()
    m = ARXIV_ABS_RE.match(link)
    if not m:
        return
    arxiv_id = m.group(1)
    if arxiv_id in cache:
        first, last, authors = cache[arxiv_id]
        if first:
            item["first_author"] = first
        if last:
            item["last_author"] = last
        if authors:
            item["authors"] = authors
        return

    api_url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
    try:
        xml = _fetch_text(api_url, timeout_s=25)
        root = ET.fromstring(xml)
        ns = {"a": "http://www.w3.org/2005/Atom"}
        entry = root.find("a:entry", ns)
        authors: list[str] = []
        if entry is not None:
            for a in entry.findall("a:author", ns):
                name = a.findtext("a:name", default="", namespaces=ns).strip()
                if name:
                    authors.append(name)
    except (urllib.error.URLError, ET.ParseError, OSError):
        authors = []

    first = authors[0] if authors else ""
    last = authors[-1] if authors else ""
    cache[arxiv_id] = (first, last, authors)
    if first:
        item["first_author"] = first
    if last:
        item["last_author"] = last
    if authors:
        item["authors"] = authors


def enrich_og_image(item: dict[str, Any]) -> None:
    """
    Best-effort thumbnail via og:image or twitter:image meta tags.
    Intended for publisher pages; arXiv is usually not helpful.
    """
    link = (item.get("link") or "").strip()
    if not link or ARXIV_ABS_RE.match(link):
        return
    try:
        html = _fetch_text(link, timeout_s=15)
    except (urllib.error.URLError, OSError):
        return
    m = OG_IMAGE_RE.search(html) or TW_IMAGE_RE.search(html)
    if not m:
        return
    url = m.group(1).strip()
    if url:
        item["image_url"] = url


def slugify(label: str) -> str:
    s = label.lower()
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"[-\s]+", "_", s).strip("_")
    return (s[:80] if s else "feed")


def parse_rss_bytes(
    data: bytes,
    source: str,
    rss_href: str,
    feed_id: str | None = None,
) -> dict[str, Any]:
    root = ET.fromstring(data)
    if strip_ns(root.tag) != "rss":
        raise ValueError(f"Expected RSS root in {source!r}")

    channel = None
    for child in root:
        if strip_ns(child.tag) == "channel":
            channel = child
            break
    if channel is None:
        raise ValueError(f"No channel in {source!r}")

    channel_title = ""
    for child in channel:
        tag = strip_ns(child.tag)
        if tag == "title":
            channel_title = elem_text(child).strip()
            break

    items_out: list[dict[str, Any]] = []
    enrich_authors = _get_env_int("PAPERS_ENRICH_AUTHORS", 1) != 0
    enrich_images = _get_env_int("PAPERS_ENRICH_IMAGES", 0) != 0
    max_images = max(0, _get_env_int("PAPERS_ENRICH_IMAGES_MAX", 10))
    arxiv_cache: dict[str, tuple[str, str, list[str]]] = {}
    images_done = 0

    for child in channel:
        if strip_ns(child.tag) != "item":
            continue
        title = link = guid = pub_date = description = ""
        for el in child:
            t = strip_ns(el.tag)
            if t == "title":
                title = elem_text(el).strip()
            elif t == "link":
                link = elem_text(el).strip()
            elif t == "guid":
                guid = elem_text(el).strip()
            elif t == "pubDate":
                pub_date = elem_text(el).strip()
            elif t == "description":
                description = elem_text(el).strip()

        parsed = parse_description(description)
        item: dict[str, Any] = {
            "title": title,
            "link": link,
            "guid": guid,
            "pub_date": pub_date,
            **parsed,
        }
        if enrich_authors:
            enrich_arxiv_authors(item, arxiv_cache)
        if enrich_images and images_done < max_images:
            before = item.get("image_url")
            enrich_og_image(item)
            if item.get("image_url") and not before:
                images_done += 1
        items_out.append(item)

    featured = pick_featured(items_out)
    fid = feed_id or (
        slugify(channel_title) if channel_title else slugify(source)
    )
    display_title = feed_display_title(channel_title, fid)

    return {
        "id": fid,
        "channel_title": channel_title,
        "display_title": display_title,
        "source": source,
        "rss_href": rss_href,
        "items": items_out,
        "featured": featured,
    }


def _strip_yaml_scalar(value: str) -> str:
    v = value.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


def load_papers_feed_from_config(cfg_path: Path) -> dict[str, str]:
    """
    Read params.papersFeed.url and localDir from config.yml without PyYAML.
    """
    url = ""
    local_dir = "static/rss"
    if not cfg_path.is_file():
        return {"url": url, "localDir": local_dir}

    lines = cfg_path.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if re.match(r"^\s*papersFeed\s*:", line):
            base_indent = len(line) - len(line.lstrip())
            i += 1
            while i < len(lines):
                li = lines[i]
                if not li.strip() or li.lstrip().startswith("#"):
                    i += 1
                    continue
                ind = len(li) - len(li.lstrip())
                if ind <= base_indent:
                    break
                m = re.match(r"^\s*url\s*:\s*(.*)$", li)
                if m:
                    url = _strip_yaml_scalar(m.group(1))
                m = re.match(r"^\s*localDir\s*:\s*(.*)$", li)
                if m:
                    local_dir = _strip_yaml_scalar(m.group(1)) or local_dir
                i += 1
            break
        i += 1

    return {"url": url, "localDir": local_dir}


def papers_feed_settings() -> tuple[str, str]:
    """Returns (feed_url, local_dir)."""
    cfg_path = REPO_ROOT / "config.yml"
    pf = load_papers_feed_from_config(cfg_path)
    url = (pf.get("url") or "").strip()
    local_dir = (pf.get("localDir") or "static/rss").strip()

    url = (os.environ.get("PAPERS_FEED_URL") or "").strip() or url
    local_dir = (os.environ.get("PAPERS_FEED_DIR") or local_dir).strip()

    return url, local_dir


def fetch_url(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "jhell-hugo-papers-build/1.0"},
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        return resp.read()


def build_feeds(
    url: str,
    local_dir: str,
    fixtures_dir: Path | None,
) -> list[dict[str, Any]]:
    feeds: list[dict[str, Any]] = []

    if fixtures_dir is not None:
        paths = sorted(fixtures_dir.glob("*.xml"))
        if not paths:
            print(f"No *.xml under {fixtures_dir}", file=sys.stderr)
            return []
        for path in paths:
            feeds.append(
                parse_rss_bytes(
                    path.read_bytes(),
                    source=str(path.relative_to(REPO_ROOT)),
                    rss_href="",
                    feed_id=path.stem,
                )
            )
        return feeds

    if url:
        data = fetch_url(url)
        feeds.append(
            parse_rss_bytes(data, source=url, rss_href="", feed_id=None)
        )
        return feeds

    base = REPO_ROOT / local_dir
    if not base.is_dir():
        print(f"No feed URL set and local dir missing: {base}", file=sys.stderr)
        return []

    xml_files = sorted(base.glob("*.xml"))
    if not xml_files:
        print(f"No *.xml in {base}", file=sys.stderr)
        return []

    for path in xml_files:
        data = path.read_bytes()
        stem = path.stem
        feeds.append(
            parse_rss_bytes(
                data,
                source=str(path.relative_to(REPO_ROOT)),
                rss_href=f"/rss/{path.name}",
                feed_id=stem,
            )
        )
    return feeds


def write_rss_browser_pages(feeds: list[dict[str, Any]], repo_root: Path) -> None:
    """
    One Hugo leaf page per feed under content/rss-browser/<id>.md so
    /rss-browser/<id>/ can render a human-readable listing (see layouts/rss-browser/).
    """
    browser_dir = repo_root / "content" / "rss-browser"
    browser_dir.mkdir(parents=True, exist_ok=True)

    valid_ids: set[str] = set()
    for feed in feeds:
        fid = str(feed.get("id") or "")
        if not FEED_SLUG_RE.match(fid):
            print(f"Skipping rss-browser page for unsafe feed id {fid!r}", file=sys.stderr)
            continue
        valid_ids.add(fid)

    for path in browser_dir.glob("*.md"):
        if path.name == "_index.md":
            continue
        if path.stem not in valid_ids:
            path.unlink()
            print(f"Removed stale {path.relative_to(repo_root)}", file=sys.stderr)

    for feed in feeds:
        fid = str(feed.get("id") or "")
        if not FEED_SLUG_RE.match(fid):
            continue
        title = feed_display_title(feed.get("channel_title"), fid)
        title_yaml = json.dumps(title, ensure_ascii=False)
        front = (
            "---\n"
            f"title: {title_yaml}\n"
            'description: "All papers in this category (from the curated RSS export)."\n'
            f"feed_id: {fid}\n"
            "hideMeta: true\n"
            "---\n\n"
        )
        (browser_dir / f"{fid}.md").write_text(front, encoding="utf-8")

    print(f"Wrote {len(valid_ids)} page(s) under content/rss-browser/")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build data/papers.json for Hugo")
    parser.add_argument(
        "--fixtures",
        action="store_true",
        help="Use scripts/fixtures/sample_papers_feed.xml only (for verification)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output JSON path (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()

    url, local_dir = papers_feed_settings()
    fixtures_dir: Path | None = None
    if args.fixtures:
        fixtures_dir = REPO_ROOT / "scripts" / "fixtures"
        if not fixtures_dir.is_dir():
            print(f"Fixtures directory missing: {fixtures_dir}", file=sys.stderr)
            return 1
        url = ""
        local_dir = ""

    try:
        feeds = build_feeds(url, local_dir, fixtures_dir)
    except (urllib.error.URLError, OSError, ValueError, ET.ParseError) as e:
        print(f"Error building papers data: {e}", file=sys.stderr)
        return 1

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "feeds": feeds,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Wrote {len(feeds)} feed(s) to {args.output}")
    write_rss_browser_pages(feeds, REPO_ROOT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
