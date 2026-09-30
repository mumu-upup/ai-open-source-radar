from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class RepoSnapshot:
    repo: str
    name: str
    url: str
    description: str
    stars: int
    forks: int
    pushed_at: Optional[str]
    updated_at: Optional[str]
    topics: List[str]
    archived: bool
    fork: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repo": self.repo,
            "name": self.name,
            "url": self.url,
            "description": self.description,
            "stars": self.stars,
            "forks": self.forks,
            "pushed_at": self.pushed_at,
            "updated_at": self.updated_at,
            "topics": list(self.topics),
            "archived": self.archived,
            "fork": self.fork,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RepoSnapshot":
        return cls(
            repo=str(data["repo"]),
            name=str(data.get("name") or data["repo"].split("/", 1)[-1]),
            url=str(data.get("url") or "https://github.com/" + data["repo"]),
            description=str(data.get("description") or ""),
            stars=int(data.get("stars", 0)),
            forks=int(data.get("forks", 0)),
            pushed_at=data.get("pushed_at"),
            updated_at=data.get("updated_at"),
            topics=list(data.get("topics") or []),
            archived=bool(data.get("archived", False)),
            fork=bool(data.get("fork", False)),
        )


@dataclass(frozen=True)
class DailyRepo:
    repo: RepoSnapshot
    delta_24h: Optional[int]
    delta_7d: Optional[int]
    baseline: bool


@dataclass(frozen=True)
class FeedItem:
    title: str
    url: str
    published_at: str
    summary: str = ""


@dataclass(frozen=True)
class TrendingRepo:
    repo: str
    url: str
    stars_today: int
    description: str = ""
