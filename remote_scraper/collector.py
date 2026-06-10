from __future__ import annotations

from remote_scraper.items import RemoteJobItem

_COLLECTED: list[dict] = []


class CollectorPipeline:
    def process_item(self, item: RemoteJobItem, spider=None):  # noqa: ANN001
        _COLLECTED.append(dict(item))
        return item


def clear_collected_items() -> None:
    _COLLECTED.clear()


def get_collected_items() -> list[dict]:
    return list(_COLLECTED)
