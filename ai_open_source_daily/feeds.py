from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import re
from typing import List, Optional
from xml.etree import ElementTree

from .models import FeedItem


_TAG_RE = re.compile(r"<[^>]+>")


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _child_text(node: ElementTree.Element, names: List[str]) -> str:
    wanted = set(names)
    for child in list(node):
        if _local_name(child.tag) in wanted:
            return "".join(child.itertext()).strip()
    return ""


def _parse_date(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class FeedReader:
    def read(self, xml_text: str, since: datetime) -> List[FeedItem]:
        if since.tzinfo is None:
            since = since.replace(tzinfo=timezone.utc)
        since = since.astimezone(timezone.utc)
        root = ElementTree.fromstring(xml_text)
        results: List[FeedItem] = []
        for node in root.iter():
            if _local_name(node.tag) not in ("item", "entry"):
                continue
            title = _child_text(node, ["title"])
            url = _child_text(node, ["link"])
            if not url:
                for child in list(node):
                    if _local_name(child.tag) == "link":
                        url = child.attrib.get("href", "")
                        if url:
                            break
            published = _child_text(node, ["pubdate", "published", "updated", "date"])
            parsed = _parse_date(published)
            if not title or not parsed or parsed < since:
                continue
            summary = _child_text(node, ["description", "summary", "content"])
            results.append(FeedItem(title, url, parsed.isoformat(), _TAG_RE.sub("", summary).strip()))
        return sorted(results, key=lambda item: item.published_at, reverse=True)
