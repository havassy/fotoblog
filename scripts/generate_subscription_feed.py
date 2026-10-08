#!/usr/bin/env python3
"""Maintain the Atom feed used only for e-mail notifications.

The normal Jekyll feed is intentionally based on the date when a photograph
was taken.  That is right for the photo blog, but it means a newly uploaded
old photograph can be absent from the normal feed.  This script keeps a
separate, publication-order feed without changing any post metadata.

The state file is deliberately append-only for an existing photo slug:
editing an XMP file later may update the post, but cannot create another feed
entry or another notification.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POSTS_DIR = ROOT / "_posts"
STATE_PATH = ROOT / ".subscription-feed-state.json"
FEED_PATH = ROOT / "subscription-feed.xml"
SITE_URL = "https://havassy.github.io/fotoblog"
FEED_URL = f"{SITE_URL}/subscription-feed.xml"


def post_slug(post_path: Path) -> str:
    match = re.match(r"^\d{4}-\d{2}-\d{2}-(.+)\.md$", post_path.name)
    if not match:
        raise ValueError(f"Unexpected post file name: {post_path.name}")
    return match.group(1)


def post_url(post_path: Path) -> str:
    match = re.match(r"^(\d{4})-(\d{2})-(\d{2})-(.+)\.md$", post_path.name)
    if not match:
        raise ValueError(f"Unexpected post file name: {post_path.name}")
    year, month, day, slug = match.groups()
    return f"{SITE_URL}/{year}/{month}/{day}/{slug}.html"


def unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def front_matter(post_path: Path) -> dict[str, str]:
    text = post_path.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, flags=re.DOTALL)
    if not match:
        raise ValueError(f"Missing front matter: {post_path}")

    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        field = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", line)
        if field:
            fields[field.group(1)] = unquote(field.group(2))
    return fields


def discover_posts() -> dict[str, Path]:
    posts: dict[str, Path] = {}
    for post_path in sorted(POSTS_DIR.glob("*.md")):
        posts[post_slug(post_path)] = post_path
    return posts


def write_json(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def render_feed(entries: list[dict], updated: str) -> str:
    rows = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<feed xmlns="http://www.w3.org/2005/Atom">',
        '  <title>Napjaim a Balkánon – új bejegyzések</title>',
        f'  <id>{FEED_URL}</id>',
        f'  <link href="{FEED_URL}" rel="self" type="application/atom+xml" />',
        f'  <link href="{SITE_URL}/" rel="alternate" type="text/html" />',
        f'  <updated>{updated}</updated>',
    ]
    for entry in sorted(entries, key=lambda item: item["published"], reverse=True):
        rows.extend(
            [
                "  <entry>",
                f'    <title type="html">{escape(entry["title"])}</title>',
                f'    <id>{escape(entry["id"])}</id>',
                f'    <link href="{escape(entry["url"], quote=True)}" rel="alternate" type="text/html" />',
                f'    <published>{entry["published"]}</published>',
                f'    <updated>{entry["published"]}</updated>',
                f'    <summary type="html">{escape(entry["summary"])}</summary>',
                "  </entry>",
            ]
        )
    rows.append("</feed>")
    return "\n".join(rows) + "\n"


def initialise(posts: dict[str, Path]) -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    state = {
        "version": 1,
        "initialised_at": now,
        "known_slugs": sorted(posts),
        "entries": [],
    }
    write_json(STATE_PATH, state)
    FEED_PATH.write_text(render_feed([], now), encoding="utf-8")
    print(f"Initialised subscription feed with {len(posts)} existing posts and no entries.")


def update() -> None:
    if not STATE_PATH.exists():
        raise SystemExit(
            "Missing .subscription-feed-state.json. Run with --initialise once before enabling the feed."
        )

    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    known_slugs = set(state.get("known_slugs", []))
    entries = list(state.get("entries", []))
    posts = discover_posts()
    new_slugs = sorted(set(posts) - known_slugs)

    if not new_slugs:
        print("No new posts for the subscription feed.")
        return

    published = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    for slug in new_slugs:
        post_path = posts[slug]
        fields = front_matter(post_path)
        title = fields.get("title", slug.replace("_", " ").replace("-", " ").title())
        summary = fields.get("description", "")
        url = post_url(post_path)
        entries.append(
            {
                "id": f"{SITE_URL}/subscription/{slug}",
                "slug": slug,
                "title": title,
                "summary": summary,
                "url": url,
                "published": published,
            }
        )

    state["known_slugs"] = sorted(known_slugs | set(new_slugs))
    state["entries"] = entries
    state["updated_at"] = published
    write_json(STATE_PATH, state)
    FEED_PATH.write_text(render_feed(entries, published), encoding="utf-8")
    print(f"Added {len(new_slugs)} new post(s) to the subscription feed.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--initialise", action="store_true")
    args = parser.parse_args()
    posts = discover_posts()

    if args.initialise:
        if STATE_PATH.exists():
            raise SystemExit(f"Refusing to overwrite existing state: {STATE_PATH}")
        initialise(posts)
    else:
        update()


if __name__ == "__main__":
    main()
