from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import re
from typing import List, Optional
from xml.etree import ElementTree

from .models import FeedItem


_TAG_RE = re.compile(r"<[^>]+>")
_MARKDOWN_DATE_RE = re.compile(r"^###\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})\s*$")
_MARKDOWN_BULLET_RE = re.compile(r"^\s*[*-]\s+(.*)$")
_UPDATE_BLOCK_RE = re.compile(r"<Update\b([^>]*)>(.*?)</Update>", re.I | re.S)
_UPDATE_ATTR_RE = re.compile(r"([A-Za-z_][\w-]*)=\"([^\"]*)\"")
_DEEPSEEK_SECTION_RE = re.compile(
    r'<h2\b[^>]*\bid="date-(\d{4}-\d{2}-\d{2})"[^>]*>.*?</h2>(.*?)(?=<h2\b[^>]*\bid="date-\d{4}-\d{2}-\d{2}"|$)',
    re.I | re.S,
)
_AI_EVENT_RE = re.compile(
    r"\b(ai|artificial intelligence|machine learning|llm|agent|model|inference|rag|diffusion|embedding|vision|voice|tts|stt|generative|openai|gpt|chatgpt|codex|anthropic|claude|gemini|glm|kimi|deepseek|qwen|llama|mistral|copilot|mcp|multimodal|computer-use|hermes|gemma|grok|phi|minimax|jev)\b",
    re.I,
)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _child_text(node: ElementTree.Element, names: List[str]) -> str:
    wanted = set(names)
    for child in list(node):
        if _local_name(child.tag) in wanted:
            return "".join(child.itertext()).strip()
    return ""


def _parse_date(value: str) -> Optional[datetime]:
    if not isinstance(value, str) or not value:
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
    def read(
        self,
        xml_text: str,
        since: datetime,
        source: str = "",
        ai_only: bool = False,
        until: Optional[datetime] = None,
    ) -> List[FeedItem]:
        if since.tzinfo is None:
            since = since.replace(tzinfo=timezone.utc)
        since = since.astimezone(timezone.utc)
        if until is not None:
            if until.tzinfo is None:
                until = until.replace(tzinfo=timezone.utc)
            until = until.astimezone(timezone.utc)
        root = ElementTree.fromstring(xml_text)
        results: List[FeedItem] = []
        seen = set()
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
            if not title or not parsed or parsed < since or (until is not None and parsed >= until):
                continue
            summary = _child_text(node, ["description", "summary", "content"])
            if ai_only and not _AI_EVENT_RE.search("%s %s" % (title, summary)):
                continue
            key = url or title
            if key in seen:
                continue
            seen.add(key)
            results.append(FeedItem(title, url, parsed.isoformat(), _TAG_RE.sub("", summary).strip(), source))
        return sorted(results, key=lambda item: item.published_at, reverse=True)

    def read_huggingface_models(
        self,
        json_text: str,
        since: datetime,
        source: str = "",
        until: Optional[datetime] = None,
        base_url: str = "",
    ) -> List[FeedItem]:
        """Read model repository activity from the Hugging Face models API."""
        try:
            payload = json.loads(json_text)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("invalid Hugging Face models JSON") from exc
        if not isinstance(payload, list):
            raise ValueError("Hugging Face models payload must be a list")

        if since.tzinfo is None:
            since = since.replace(tzinfo=timezone.utc)
        since = since.astimezone(timezone.utc)
        if until is not None:
            if until.tzinfo is None:
                until = until.replace(tzinfo=timezone.utc)
            until = until.astimezone(timezone.utc)

        results: List[FeedItem] = []
        seen = set()
        for row in payload:
            if not isinstance(row, dict):
                continue
            model_id = row.get("id")
            if not isinstance(model_id, str) or not model_id.strip():
                continue
            model_id = model_id.strip()
            modified = _parse_date(row.get("lastModified"))
            if modified is None or modified < since or (until is not None and modified >= until):
                continue
            url = "https://huggingface.co/" + model_id.lstrip("/")
            if url in seen:
                continue
            seen.add(url)

            created = _parse_date(row.get("createdAt"))
            new_repository = (
                created is not None
                and created <= modified
                and created >= since
                and (until is None or created < until)
            )
            activity_kind = "New model repository" if new_repository else "Model repository update"
            title = "%s — %s" % (model_id, activity_kind)
            if new_repository:
                summary = (
                    "New model repository created on Hugging Face at %s; "
                    "repository activity last modified at %s."
                ) % (created.isoformat(), modified.isoformat())
            else:
                summary = (
                    "Model repository updated on Hugging Face; last modified at %s."
                    % modified.isoformat()
                )

            pipeline = row.get("pipeline_tag")
            if isinstance(pipeline, str) and pipeline.strip():
                summary += " Pipeline: %s." % pipeline.strip()
            tags = row.get("tags")
            if isinstance(tags, list):
                clean_tags = []
                for tag in tags:
                    if isinstance(tag, str) and tag.strip() and tag.strip() not in clean_tags:
                        clean_tags.append(tag.strip())
                if clean_tags:
                    summary += " Tags: %s." % ", ".join(clean_tags)
            results.append(FeedItem(title, url, modified.isoformat(), summary, source))
        return sorted(results, key=lambda item: item.published_at, reverse=True)

    def read_markdown(
        self,
        markdown_text: str,
        since: datetime,
        source: str = "",
        until: Optional[datetime] = None,
        base_url: str = "",
    ) -> List[FeedItem]:
        """Read dated bullet entries from a simple Markdown changelog."""
        if since.tzinfo is None:
            since = since.replace(tzinfo=timezone.utc)
        since = since.astimezone(timezone.utc)
        if until is not None:
            if until.tzinfo is None:
                until = until.replace(tzinfo=timezone.utc)
            until = until.astimezone(timezone.utc)
        results: List[FeedItem] = []
        current_date: Optional[datetime] = None
        bullet_index = 0
        for line in markdown_text.splitlines():
            heading = _MARKDOWN_DATE_RE.match(line.strip())
            if heading:
                try:
                    current_date = datetime.strptime(heading.group(1), "%B %d, %Y").replace(tzinfo=timezone.utc)
                except ValueError:
                    current_date = None
                bullet_index = 0
                continue
            if current_date is None or current_date < since or (until is not None and current_date >= until):
                continue
            bullet = _MARKDOWN_BULLET_RE.match(line)
            if not bullet:
                continue
            bullet_index += 1
            cleaned = bullet.group(1).strip()
            cleaned = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", cleaned)
            cleaned = re.sub(r"[*_`]+", "", cleaned)
            if not cleaned:
                continue
            date_key = current_date.date().isoformat()
            url = "%s#%s-%d" % (base_url.rstrip("/"), date_key, bullet_index) if base_url else "#"
            results.append(FeedItem(cleaned[:180], url, current_date.isoformat(), cleaned, source))
        return sorted(results, key=lambda item: item.published_at, reverse=True)

    def read_update_markup(
        self,
        markup_text: str,
        since: datetime,
        source: str = "",
        until: Optional[datetime] = None,
        base_url: str = "",
    ) -> List[FeedItem]:
        """Read dated <Update label=...> blocks used by several model changelogs."""
        if since.tzinfo is None:
            since = since.replace(tzinfo=timezone.utc)
        since = since.astimezone(timezone.utc)
        if until is not None:
            if until.tzinfo is None:
                until = until.replace(tzinfo=timezone.utc)
            until = until.astimezone(timezone.utc)
        results: List[FeedItem] = []
        for index, match in enumerate(_UPDATE_BLOCK_RE.finditer(markup_text), 1):
            attrs = dict(_UPDATE_ATTR_RE.findall(match.group(1)))
            label = attrs.get("label", "")
            parsed = None
            try:
                if re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", label):
                    parsed = datetime.strptime(label, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                elif re.fullmatch(r"\d{4}年\d{1,2}月", label):
                    parsed = datetime.strptime(label, "%Y年%m月").replace(tzinfo=timezone.utc)
            except ValueError:
                parsed = None
            if parsed is None or parsed < since or (until is not None and parsed >= until):
                continue
            body = _TAG_RE.sub(" ", match.group(2))
            body = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", body)
            body = re.sub(r"[#*_`]+", "", body)
            body = " ".join(body.split())
            title = attrs.get("description", "").strip() or body[:180] or "模型平台更新"
            date_key = parsed.date().isoformat()
            url = "%s#%s-%d" % (base_url.rstrip("/"), date_key, index) if base_url else "#"
            results.append(FeedItem(title, url, parsed.isoformat(), body, source))
        return sorted(results, key=lambda item: item.published_at, reverse=True)

    def read_deepseek_html(
        self,
        html_text: str,
        since: datetime,
        source: str = "",
        until: Optional[datetime] = None,
        base_url: str = "",
    ) -> List[FeedItem]:
        """Read dated h2/h3/p sections from the DeepSeek API changelog."""
        if since.tzinfo is None:
            since = since.replace(tzinfo=timezone.utc)
        since = since.astimezone(timezone.utc)
        if until is not None:
            if until.tzinfo is None:
                until = until.replace(tzinfo=timezone.utc)
            until = until.astimezone(timezone.utc)
        results: List[FeedItem] = []
        for section in _DEEPSEEK_SECTION_RE.finditer(html_text):
            parsed = datetime.fromisoformat(section.group(1)).replace(tzinfo=timezone.utc)
            if parsed < since or (until is not None and parsed >= until):
                continue
            block = section.group(2)
            title_match = re.search(r"<h3\b[^>]*>(.*?)</h3>", block, re.I | re.S)
            summary_match = re.search(r"<p\b[^>]*>(.*?)</p>", block, re.I | re.S)
            title = _TAG_RE.sub(" ", title_match.group(1) if title_match else "").strip()
            summary = _TAG_RE.sub(" ", summary_match.group(1) if summary_match else "").strip()
            title = " ".join(title.split())
            summary = " ".join(summary.split())
            if not title:
                continue
            url = "%s#date-%s" % (base_url.rstrip("/"), section.group(1)) if base_url else "#"
            results.append(FeedItem(title, url, parsed.isoformat(), summary, source))
        return sorted(results, key=lambda item: item.published_at, reverse=True)
