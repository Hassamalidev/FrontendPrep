"""Fetch recent news and turn it into current-affairs material.

**What this deliberately does and does not do.** It reads public RSS feeds --
the syndication format publishers provide precisely so software can read it --
and stores the headline, summary and link. It does *not* scrape other coaching
sites' question banks: those are someone else's copyrighted content, and copying
them would be both a legal problem and a worse product. Questions are generated
from the news by this platform's own pipeline, which is what the whole
``app/agents/`` package exists for.

**What is stored.** Headline, summary, source, link and date. Full article text
is only kept when the feed itself carries it, and the retention job drops even
that once questions have been generated. Nothing is republished wholesale.

Feeds are configurable because the useful set changes; the defaults are the
Pakistani outlets a candidate is expected to be reading anyway.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.enums import ContentStatus
from app.models.content import Article
from app.models.user import User
from app.schemas.content import ArticleIn
from app.services import content_service

log = logging.getLogger("issb.news")

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")

# Namespaces RSS feeds use for the fuller body some publishers include.
_CONTENT_NS = "{http://purl.org/rss/1.0/modules/content/}encoded"
_DC_DATE = "{http://purl.org/dc/elements/1.1/}date"


@dataclass(slots=True)
class FeedItem:
    title: str
    summary: str
    link: str
    source: str
    published: datetime | None
    body: str = ""

    @property
    def text(self) -> str:
        """What the question pipeline reads: the fullest text we legitimately have."""
        return self.body if len(self.body) > len(self.summary) else self.summary


def _clean(raw: str | None) -> str:
    if not raw:
        return ""
    return _WS.sub(" ", _TAG.sub(" ", raw)).strip()


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def parse_feed(xml: str, source: str) -> list[FeedItem]:
    """Parse RSS 2.0 or Atom into a common shape. Never raises on bad XML."""
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError:
        log.warning("could not parse feed from %s", source)
        return []

    items: list[FeedItem] = []

    # RSS 2.0
    for node in root.iter("item"):
        title = _clean(node.findtext("title"))
        if not title:
            continue
        items.append(
            FeedItem(
                title=title,
                summary=_clean(node.findtext("description")),
                link=(node.findtext("link") or "").strip(),
                source=source,
                published=_parse_date(node.findtext("pubDate") or node.findtext(_DC_DATE)),
                body=_clean(node.findtext(_CONTENT_NS)),
            )
        )

    # Atom
    if not items:
        atom = "{http://www.w3.org/2005/Atom}"
        for node in root.iter(f"{atom}entry"):
            title = _clean(node.findtext(f"{atom}title"))
            if not title:
                continue
            link_node = node.find(f"{atom}link")
            items.append(
                FeedItem(
                    title=title,
                    summary=_clean(
                        node.findtext(f"{atom}summary") or node.findtext(f"{atom}content")
                    ),
                    link=(link_node.get("href") if link_node is not None else "") or "",
                    source=source,
                    published=_parse_date(
                        node.findtext(f"{atom}published") or node.findtext(f"{atom}updated")
                    ),
                )
            )

    return items


async def fetch_feed(client: httpx.AsyncClient, url: str, source: str) -> list[FeedItem]:
    """One feed. A failure is logged and skipped, never fatal to the run."""
    try:
        response = await client.get(url, timeout=settings.NEWS_TIMEOUT_SEC)
        response.raise_for_status()
    except Exception as exc:
        log.warning("feed %s failed: %s", source, exc)
        return []
    return parse_feed(response.text, source)


def _within_window(item: FeedItem, days: int) -> bool:
    """Current affairs means current. Anything older is not what a board asks about."""
    if item.published is None:
        return True  # undated items are usually the newest on the feed
    return item.published >= datetime.now(UTC) - timedelta(days=days)


async def fetch_recent(days: int | None = None, limit: int | None = None) -> list[FeedItem]:
    """Every configured feed, newest first, inside the recency window."""
    window = days or settings.NEWS_WINDOW_DAYS
    cap = limit or settings.NEWS_MAX_ITEMS

    feeds: list[tuple[str, str]] = []
    for entry in settings.NEWS_FEEDS.split(","):
        entry = entry.strip()
        if not entry:
            continue
        source, _, url = entry.partition("|")
        feeds.append((source.strip(), url.strip() or source.strip()))

    headers = {"User-Agent": f"{settings.APP_NAME}/{settings.APP_VERSION} (feed reader)"}
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        batches = await asyncio.gather(
            *(fetch_feed(client, url, source) for source, url in feeds)
        )

    items = [item for batch in batches for item in batch if _within_window(item, window)]
    items.sort(key=lambda i: i.published or datetime.now(UTC), reverse=True)

    # De-duplicate on headline: the same wire story runs on several outlets.
    seen: set[str] = set()
    unique: list[FeedItem] = []
    for item in items:
        key = _WS.sub(" ", item.title.lower()).strip()[:120]
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)

    return unique[:cap]


# --- In-memory cache -------------------------------------------------------
#
# Current affairs are read once and then stale. Storing them would add a few
# thousand rows a year and tens of megabytes of body text for content nobody
# re-reads -- on a 0.5 GB free tier that is the most wasteful thing the platform
# could do. So the feed lives in process memory with a TTL and is simply
# re-fetched when it expires. A cold start costs one HTTP round trip.
#
# The durable artefact is the *question* generated from a story, which is small
# and permanently useful. The story itself is not kept.

_cache: dict[str, tuple[datetime, list[FeedItem]]] = {}


def _cache_key(days: int, limit: int) -> str:
    return f"{days}:{limit}"


async def live_items(days: int | None = None, limit: int | None = None) -> list[FeedItem]:
    """Recent stories, cached in memory. Never touches the database."""
    window = days or settings.NEWS_WINDOW_DAYS
    cap = limit or settings.NEWS_MAX_ITEMS
    key = _cache_key(window, cap)

    hit = _cache.get(key)
    if hit and hit[0] > datetime.now(UTC):
        return hit[1]

    items = await fetch_recent(window, cap)
    if items:  # never cache a failed fetch, or one outage lasts the whole TTL
        _cache[key] = (
            datetime.now(UTC) + timedelta(minutes=settings.NEWS_CACHE_MINUTES),
            items,
        )
    return items


def cache_state() -> dict:
    """What is cached and until when, for the admin screen."""
    now = datetime.now(UTC)
    return {
        "entries": len(_cache),
        "items": sum(len(v[1]) for v in _cache.values()),
        "expires_in_sec": max(
            (int((expiry - now).total_seconds()) for expiry, _ in _cache.values()), default=0
        ),
        "stored_in_database": False,
    }


def clear_cache() -> None:
    _cache.clear()


async def ingest(
    db: AsyncSession,
    *,
    actor: User,
    days: int | None = None,
    limit: int | None = None,
    publish: bool = True,
) -> dict:
    """Fetch, filter and store. Returns what happened, for the admin screen."""
    items = await fetch_recent(days, limit)

    created: list[Article] = []
    skipped_short = 0
    skipped_duplicate = 0

    for item in items:
        text = item.text
        # Too thin to generate from, and too thin to be worth reading.
        if len(text) < settings.NEWS_MIN_CHARS:
            skipped_short += 1
            continue

        body = f"{item.title}. {text}"
        digest = content_service.body_hash(body)
        from sqlalchemy import select

        if await db.scalar(select(Article.id).where(Article.body_hash == digest)):
            skipped_duplicate += 1
            continue

        try:
            article = await content_service.create_article(
                db,
                ArticleIn(
                    title=item.title[:240],
                    body=body,
                    category="current_affairs",
                    summary=item.summary[:4000] or None,
                    source_name=item.source[:120],
                    source_url=item.link[:500] or None,
                    published_on=item.published.date() if item.published else None,
                    status=ContentStatus.APPROVED if publish else ContentStatus.DRAFT,
                    is_featured=False,
                ),
                author=actor,
            )
            created.append(article)
        except Exception as exc:  # a single bad item must not end the run
            log.warning("could not store %r: %s", item.title[:60], exc)

    log.info(
        "news ingest: %d fetched, %d stored, %d duplicates, %d too short",
        len(items), len(created), skipped_duplicate, skipped_short,
    )
    return {
        "fetched": len(items),
        "stored": len(created),
        "duplicates": skipped_duplicate,
        "too_short": skipped_short,
        "articles": [{"id": a.id, "title": a.title, "source": a.source_name} for a in created],
    }
