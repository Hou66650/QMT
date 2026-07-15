from __future__ import annotations

import json
from pathlib import Path
from threading import RLock

from app.schemas import WatchlistItem


class WatchlistService:
    def __init__(self, path: Path):
        self.path = path
        self._lock = RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write([WatchlistItem(code="600519", name="贵州茅台"), WatchlistItem(code="300750", name="宁德时代"), WatchlistItem(code="000001", name="平安银行")])

    def _read(self) -> list[WatchlistItem]:
        with self._lock:
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                return [WatchlistItem.model_validate(item) for item in data]
            except (json.JSONDecodeError, OSError):
                return []

    def _write(self, items: list[WatchlistItem]) -> None:
        with self._lock:
            self.path.write_text(json.dumps([item.model_dump() for item in items], ensure_ascii=False, indent=2), encoding="utf-8")

    def list(self) -> list[WatchlistItem]:
        return self._read()

    def add(self, item: WatchlistItem) -> list[WatchlistItem]:
        items = self._read()
        if all(existing.code != item.code for existing in items):
            items.append(item)
            self._write(items)
        return items

    def delete(self, code: str) -> list[WatchlistItem]:
        items = [item for item in self._read() if item.code != code.upper()]
        self._write(items)
        return items
