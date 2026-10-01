import json
from datetime import date, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

from .models import RepoSnapshot


def calculate_delta(current: int, previous: Optional[int]) -> Optional[int]:
    return None if previous is None else current - previous


class SnapshotStore:
    def __init__(self, root: Path):
        self.root = root

    def _path(self, day: date) -> Path:
        return self.root / (day.isoformat() + ".json")

    def save(self, day: date, repos: List[RepoSnapshot]) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path(day)
        path.write_text(
            json.dumps([repo.to_dict() for repo in repos], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return path

    def load(self, day: date) -> Optional[List[RepoSnapshot]]:
        path = self._path(day)
        if not path.exists():
            return None
        return [RepoSnapshot.from_dict(item) for item in json.loads(path.read_text(encoding="utf-8"))]

    def find_previous(self, repo: str, before: date, days: int) -> Optional[RepoSnapshot]:
        for offset in range(1, days + 1):
            items = self.load(before - timedelta(days=offset))
            if items:
                for item in items:
                    if item.repo == repo:
                        return item
        return None

    def find_previous_with_day(self, repo: str, before: date, days: int) -> Optional[Tuple[date, RepoSnapshot]]:
        for offset in range(1, days + 1):
            snapshot_day = before - timedelta(days=offset)
            items = self.load(snapshot_day)
            if items is None:
                continue
            for item in items:
                if item.repo == repo:
                    return snapshot_day, item
        return None
